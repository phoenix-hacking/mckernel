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


REPO = Path(__file__).resolve().parents[1]
SUDO_HELPER = REPO / "scripts/os_goal_sudo_askpass.py"
SUDO_CREDENTIAL = Path.home() / ".local/state/mckernel-os-goal/sudo-password"
PLAN_REL = "docs/verification/os-milestones-20260914"
DEFAULT_DISPATCHER_MODEL = "gpt-6.1-sol"
DEFAULT_WORKER_MODEL = "gpt-6.1-sol"
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
# The user selected continuous work through effectively the weekly allowance.
# The user requested a 3% reserve for in-flight work and delayed usage reports.
INCLUDED_USAGE_STOP_PERCENT = 97
USER_INPUT_METHOD = "item/tool/requestUserInput"
AUTONOMY_REPLY = (
    "Automatic launcher response applying the user's standing instruction; "
    "no new human answer was provided. Continue the authorized OS milestone "
    "work autonomously without asking questions. Choose reasonable implementation "
    "defaults and record assumptions. If a missing fact, credential or external "
    "resource cannot be inferred, record that task's blocker and continue other "
    "ready work. Do not fabricate facts, select an external-action approval, "
    "weaken acceptance criteria, or repeat this question."
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


def read_startup_instruction(path):
    """Load an explicit invocation note before thread/resume can start work."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8192:
            raise ValueError("Startup instruction must be a regular file of at most 8192 bytes")
        raw = os.read(fd, 8193)
        after = os.fstat(fd)
        if (len(raw) != before.st_size or
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise ValueError("Startup instruction changed during read")
        note = raw.decode("utf-8")
        if not note.strip() or "\0" in note:
            raise ValueError("Startup instruction must be nonempty UTF-8 text without NUL")
        return note
    finally:
        os.close(fd)


def say(message):
    print("[os-goal] " + message, flush=True)


def is_policy_stop(state):
    error = state.get("last_error")
    return (state.get("stop_reason") in {"turn_failed", "server_error"}
            and isinstance(error, dict) and error.get("codexErrorInfo") == "cyberPolicy")


def restart_advice(state):
    if is_policy_stop(state):
        failed = state.get("last_turn") or {}
        if not isinstance(failed, dict):
            failed = {}
        return ("service-side cyberPolicy stop; automatic retry is disabled. "
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


def queue_instruction(directory, instruction):
    """Queue an owner's instruction without touching the running server lease."""
    if not (directory / "state.json").is_file():
        raise RuntimeError("No saved OS campaign exists; start the runner first.")
    if not instruction.strip() or len(instruction.encode("utf-8")) > 8192:
        raise ValueError("Instruction must be nonempty and at most 8192 UTF-8 bytes.")
    inbox = directory / "instructions" / "pending"
    inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    ident = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex
    atomic_json(inbox / (ident + ".json"),
                {"id": ident, "submitted_at": utc(), "text": instruction})
    return ident


def progress_report(directory, repo):
    """Read the live heartbeat and existing engineering dashboard; never infer credit."""
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text()) if state_path.is_file() else {}
    goal = state.get("goal") or {}
    active = state.get("active_turns") or {}
    primary = state.get("thread_id")
    children = len(active) - int(primary in active)
    agents = ((state.get("settings") or {}).get("resources") or {}).get("max_agents", "?")
    lines = ["Runner: {} | goal: {} | active child agents: {}/{}".format(
        state.get("phase", "not_started"), goal.get("status", "none"), children, agents),
        "Last heartbeat: {}".format(state.get("updated_at", "none"))]
    control = directory / "instructions"
    pending = list((control / "pending").glob("*.json"))
    uncertain = list((control / "sending").glob("*.json"))
    lines.append("Instructions: {} pending, {} delivery-uncertain".format(len(pending), len(uncertain)))
    last_instruction = state.get("last_instruction") or {}
    if last_instruction:
        lines.append("Last instruction: {} ({})".format(
            last_instruction.get("id", "?"), last_instruction.get("status", "?")))
    dashboard = repo / PLAN_REL / "PROGRESS.md"
    if not dashboard.is_file():
        lines.append("Progress dashboard is not available.")
        return "\n".join(lines)
    lines.append("Dashboard (last generated snapshot; not live acceptance):")
    for line in dashboard.read_text().splitlines():
        if (line.startswith("- Dashboard refreshed:")
                or line.startswith("Engineering snapshot:")
                or line.startswith("- Native production gates:")
                or line.startswith("- Earned contractual points:")
                or line.startswith("- Application catalog:")
                or line.startswith("- Narrow fault modes:")
                or line.startswith("- Language gates:")
                or line.startswith("| M0")):
            lines.append(line)
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


class RPC:
    """JSON-lines transport; waiting and goal observation consume no model tokens."""
    def __init__(self, argv, log_dir, on_event):
        self.on_event = on_event
        self.next_id = 0
        self.responses = {}
        self.buffer = b""
        self.events = (log_dir / "protocol.jsonl").open("a", buffering=1)
        self.stderr = (log_dir / "server.stderr.log").open("ab")
        self.stderr_reader = (log_dir / "server.stderr.log").open("rb")
        self.stderr_decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr, bufsize=0, start_new_session=True,
                                     env=runtime_environment())
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)

    def send(self, value):
        self.proc.stdin.write((json.dumps(value) + "\n").encode())
        self.proc.stdin.flush()

    def pump(self, timeout=1.0):
        self.pump_stderr()
        if b"\n" not in self.buffer:
            if not self.selector.select(timeout):
                return
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                raise RecoverableFailure("Codex app server disconnected; see retained stderr.")
            self.buffer += chunk
        if len(self.buffer) > 32 * 1024 * 1024:
            raise RuntimeError("Oversized app-server record; stopped without discarding logs.")
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            message = json.loads(line)
            if "method" not in message:
                self.responses[message["id"]] = message
                continue
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
        self.next_id += 1
        ident = self.next_id
        self.events.write(json.dumps({"at": utc(), "request": method, "id": ident}) + "\n")
        self.send({"id": ident, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while ident not in self.responses:
            if time.monotonic() >= deadline:
                raise RecoverableFailure("App-server request timed out: " + method)
            self.pump(min(1.0, max(0.0, deadline - time.monotonic())))
        response = self.responses.pop(ident)
        if "error" in response:
            raise RuntimeError(method + ": " + json.dumps(response["error"]))
        return response["result"]

    def close(self):
        # Only this launcher's server process; never kill a host-wide process name.
        if self.proc.stdin:
            self.proc.stdin.close()
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
    """Resolve once per worker so configuration, prompts and evidence agree."""
    if not hasattr(args, "resources"):
        args.resources = resolve_resources(args.profile, args.max_agents,
                                           args.build_jobs, args.memory_gib, repo)
    return args.resources


def policy_hashes(repo):
    return {name: hashlib.sha256((repo / PLAN_REL / name).read_bytes()).hexdigest()
            for name in ("GOAL.md", "START.md", "CONVERGENCE.md", "HANDOFF.md")
            if (repo / PLAN_REL / name).is_file()}


def agent_settings(args, repo):
    return {"enabled": True,
            "max_concurrent_threads_per_session": launch_resources(args, repo)["max_agents"],
            "max_depth": 1, "default_subagent_model": DEFAULT_WORKER_MODEL,
            "default_subagent_reasoning_effort": "medium"}


def model_routing(args):
    """One source for model admission, dispatcher guidance and preview output."""
    return {
        "dispatcher": {"model": args.model, "effort": args.effort},
        "default_worker": {"model": DEFAULT_WORKER_MODEL, "effort": "medium"},
        "complex_worker": {"model": DEFAULT_WORKER_MODEL, "effort": "high"},
        "auditor": {"model": AUDIT_MODEL, "effort": "low"},
        "reviewer": {"model": REVIEW_MODEL, "effort": "high"},
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
    return argv + ["app-server", "--stdio"]


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
    models, cursor = {}, None
    while True:
        page = rpc.call("model/list", {"includeHidden": True, "limit": 100, "cursor": cursor})
        models.update((row["model"], row) for row in page["data"])
        cursor = page.get("nextCursor")
        if not cursor:
            break
    for selection in model_routing(args).values():
        model, effort = selection["model"], selection["effort"]
        if effort not in {r["reasoningEffort"] for r in models.get(model, {}).get("supportedReasoningEfforts", [])}:
            raise RuntimeError("Required model/effort not advertised: " + model + "/" + effort)
    # Deliberately do not serialize the full personal config or authentication data.
    return {"model": args.model, "effort": args.effort, "agents": expected,
            "model_routing": model_routing(args),
            "included_usage_stop_percent": INCLUDED_USAGE_STOP_PERCENT,
            "resources": launch_resources(args, repo), "policy_sha256": policy_hashes(repo),
            "agent_windows": window_capability(args.agent_windows),
            "goals": True, "approval_policy": "never", "sandbox_mode": "danger-full-access",
            "scope": "Configuration and advertised models only; quota and inference untested."}


class Campaign:
    def __init__(self, args, repo, directory, rpc_factory=RPC):
        self.args, self.repo, self.directory = args, repo, directory
        self.state_path = directory / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            "schema_version": 1, "repo": str(repo), "thread_id": None, "created_at": utc()}
        if self.state.get("schema_version") != 1 or self.state.get("repo") != str(repo):
            raise RuntimeError("State belongs to a different repository or unsupported schema.")
        self.log_dir = directory / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
        self.log_dir.mkdir(parents=True, mode=0o700)
        self.rpc_factory, self.rpc = rpc_factory, None
        self.active = {}
        self.goal = None
        self.stop_reason = None
        self.stop_now = False
        self.checkpoint_requested = False
        self.last_activity = time.monotonic()
        self.stopping = False
        self.controlled = False
        self.output = LiveOutput(self.log_dir, quiet=args.quiet, agent_windows=args.agent_windows)
        self.output.primary = self.state.get("thread_id")

    def save(self, **fields):
        self.state.update(fields)
        self.state.update(updated_at=utc(), log_dir=str(self.log_dir), active_turns=self.active,
                          agents=self.output.snapshot(), console_log=str(self.log_dir / "console.log"),
                          agent_event_count=self.output.agent_event_count)
        atomic_json(self.state_path, self.state)

    def deliver_instruction(self):
        """Steer one active coordinator turn; retain uncertain deliveries for audit."""
        ident = self.state.get("thread_id")
        if (not ident or not self.controlled or self.checkpoint_requested or self.stop_reason
                or not self.goal or self.goal.get("status") != "active"
                or ident not in self.active):
            return
        control = self.directory / "instructions"
        sending_dir = control / "sending"
        if any(sending_dir.glob("*.json")):
            return  # An uncertain earlier delivery must be resolved before newer ones.
        pending = sorted((control / "pending").glob("*.json"))
        if not pending:
            return
        sending_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        source = pending[0]
        sending = sending_dir / source.name
        os.replace(source, sending)
        item = json.loads(sending.read_text())
        receipt = {"id": item["id"], "thread_id": ident,
                   "turn_id": self.active[ident], "submitted_at": item["submitted_at"]}
        try:
            self.rpc.call("turn/steer", {"threadId": ident,
                          "expectedTurnId": receipt["turn_id"], "input": [{"type": "text",
                          "text": "Live user instruction " + item["id"] + ":\n" + item["text"]}]})
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
            self.save(last_instruction=receipt)
            self.output.notice("Instruction delivery uncertain; inspect " + str(sending))

    def on_signal(self, signum, frame):
        if (self.stop_reason or "").startswith("signal_"):
            self.stop_now = True
        # Signals retain stop authority even if a retryable error arrived first.
        self.stop_reason = "signal_" + str(signum)

    def on_watchdog(self, signum, frame):
        from watch_os_goal import watchdog_requested
        if not watchdog_requested(self.directory, os.getpid()):
            self.on_signal(signum, frame)
            return
        if not self.stop_reason and not self.stop_now:
            self.stop_reason = "watchdog_recovery"

    def remember_goal(self, goal):
        self.goal = goal
        self.save(goal=goal)

    def record_failure(self, error, reason, will_retry=False):
        self.save(last_error=error)
        if (self.stop_reason or "").startswith("signal_") or self.stop_reason in {
                "work_window", "needs_user_input", "goal_cleared"}:
            # A late server error must not turn a requested stop into recovery.
            return
        info = (error or {}).get("codexErrorInfo")
        if isinstance(info, str) and info in LIMIT_ERRORS:
            self.stop_reason, self.stop_now = "quota_exhausted", True
        elif self.stop_reason != "quota_exhausted" and not will_retry:
            self.stop_reason = "rate_limit" if info == "rateLimitExceeded" else reason
            self.stop_now = True

    def record_rate_limits(self, limits):
        previous = self.state.get("last_rate_limits") or {}
        self.save(last_rate_limits=limits)
        if self.stop_reason:
            return
        primary = (limits or {}).get("primary") or {}
        used = primary.get("usedPercent")
        if (not isinstance(used, (int, float)) or isinstance(used, bool) or
                not math.isfinite(used) or not 0 <= used <= 100):
            self.stop_reason, self.stop_now = "included_usage_unknown", True
        elif used >= INCLUDED_USAGE_STOP_PERCENT:
            # Leave room for already-running turns and delayed usage reports.
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
            self.output.notice("Included-usage safety stop: " + self.stop_reason)

    def event(self, message):
        method, data = message.get("method"), message.get("params", {})
        self.output.event(message)
        thread = data.get("threadId")
        primary = thread == self.state.get("thread_id")
        if "id" in message:
            if method == USER_INPUT_METHOD:
                self.save(last_automatic_input={"thread_id": thread, "request_id": message["id"],
                          "question_ids": [q["id"] for q in data["questions"]],
                          "policy": "standing_autonomy_instruction; no new human answer"})
                return
            self.save(pending_request={"method": method, "params": data})
            self.stop_reason, self.stop_now = "needs_user_input", True
        elif method == "thread/goal/updated" and primary:
            self.remember_goal(data["goal"])
        elif method == "thread/goal/cleared" and primary:
            self.goal = None
            self.stop_reason, self.stop_now = "goal_cleared", True
        elif method == "turn/started":
            self.active[thread] = data["turn"]["id"]
            self.last_activity = time.monotonic()
            self.save()
        elif method == "turn/completed":
            if self.active.get(thread) == data["turn"]["id"]:
                self.active.pop(thread, None)
            self.last_activity = time.monotonic()
            self.save(last_turn={"thread_id": thread, "id": data["turn"]["id"],
                                 "status": data["turn"]["status"]})
            if data["turn"]["status"] == "failed":
                self.record_failure(data["turn"].get("error"), "turn_failed")
        elif method == "error":
            self.record_failure(data["error"], "server_error", data.get("willRetry", False))
        elif method == "account/rateLimits/updated":
            self.record_rate_limits(data.get("rateLimits"))
        elif method == "account/updated" and data.get("authMode") not in (None, "chatgpt"):
            self.stop_reason, self.stop_now = "chatgpt_auth_changed", True
        elif method == "item/agentMessage/delta" and primary:
            # Preserve the existing dispatcher-only transcript for older consumers.
            excerpt = data.get("delta", "")
            with (self.log_dir / "dispatcher.txt").open("a") as stream:
                stream.write(excerpt)

    def instructions(self):
        continuation = (
            "This invocation has no time limit. The user explicitly requests continuous "
            "work until the entire OS objective is accepted or the included-plan "
            "usage guard stops this invocation; never spend purchased credits. "
            "Earlier work-window endings, checkpoint pauses and statements that a window "
            "is authoritative are historical and do not pause this invocation. Continue "
            "after checkpoints. Repair project-owned prerequisites and pursue independent "
            "ready work when a task blocks. Preserve real external blockers and recheck "
            "availability with backoff when no work is ready; do not invent acceptance. "
            if not self.args.hours else
            "The user explicitly selected a finite work window for this invocation. "
            "Earlier window endings are historical; continue until this launcher sends "
            "a new checkpoint/stop request. "
        )
        return (
            (("Current user instruction for this invocation, loaded before session activation:\n"
              + self.args.startup_instruction + "\nEnd current invocation instruction.\n")
             if getattr(self.args, "startup_instruction", None) else "") +
            (("The user explicitly requested a fresh OS development conversation guided by "
              "Markdown. Read " + PLAN_REL + "/SESSION-HANDOFF.md first, then the current "
              "goal/start/convergence/handoff files. Prior session state is preserved under "
              "session-archives; do not load its entire conversation or replay a rejected "
              "compaction/request. Work on the next independent authorized OS task. "
              "Preserve prior blocked work for review and keep service checks active. ")
             if getattr(self.args, "fresh_session", False)
             or getattr(self.args, "fresh_recovery_proof", None)
             or self.state.get("previous_session") else "") +
            "The user invoked scripts/run_os_goal.py for autonomous execution, not planning. "
            + continuation +
            "The user explicitly authorized full filesystem/network access and no "
            "approval or clarification prompts for this OS campaign. Do not ask "
            "questions: choose reasonable defaults, record assumptions, and dispatch "
            "independent ready work when a task lacks necessary information. Pass "
            "these instructions to every worker. Use noninteractive commands. "
            "The user supplied a local sudo credential: use sudo -A with the "
            "inherited SUDO_ASKPASS helper when elevated host access is necessary. "
            "Do not add -n to password-authenticated sudo -A. Never read the private "
            "credential file, invoke the askpass helper directly, or put its output "
            "in a tool response, shell command, environment value, Git file or log. "
            "If authentication fails, retain the error and continue unrelated work. "
            "First read " + PLAN_REL + "/GOAL.md, START.md, CONVERGENCE.md and HANDOFF.md. "
            "Read README.md once for the original acceptance requirements. Read only "
            "the latest relevant CURRENT.md entries and selected evidence, not its entire history. "
            "This startup order supersedes the historical reading order in the immutable "
            "stored objective. Reconcile the compact handoff against live sources and leases. "
            "Adopt and record these policy SHA256 values: " + json.dumps(policy_hashes(self.repo), sort_keys=True) + ". "
            "The user explicitly authorizes "
            "automatic bounded subagents; use fresh bounded packets and explicit models. "
            "The user requested more GPT-6.1 use. Apply this invocation's model routing "
            "instead of older model-selection instructions in workflow documents: "
            + json.dumps(model_routing(self.args), sort_keys=True) + ". " +
            "Use GPT-6.1 Sol/medium for implementation, test repair and ordinary workers; "
            "use GPT-6.1 Sol/high for difficult multi-step kernel repairs. All "
            "roles must use gpt-6.1-sol, including auditors and independent reviewers. Use the "
            "auditor model only for bounded extraction/inventory tasks with fixed "
            "expectations. Preserve the independent reviewer for unsafe ownership, "
            "concurrency, ABI, execution release and final acceptance. Do not use "
            "the auditor role for kernel implementation. Do not silently fall back "
            "to an older model when a required selection is unavailable. "
            "Choose the lowest effort suitable for the actual task: low for simple "
            "inventories and extraction, medium for routine implementation/tests, "
            "high for complex repairs and independent safety review. Increase effort "
            "only when a concrete difficulty or failed bounded correction warrants "
            "it; do not spend high effort on repetitive bookkeeping. Max/Ultra are disabled. "
            + resource_instructions(launch_resources(self.args, self.repo)) + " " +
            "Apply CONVERGENCE.md on every continuation: one failed candidate and one "
            "bounded correction per failure family before expert escalation. Carry family "
            "history across resumed turns; never repeat an unchanged deterministic failure. "
            "The user's immediate priority is a functional, stable, app-testable "
            "McKernel core, not perfect formal gate closure. Use a fast diagnostic "
            "loop: build the smallest current-candidate kernel artifact, run the "
            "smallest real McKernel startup app, repair the observed failure, and "
            "repeat for memory, file, thread and shutdown smokes. A diagnostic "
            "result is never formal application or production acceptance. "
            "For unprivileged compile/tests inside an already reviewed reusable "
            "profile, execute promptly; do not create a fresh packet, archive or "
            "independent review for each edit or test vector. Keep the actual "
            "command, result and relevant failure evidence. For root, module or "
            "guest work, retain the applicable independent execution release, "
            "isolation, resource lease and cleanup requirements. Do not reuse a "
            "source-only packet as that release. If a one-shot harness attempt "
            "fails on its own observer or evidence writer, fix that program with "
            "cheap local regression tests before seeking another privileged run; "
            "do not send unchanged packet designs through more review cycles. "
            "Parallelize independent kernel/Rust repair, candidate build binding, "
            "Linux oracle/diagnostic runner, and bounded regression work across "
            "disjoint files. Prefer useful implementation/test lanes to audits; "
            "use the available child slots only for ready independent work. "
            "Do not wait for unrelated M01-M03 formal acceptance before a safe "
            "diagnostic app pilot, but honor its actual runtime prerequisites. "
            "Capture observed app bytes, exit status, kernel log and teardown. "
            "Keep worker "
            "write sets disjoint, integrate promptly, close completed children and refill "
            "available slots with dependency-ready work. Preserve independent final review. "
            "The user's priority is strong, measurable OS progress. For each active lane "
            "name its owner, concrete defect, next executable check and downstream task "
            "it unlocks. Use the available slots for implementation and regression tests; "
            "assign audits or reviews only when they answer a specific blocking question. "
            "At each existing checkpoint report newly verified behavior, actual tests and "
            "evidence, the count of real guest apps and current-candidate builds, remaining "
            "blockers and the next executable step. If two completed "
            "dispatch cycles produce no technical result, change the repair strategy or "
            "move to a dependency-ready task; do not interrupt healthy builds or soaks. "
            "Avoid more launcher or dashboard work unless a reproduced defect "
            "blocks execution, correctness or requested visibility. "
            "Never weaken an oracle or count planning, agent activity or documentation "
            "as implemented OS behavior. Follow all original execution releases. "
            "Preserve preexisting untracked work. Read all applicable active instructions. "
            "Write implementation evidence and the live task cursor per the plan. This "
            "launcher's logs are at " + str(self.log_dir) + "; state.json is launcher-owned. "
            "Do not edit or start another launcher, clear/replace this goal, change its "
            "budget, or alter model/permission settings to bypass a blocker. "
            "The launcher controls the work window and goal pausing; agents use goal "
            "status tools only under their actual tool rules. "
            "Never signal or kill this invocation's watcher/worker/server to obey a "
            "historical preparation hold. Never call --instruct to fabricate a new "
            "user instruction or requeue a historical instruction. A normal Git "
            "checkpoint does not pause or stop the campaign. Only a new external "
            "stop, the selected usage/time limit or an actual safety blocker does. "
            "Keep CURRENT.md and docs/verification/os-milestones-20260914/PROGRESS.md updated and "
            "commit/push verified checkpoints about every 30 minutes and before long "
            "runs. At coherent checkpoints or formal acceptance updates, run "
            "python3 scripts/update_progress_tracker.py so the intermediary-goal bars, "
            "task ledger, blockers, evidence paths, and next action reflect the new "
            "state. On a checkpoint request stop new dispatch, finish bounded work, "
            "join/close workers, record any live process identities, checkpoint and return. "
            "If credentials or external resources are unavailable, preserve the blocker "
            "and continue independent ready work. Never store credentials in the plan or logs."
            + (" This is automatic crash recovery. Read HANDOFF.md, relevant CURRENT.md entries and the previous "
               "run/watcher records first. Reconcile source changes and exact live "
               "process/runtime leases before any new build or guest. "
               + ("Continue from the Markdown handoff in this fresh conversation and preserve "
                  "the acceptance ledger; do not replay completed or rejected work."
                  if getattr(self.args, "fresh_recovery_proof", None)
                  or getattr(self.args, "fresh_session", False)
                  or self.state.get("previous_session") else
                  "Resume the existing thread and acceptance ledger; do not replay completed work.")
               if self.args.recovered else "")
        )

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

    def begin(self):
        # Admission failures belong to this worker, never the preceding retry.
        if (self.state.get("resume_instruction") or {}).get("status") in {"sending", "delivery_uncertain"}:
            raise RuntimeError("Resume instruction delivery is uncertain; reconcile its saved turn before resuming")
        note = getattr(self.args, "startup_instruction", None)
        self.save(worker_pid=os.getpid(), server_pid=None, server_start=None, retryable=False,
                  startup_instruction_sha256=hashlib.sha256(note.encode()).hexdigest() if note else None)
        check_resources(launch_resources(self.args, self.repo))
        self.rpc = self.rpc_factory(server_argv(self.args, self.repo), self.log_dir, self.event)
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
        if note and previous_id and goal and goal["status"] == "paused" and not self.args.recovered:
            # A fresh explicit --run is a CURRENT user instruction. Seeding it
            # once before activation fixes stale user-role history without a
            # second dispatcher or an automatic turn/start continuation loop.
            page = self.rpc.call("thread/turns/list", {
                "threadId": ident, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"})
            if any(turn.get("status") == "inProgress" for turn in page["data"]):
                raise RuntimeError("A saved turn is still active; reconcile it before a fresh resume instruction")
            receipt = {"sha256": hashlib.sha256(note.encode()).hexdigest(), "status": "sending"}
            self.save(resume_instruction=receipt)
            try:
                started = self.rpc.call("turn/start", {
                    "threadId": ident, "input": [{"type": "text", "text": note}]})
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

    def pause(self):
        ident = self.state.get("thread_id")
        if not ident or not self.controlled:
            return
        current = self.rpc.call("thread/goal/get", {"threadId": ident})["goal"]
        if current and current["objective"] != OBJECTIVE:
            self.controlled = False
            raise RuntimeError("Goal objective changed externally; launcher will not alter it.")
        if current and current["status"] == "active":
            current = self.rpc.call("thread/goal/set", {"threadId": ident, "status": "paused"})["goal"]
        self.remember_goal(current)

    def request_checkpoint(self):
        self.pause()
        self.checkpoint_requested = True
        ident = self.state["thread_id"]
        turn = self.active.get(ident)
        if turn:
            self.rpc.call("turn/steer", {"threadId": ident, "expectedTurnId": turn,
                "input": [{"type": "text", "text":
                    "The launcher is stopping this invocation following a signal or an "
                    "explicitly configured time limit. Stop new task dispatch. "
                    "Finish bounded active operations, join/close child agents, preserve "
                    "original evidence and active process identities, update CURRENT.md "
                    "with next tasks, commit/push and verify the checkpoint, then return. "
                    "The launcher has paused future goal continuations. Do not mark the OS "
                    "complete or resume it during shutdown. A subsequent launcher "
                    "invocation authorizes continuation; this pause is not permanent."}]})
        self.output.notice("Checkpoint requested; waiting for bounded active work to finish.")

    def stop(self):
        if not self.rpc or self.stopping or not self.controlled:
            return
        self.stopping = True
        errors = []
        try:
            self.pause()
        except Exception as error:
            errors.append(str(error))
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

    def run(self):
        started = time.monotonic()
        deadline = started + self.args.hours * 3600 if self.args.hours else float("inf")
        checkpoint_at = max(started, deadline - min(self.args.grace_seconds, self.args.hours * 1800))
        stop_deadline = None
        next_refresh = started + 30
        next_heartbeat = started
        code = 1
        try:
            self.output.notice("Starting launcher; worker_pid=" + str(os.getpid())
                               + "; live log: " + str(self.log_dir / "console.log"))
            self.begin()
            while True:
                now = time.monotonic()
                status = self.goal["status"] if self.goal else None
                if self.stop_now:
                    code = 21 if self.stop_reason in {"quota_exhausted", "included_usage_guard",
                                                      "included_usage_unknown", "credit_balance_decreased",
                                                      "credit_balance_unknown", "chatgpt_auth_required",
                                                      "chatgpt_auth_changed"} else 23
                    break
                if status in TERMINAL_CODES and not self.checkpoint_requested:
                    code = TERMINAL_CODES[status]
                    break
                if not self.checkpoint_requested and (self.stop_reason or now >= checkpoint_at):
                    self.stop_reason = self.stop_reason or "work_window"
                    self.request_checkpoint()
                    stop_deadline = min(deadline, now + self.args.grace_seconds)
                if self.checkpoint_requested and (not self.active or now >= stop_deadline):
                    code = 10
                    break
                if not self.active and now - self.last_activity > 120:
                    self.stop_reason = "active_goal_did_not_continue"
                    self.save(retryable=True)
                    code = 24
                    break
                self.deliver_instruction()
                self.rpc.pump(timeout=1)
                self.output.flush()
                now = time.monotonic()
                if now >= next_heartbeat:
                    self.output.heartbeat(self.goal, self.active, now - started,
                                          os.getpid(), self.state.get("server_pid"))
                    self.save(heartbeat_at=utc(), uptime_seconds=round(now - started, 1))
                    next_heartbeat = now + self.args.heartbeat_seconds
                if now >= next_refresh:
                    self.remember_goal(self.rpc.call("thread/goal/get", {"threadId": self.state["thread_id"]})["goal"])
                    next_refresh = now + 30
        except Exception as error:
            self.stop_reason = self.stop_reason or "launcher_error"
            self.save(last_error=str(error), retryable=isinstance(error, (
                RecoverableFailure, BrokenPipeError, ConnectionResetError)))
            self.output.notice(str(error))
        finally:
            try:
                self.stop()
            finally:
                try:
                    if self.rpc:
                        self.rpc.close()
                    self.save(phase="stopped", stop_reason=self.stop_reason, exit_code=code)
                    self.output.notice("Stopped: goal reports " + str((self.goal or {}).get("status", "unknown"))
                                       + "; " + (self.stop_reason or "goal status") + ".")
                    self.output.notice("State: " + str(self.state_path) + "; " + restart_advice(self.state))
                finally:
                    self.output.close()
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
    parser.add_argument("--hours", type=float, default=0, help="Optional work window in hours; 0 means no time limit (default: 0)")
    parser.add_argument("--grace-seconds", type=float, default=600, help="Reserve up to this many seconds for a checkpoint")
    parser.add_argument("--model", default=DEFAULT_DISPATCHER_MODEL, choices=[DEFAULT_DISPATCHER_MODEL],
                        help="Dispatcher model; default: " + DEFAULT_DISPATCHER_MODEL)
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--profile", choices=["aggressive", "balanced"], default="aggressive",
                        help="Dedicated-machine parallelism (default) or historical balanced limits")
    parser.add_argument("--max-agents", type=int, help="Child-agent ceiling; default up to 8 aggressive / 3 balanced")
    parser.add_argument("--build-jobs", type=int, help="Aggregate build jobs; default all affinity CPUs in aggressive mode")
    parser.add_argument("--memory-gib", type=float, help="Aggregate build memory budget; default up to 24 GiB aggressive / 12 balanced")
    parser.add_argument("--agent-windows", choices=["auto", "on", "off"], default="auto",
                        help="Separate live desktop window per child (default: auto when a desktop is available); logs always retained")
    parser.add_argument("--fresh-session", action="store_true",
                        help="Explicitly start a fresh conversation from Markdown; archive the previous state")
    parser.add_argument("--fresh-on-recovery", action="store_true",
                        help="Use fresh Markdown-guided conversations after classified recoverable crashes")
    parser.add_argument("--fresh-recovery-proof", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--token-budget", type=int, help="Explicit total goal budget; omitted preserves the current budget")
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
    parser.add_argument("--recovered", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
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
        print(json.dumps(current, indent=2))
        return 0
    if args.progress:
        print(progress_report(directory, REPO))
        return 0
    if args.instruct is not None:
        ident = queue_instruction(directory, args.instruct)
        print("Queued instruction " + ident + "; it will reach the next active coordinator turn.")
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
                          "resources": launch_resources(args, REPO), "policy_sha256": policy_hashes(REPO),
                          "model_routing": model_routing(args),
                          "included_usage_stop_percent": INCLUDED_USAGE_STOP_PERCENT,
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
                print(json.dumps(preflight(rpc, args, REPO), indent=2))
            finally:
                rpc.close()
        return 0
    if not args.worker:
        check_resources(launch_resources(args, REPO))
        from watch_os_goal import supervise
        return supervise(args, REPO, directory, list(sys.argv[1:] if argv is None else argv), Lease, atomic_json)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lease = Lease(directory / "run.lock")
    try:
        if args.fresh_session or args.fresh_recovery_proof:
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
