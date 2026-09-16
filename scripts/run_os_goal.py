#!/usr/bin/env python3
"""Start/resume the McKernel milestone goal through the local Codex app server.

No model calls for --dry-run, --status, --check or --check-sudo. A normal invocation starts
paid/account-metered work. Runtime state stays in the repository's Git directory.
"""

import argparse
import codecs
import fcntl
import json
import math
import os
from pathlib import Path
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from uuid import uuid4

from os_goal_output import LiveOutput


REPO = Path(__file__).resolve().parents[1]
SUDO_HELPER = REPO / "scripts/os_goal_sudo_askpass.py"
SUDO_CREDENTIAL = Path.home() / ".local/state/mckernel-os-goal/sudo-password"
PLAN_REL = "docs/verification/os-milestones-20260914"
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


def say(message):
    print("[os-goal] " + message, flush=True)


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


def server_argv(args, repo):
    settings = {
        "model": args.model,
        "model_reasoning_effort": args.effort,
        "features.goals": True,
        "agents.enabled": True,
        "agents.max_concurrent_threads_per_session": 3,
        "agents.max_depth": 1,
        "agents.default_subagent_model": "gpt-5.6-luna",
        "agents.default_subagent_reasoning_effort": "low",
        "approval_policy": "never",
        # The user explicitly authorized full access for the standalone launcher.
        # This is local to this process; global config/project trust are unchanged.
        "sandbox_mode": "danger-full-access",
    }
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
    expected = {"enabled": True, "max_concurrent_threads_per_session": 3,
                "max_depth": 1, "default_subagent_model": "gpt-5.6-luna",
                "default_subagent_reasoning_effort": "low"}
    if (config.get("model") != args.model or config.get("model_reasoning_effort") != args.effort
            or not (config.get("features") or {}).get("goals")
            or config.get("approval_policy") != "never"
            or any(agents.get(key) != value for key, value in expected.items())):
        raise RuntimeError("Effective Codex settings differ from the requested dispatch limits.")
    models, cursor = {}, None
    while True:
        page = rpc.call("model/list", {"includeHidden": True, "limit": 100, "cursor": cursor})
        models.update((row["model"], row) for row in page["data"])
        cursor = page.get("nextCursor")
        if not cursor:
            break
    for model, effort in [(args.model, args.effort), ("gpt-5.6-luna", "low"),
                          ("gpt-5.6-luna", "medium"), ("gpt-6-astra", "high")]:
        if effort not in {r["reasoningEffort"] for r in models.get(model, {}).get("supportedReasoningEfforts", [])}:
            raise RuntimeError("Required model/effort not advertised: " + model + "/" + effort)
    # Deliberately do not serialize the full personal config or authentication data.
    return {"model": args.model, "effort": args.effort, "agents": expected,
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
        self.output = LiveOutput(self.log_dir, quiet=args.quiet)
        self.output.primary = self.state.get("thread_id")

    def save(self, **fields):
        self.state.update(fields)
        self.state.update(updated_at=utc(), log_dir=str(self.log_dir), active_turns=self.active,
                          agents=self.output.snapshot(), console_log=str(self.log_dir / "console.log"),
                          agent_event_count=self.output.agent_event_count)
        atomic_json(self.state_path, self.state)

    def on_signal(self, signum, frame):
        if self.stop_reason:
            self.stop_now = True
        else:
            self.stop_reason = "signal_" + str(signum)

    def remember_goal(self, goal):
        self.goal = goal
        self.save(goal=goal)

    def record_failure(self, error, reason, will_retry=False):
        self.save(last_error=error)
        info = (error or {}).get("codexErrorInfo")
        if isinstance(info, str) and info in LIMIT_ERRORS:
            self.stop_reason, self.stop_now = "quota_exhausted", True
        elif self.stop_reason != "quota_exhausted" and not will_retry:
            self.stop_reason = "rate_limit" if info == "rateLimitExceeded" else reason
            self.stop_now = True

    def record_rate_limits(self, limits):
        # Purchased credits are a fallback after the plan's included allowance.
        # A zero credit balance therefore is not evidence that Codex usage itself
        # is exhausted; the server reports that separately as a limit error.
        self.save(last_rate_limits=limits)

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
        elif method == "item/agentMessage/delta" and primary:
            # Preserve the existing dispatcher-only transcript for older consumers.
            excerpt = data.get("delta", "")
            with (self.log_dir / "dispatcher.txt").open("a") as stream:
                stream.write(excerpt)

    def instructions(self):
        continuation = (
            "This invocation has no time limit. The user explicitly requests continuous "
            "work until the entire OS objective is accepted or account credits are exhausted. "
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
            "Follow " + PLAN_REL + "/START.md and GOAL.md. The user explicitly authorizes "
            "automatic cheap subagents; use fresh bounded packets and explicit models. "
            "Maximum three children, no recursive dispatch, one heavy build/guest owner. "
            "Preserve preexisting untracked work. Read all applicable active instructions. "
            "Write implementation evidence and the live task cursor per the plan. This "
            "launcher's logs are at " + str(self.log_dir) + "; state.json is launcher-owned. "
            "Do not edit or start another launcher, clear/replace this goal, change its "
            "budget, or alter model/permission settings to bypass a blocker. "
            "The launcher controls the work window and goal pausing; agents use goal "
            "status tools only under their actual tool rules. Keep CURRENT.md and "
            "docs/verification/os-milestones-20260914/PROGRESS.md updated and "
            "commit/push verified checkpoints about every 30 minutes and before long "
            "runs. After every accepted packet, diagnosis, or checkpoint, run "
            "python3 scripts/update_progress_tracker.py so the intermediary-goal bars, "
            "task ledger, blockers, evidence paths, and next action reflect the new "
            "state. On a checkpoint request stop new dispatch, finish bounded work, "
            "join/close workers, record any live process identities, checkpoint and return. "
            "If credentials or external resources are unavailable, preserve the blocker "
            "and continue independent ready work. Never store credentials in the plan or logs."
            + (" This is automatic crash recovery. Read CURRENT.md and the previous "
               "run/watcher records first. Reconcile source changes and exact live "
               "process/runtime leases before any new build or guest. Resume the "
               "existing thread and acceptance ledger; do not replay completed work."
               if self.args.recovered else "")
        )

    def begin(self):
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
        if self.stop_reason:
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
                         goal["status"] == "budgetLimited" and self.args.token_budget is None):
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
        if goal and goal["status"] == "budgetLimited" and self.args.token_budget is None:
            self.remember_goal(goal)
            return
        if self.stop_reason:
            self.remember_goal(goal)
            return
        update = {"threadId": ident, "status": "active"}
        if not goal:
            update["objective"] = OBJECTIVE
        if self.args.token_budget is not None:
            update["tokenBudget"] = self.args.token_budget
        if not goal or goal["status"] != "active" or self.args.token_budget is not None:
            # The server's durable-goal engine starts/continues idle turns. Do not
            # also send a turn/start loop, which could duplicate or steer that work.
            goal = self.rpc.call("thread/goal/set", update)["goal"]
        self.remember_goal(goal)
        self.save(phase="running")
        self.output.notice("Thread " + ident + "; " + self.args.model + "/" + self.args.effort + "; Luna workers.")

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
                    code = 21 if self.stop_reason == "quota_exhausted" else 23
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
                    self.output.notice("State: " + str(self.state_path) + "; run the same command to resume unfinished work.")
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
    parser.add_argument("--hours", type=float, default=0, help="Optional work window in hours; 0 means no time limit (default: 0)")
    parser.add_argument("--grace-seconds", type=float, default=600, help="Reserve up to this many seconds for a checkpoint")
    parser.add_argument("--model", default="gpt-5.6-sol", help="Dispatcher model; default: gpt-5.6-sol")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max", "ultra"])
    parser.add_argument("--token-budget", type=int, help="Explicit total goal budget; omitted preserves the current budget")
    parser.add_argument("--codex", default="codex", help="Path to the local Codex executable")
    parser.add_argument("--max-restarts", type=int, default=-1, help="Automatic recoveries; -1 means unlimited, 0 disables (default: -1)")
    parser.add_argument("--restart-delay", type=float, default=5, help="Initial recovery backoff in seconds (default: 5)")
    parser.add_argument("--watchdog-seconds", type=float, default=180, help="Recover a runner with no state heartbeat; 0 disables")
    parser.add_argument("--heartbeat-seconds", type=float, default=15, help="Print liveness and agent activity every N seconds (default: 15)")
    parser.add_argument("--stall-seconds", type=float, default=900, help="Recover a running campaign with no agent events for N seconds; 0 disables (default: 900)")
    parser.add_argument("--quiet", action="store_true", help="Hide live agent output; keep heartbeats and console.log")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--recovered", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
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
    if args.dry_run:
        print(json.dumps({"command": shlex.join(server_argv(args, REPO)), "hours": args.hours,
                          "checkpoint_reserve_seconds": args.grace_seconds, "state_directory": str(directory),
                          "objective": OBJECTIVE, "model_calls": 0,
                          "sudo_helper": str(SUDO_HELPER), "sudo_credential_configured": SUDO_CREDENTIAL.is_file(),
                          "supervised": not args.worker, "max_restarts": args.max_restarts,
                          "watchdog_seconds": args.watchdog_seconds,
                          "heartbeat_seconds": args.heartbeat_seconds, "live_output": not args.quiet,
                          "stall_seconds": args.stall_seconds,
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
        with tempfile.TemporaryDirectory(prefix="mckernel-goal-check-") as temporary:
            rpc = RPC(server_argv(args, REPO), Path(temporary), lambda event: None)
            try:
                print(json.dumps(preflight(rpc, args, REPO), indent=2))
            finally:
                rpc.close()
        return 0
    if not args.worker:
        from watch_os_goal import supervise
        return supervise(args, REPO, directory, list(sys.argv[1:] if argv is None else argv), Lease, atomic_json)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lease = Lease(directory / "run.lock")
    try:
        campaign = Campaign(args, REPO, directory)
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, campaign.on_signal)
        return campaign.run()
    finally:
        lease.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as failure:
        say(str(failure))
        sys.exit(1)
