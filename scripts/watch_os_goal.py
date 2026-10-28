"""Supervise the OS runner and preserve its work window across crashes."""

import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

from os_goal_transport import (READ_ONLY_RPC_METHODS, classify_rpc_failure,
                               classify_service_failure, classify_usage_failure)
from os_goal_handoff import write_recovery_handoff


def process_start(pid):
    """Linux process birth identity; never act on a reused or unreadable PID."""
    try:
        fields = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except FileNotFoundError:
        return None
    except (OSError, IndexError):
        return "unknown"


def snapshot(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}


def watchdog_requested(directory, worker_pid):
    """Authenticate a persisted hang request for this worker and live parent."""
    if type(worker_pid) is not int or worker_pid != os.getpid():
        return False
    worker_start = process_start(worker_pid)
    if not isinstance(worker_start, str) or not worker_start.isdigit():
        return False
    path = Path(directory) / ("watchdog-request-" + str(worker_pid) + "-" + worker_start + ".json")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                    or before.st_size > 4096):
                return False
            raw = os.read(fd, 4097)
            after = os.fstat(fd)
            if (len(raw) != before.st_size or before.st_size != after.st_size
                    or before.st_mtime_ns != after.st_mtime_ns
                    or before.st_ctime_ns != after.st_ctime_ns):
                return False
        finally:
            os.close(fd)
        request = json.loads(raw)
        parent = os.getppid()
        parent_start = process_start(parent)
        return (isinstance(request, dict) and type(request.get("schema_version")) is int
                and request["schema_version"] == 1
                and type(request.get("watcher_pid")) is int and request["watcher_pid"] == parent
                and isinstance(parent_start, str) and parent_start.isdigit()
                and request.get("watcher_start") == parent_start
                and type(request.get("worker_pid")) is int and request["worker_pid"] == worker_pid
                and request.get("worker_start") == worker_start
                and request.get("reason") in {"heartbeat_stalled", "agent_progress_stalled"})
    except (OSError, ValueError, TypeError):
        return False


def credit_poll_timeout(state):
    """Legacy name: classify only the shared endpoint-qualified usage transport cases."""
    return (state.get("stop_reason") == "credit_budget_unknown"
            and classify_usage_failure(state.get("credit_budget_error")) is not None)


def timeout_pause_owned(state):
    """Validate the current worker's actual successful timeout shutdown pause."""
    row = state.get("credit_timeout_shutdown_pause")
    goal = state.get("goal")
    if not isinstance(row, dict) or not isinstance(goal, dict):
        return False
    before = row.get("goal_before") or {}
    return (row.get("schema_version") == 1 and row.get("pause_confirmed") is True
            and row.get("pause_method") == "thread/goal/set"
            and type(row.get("worker_pid")) is int and row["worker_pid"] == state.get("worker_pid")
            and isinstance(row.get("worker_start"), str) and row["worker_start"].isdigit()
            and row["worker_start"] == state.get("worker_start")
            and row.get("thread_id") == state.get("thread_id")
            and row.get("stop_reason") == state.get("stop_reason")
            and row.get("credit_budget_error") == state.get("credit_budget_error")
            and before.get("status") == "active" and goal.get("status") == "paused"
            and goal.get("updatedAt") is not None and before.get("updatedAt") is not None
            and before.get("objective") == goal.get("objective")
            and row.get("goal_after") == goal
            and row.get("goal_after_sha256") == hashlib.sha256(json.dumps(
                goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest())


def timeout_startup_owned(state):
    """Only the current watcher's in-memory approved origin permits startup retries."""
    row, origin = state.get("credit_timeout_startup"), state.get("_credit_timeout_origin")
    goal = state.get("goal")
    if not isinstance(row, dict) or not isinstance(origin, dict) or not isinstance(goal, dict):
        return False
    digest = hashlib.sha256(json.dumps(goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return (row.get("schema_version") == 1 and row.get("before_inference") is True
            and row.get("account_validated") is True and row.get("phase_at_failure") == "starting"
            and row.get("worker_pid") == state.get("worker_pid")
            and isinstance(row.get("worker_start"), str) and row["worker_start"].isdigit()
            and row["worker_start"] == state.get("worker_start")
            and row.get("watcher_pid") == origin.get("watcher_pid")
            and row.get("watcher_start") == origin.get("watcher_start")
            and row.get("thread_id") == origin.get("thread_id") == state.get("thread_id")
            and goal.get("status") == "paused" and origin.get("approved") is True
            and row.get("expected_goal_sha256") == origin.get("goal_after_sha256") == digest)


def transport_failure_owned(state):
    """Typed producer observation for this worker, not a generic retryable flag."""
    row = state.get("transport_failure")
    if not (isinstance(row, dict) and row.get("schema_version") == 1
            and row.get("worker_pid") == state.get("worker_pid")
            and isinstance(row.get("worker_start"), str) and row["worker_start"].isdigit()
            and row["worker_start"] == state.get("worker_start")
            and row.get("thread_id") == state.get("thread_id")
            and isinstance(row.get("thread_id"), str) and bool(row["thread_id"].strip())
            and row.get("class") in {"disconnected", "broken_pipe", "connection_reset",
                                     "rpc_timeout", "continuation_stall", "service_transient"}
            and row.get("mutating") is False
            and (row.get("method") is None or row.get("method") in READ_ONLY_RPC_METHODS)):
        return False
    label = row["class"]
    if label == "service_transient":
        error = state.get("last_error")
        return (row.get("error_type") == "ServiceTransient" and row.get("method") is None
                and state.get("stop_reason") in {"server_error", "turn_failed", "rate_limit", "launcher_error"}
                and classify_service_failure(error) is not None
                and row.get("service_error", error) == error
                and row.get("error") == json.dumps(error, sort_keys=True, separators=(",", ":")))
    if label in {"disconnected", "rpc_timeout"}:
        return classify_rpc_failure(row.get("error")) == label
    if label in {"broken_pipe", "connection_reset"}:
        return row.get("error_type") == {"broken_pipe": "BrokenPipeError",
                                          "connection_reset": "ConnectionResetError"}[label]
    return (row.get("error") == "active_goal_did_not_continue"
            and state.get("stop_reason") == "active_goal_did_not_continue")


def transport_pause_owned(state):
    """Only an actual successful transport shutdown may qualify a paused goal."""
    row, failure, goal = (state.get("transport_shutdown_pause"),
                          state.get("transport_failure"), state.get("goal"))
    if not transport_failure_owned(state) or not isinstance(row, dict) or not isinstance(goal, dict):
        return False
    before = row.get("goal_before") or {}
    return (row.get("schema_version") == 1 and row.get("pause_confirmed") is True
            and row.get("pause_method") == "thread/goal/set"
            and row.get("worker_pid") == state.get("worker_pid")
            and row.get("worker_start") == state.get("worker_start")
            and row.get("thread_id") == state.get("thread_id")
            and row.get("stop_reason") == state.get("stop_reason")
            and row.get("transport_error") == failure.get("error")
            and row.get("transport_class") == failure.get("class")
            and row.get("transport_method") == failure.get("method")
            and before.get("status") == "active" and goal.get("status") == "paused"
            and before.get("objective") == goal.get("objective")
            and before.get("updatedAt") is not None and goal.get("updatedAt") is not None
            and row.get("goal_after") == goal
            and row.get("goal_after_sha256") == hashlib.sha256(json.dumps(
                goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest())


def transport_startup_owned(state):
    """A new startup can inherit only this live watcher's in-memory approval."""
    row, origin, goal = (state.get("transport_startup"), state.get("_transport_origin"),
                          state.get("goal"))
    if not isinstance(row, dict) or not isinstance(origin, dict) or not isinstance(goal, dict):
        return False
    if not (row.get("schema_version") == 1 and row.get("before_inference") is True
            and row.get("worker_pid") == state.get("worker_pid")
            and isinstance(row.get("worker_start"), str) and row["worker_start"].isdigit()
            and row["worker_start"] == state.get("worker_start")
            and row.get("watcher_pid") == origin.get("watcher_pid")
            and row.get("watcher_start") == origin.get("watcher_start")
            and row.get("thread_id") == origin.get("thread_id") == state.get("thread_id")
            and origin.get("approved") is True):
        return False
    usage = (row.get("method") == "account/rateLimits/read"
             and classify_usage_failure(row.get("error")) == row.get("class")
             and row.get("class") is not None)
    failure = state.get("transport_failure") or {}
    generic = (transport_failure_owned(state) and row.get("class") == failure.get("class")
               and row.get("error") == failure.get("error") and row.get("method") == failure.get("method"))
    if not usage and not generic:
        return False
    if origin.get("require_active") is True:
        return row.get("require_active") is True and goal.get("status") == "active"
    digest = hashlib.sha256(json.dumps(goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return (goal.get("status") == "paused"
            and row.get("expected_goal_sha256") == origin.get("goal_after_sha256") == digest)


def should_restart(code, state, watchdog=False, stopped=False):
    status = (state.get("goal") or {}).get("status")
    if stopped or status in {
            "complete", "usageLimited", "budgetLimited"}:
        return False
    reason = state.get("stop_reason") or ""
    if any(state.get(key) for key in ("service_hold", "policy_hold", "auth_hold", "billing_hold")):
        return False
    if state.get("transport_uncertain"):
        return False
    for key in ("resume_instruction", "last_instruction"):
        receipt = state.get(key)
        if receipt is not None and (not isinstance(receipt, dict) or receipt.get("status")
                                    in {"sending", "delivery_uncertain", "intent", "uncertain"}):
            return False
    usage_timeout = code == 21 and credit_poll_timeout(state)
    # Hard service/usage stops retain authority even when a crash leaves a stale
    # phase or a transport exit code. Never reset a session to retry these.
    error = state.get("last_error")
    info = error.get("codexErrorInfo") if isinstance(error, dict) else None
    stop_classes = ("quota", "credit", "auth", "policy", "included_usage",
                    "billing", "budget", "usagelimit", "spendcontrol")
    if not usage_timeout and any(word in reason.lower() for word in stop_classes):
        return False
    if isinstance(info, (str, dict)) and any(
            word in json.dumps(info).lower() for word in stop_classes):
        return False
    if usage_timeout:
        local_channel = (classify_usage_failure(state.get("credit_budget_error"))
                         in {"local_disconnected", "local_broken_pipe", "local_connection_reset"}
                         and transport_failure_owned(state)
                         and state["transport_failure"].get("channel_unusable") is True
                         and state["transport_failure"].get("method") == "account/rateLimits/read"
                         and state["transport_failure"].get("class") in
                         {"disconnected", "broken_pipe", "connection_reset"})
        return ((status == "active" and local_channel
                 or status == "paused" and (timeout_pause_owned(state) or timeout_startup_owned(state))
                 or status in {"active", "paused"} and transport_startup_owned(state))
                and isinstance(state.get("thread_id"), str) and bool(state["thread_id"].strip()))
    if code in {21, 22} or reason in {"quota_exhausted", "quota_or_rate_limit",
                                     "needs_user_input", "goal_cleared", "budget_exhausted"}:
        return False
    # A watchdog observation cannot revoke a recorded stop. In particular,
    # signal_* does not prove that this supervisor was the signal's sender.
    if reason == "work_window" or reason.startswith("signal_"):
        return False
    if code in {-signal.SIGINT, -signal.SIGTERM, -signal.SIGHUP} and not watchdog:
        return False
    if (not isinstance(state.get("thread_id"), str) or not state["thread_id"].strip()
            or status not in {"active", "paused", "blocked"}):
        return False
    service = (reason in {"server_error", "turn_failed", "rate_limit"} and code == 23
               and (state.get("transport_failure") or {}).get("class") == "service_transient")
    transport = ((reason in {"launcher_error", "active_goal_did_not_continue"}
                  and (code == 24 or code == 1 and state.get("retryable") is True) or service)
                 and (transport_failure_owned(state) or transport_startup_owned(state)))
    if transport:
        return (status == "active" or status == "paused"
                and (transport_pause_owned(state) or transport_startup_owned(state)))
    if code == 24 or code == 1 and state.get("retryable") is True:
        return False
    if status in {"paused", "blocked"}:
        return reason == "watchdog_recovery" and watchdog and status == "paused"
    if reason in {"server_error", "turn_failed", "rate_limit"}:
        return False  # Current typed service provenance was handled above.
    if reason == "watchdog_recovery":
        return watchdog
    if watchdog:
        return True
    return code < 0 or code == 0 and status == "active"


def restart_delay(initial, restarts):
    """Cap the exponent as well as the delay for months of continuous recovery."""
    return min(initial * 2 ** min(max(restarts - 1, 0), 1023), 60)


def saved_recovery_argv(argv):
    """A communications recovery never archives an unreconciled remote cursor."""
    result = []
    values = iter(argv)
    for value in values:
        if value in {"--fresh-recovery-proof", "--credit-timeout-goal-sha256", "--recovery-goal-sha256"}:
            next(values, None)
        elif value not in {"--fresh-session", "--fresh-on-recovery", "--recovery-require-active"}:
            result.append(value)
    return result


def progress_marker(state, worker_pid):
    if (state.get("worker_pid") == worker_pid and state.get("phase") == "running"
            and (state.get("goal") or {}).get("status") == "active"):
        return state.get("agent_event_count")
    return None


def diagnostics(state, worker_pid):
    """Capture process/resource state without command lines or environment secrets."""
    result = {"state": state, "processes": {}, "resources": {}}
    for name, pid in (("worker", worker_pid), ("server", state.get("server_pid"))):
        if not pid:
            continue
        row = {"pid": pid, "observed_start": process_start(pid)}
        for source in ("status", "wchan"):
            try:
                row[source] = (Path("/proc") / str(pid) / source).read_text()
            except OSError as error:
                row[source + "_error"] = str(error)
        result["processes"][name] = row
    for source in ("meminfo", "loadavg"):
        try:
            result["resources"][source] = (Path("/proc") / source).read_text()
        except OSError as error:
            result["resources"][source + "_error"] = str(error)
    return result


def _linux_pidfd_syscall(number, *arguments):
    # Only the verified Linux x86-64 ABI is supported when Python lacks its
    # pidfd builtins. Numbers: asm/unistd_64.h pidfd_open434/send_signal424.
    if os.name != 'posix':
        raise NotImplementedError('pidfd fallback requires Linux x86_64')
    host = os.uname()
    if host.sysname != 'Linux' or host.machine != 'x86_64' or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise NotImplementedError('pidfd fallback requires Linux x86_64')
    syscall = ctypes.CDLL(None, use_errno=True).syscall
    syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = syscall(ctypes.c_long(number), *arguments)
    if result == -1:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def pidfd_open(pid):
    builtin = getattr(os, 'pidfd_open', None)
    if callable(builtin):
        return builtin(pid, 0)
    return _linux_pidfd_syscall(434, ctypes.c_int(pid), ctypes.c_uint(0))


def pidfd_send_signal(fd, signum):
    builtin = getattr(signal, 'pidfd_send_signal', None)
    if callable(builtin):
        return builtin(fd, signum, None, 0)
    _linux_pidfd_syscall(424, ctypes.c_int(fd), ctypes.c_int(signum), ctypes.c_void_p(None), ctypes.c_uint(0))


def retire_server(state, worker_pid):
    """Retire only the recorded model server through a birth-checked pinned pidfd."""
    pid, birth = state.get("server_pid"), state.get("server_start")
    if pid is None:
        return True
    if (type(pid) is not int or pid <= 0 or not isinstance(birth, str) or not birth.isdigit()
            or state.get("worker_pid") != worker_pid):
        return False
    current = process_start(pid)
    if current is None or current != "unknown" and current != birth:
        return True
    if current == "unknown":
        return False
    try:
        fd = pidfd_open(pid)
    except ProcessLookupError:
        return True
    except (OSError, NotImplementedError):
        return False
    try:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            current = process_start(pid)
            if current == "unknown":
                return False
            if current != birth:
                return True
            try:
                pidfd_send_signal(fd, sig)
            except ProcessLookupError:
                return True
            except OSError:
                return False
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                current = process_start(pid)
                if current == "unknown":
                    return False
                if current != birth:
                    return True
                time.sleep(0.1)
        return False
    finally:
        os.close(fd)


def supervise(args, repo, directory, argv, lease_factory, write_json):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lease = lease_factory(directory / "watch.lock")
    state_path = directory / "state.json"
    watch_path = directory / "watcher.json"
    child = None
    stop_signals = []
    previous_handlers = {}
    started = time.monotonic()
    deadline = started + args.hours * 3600 if args.hours else float("inf")
    restarts = 0
    recovery_proof = None
    timeout_recovery = None
    transport_recovery = None
    recovery_handoff = None
    server_retired = False
    server_retirement_attempted = False
    child_start = None
    last_state = {}
    final_code = 1
    log = (directory / "watcher.jsonl").open("a", buffering=1)

    def record(event, **values):
        data = dict(event=event, at=time.time(), watcher_pid=os.getpid(),
                    watcher_start=process_start(os.getpid()),
                    worker_pid=child.pid if child else None, restarts=restarts,
                    credit_timeout_recovery=timeout_recovery, transport_recovery=transport_recovery,
                    recovery_handoff=recovery_handoff, **values)
        write_json(watch_path, data)
        log.write(json.dumps(data) + "\n")
        details = " ".join(str(key) + "=" + str(value) for key, value in data.items()
                           if key not in {"event", "at", "watcher_pid"})
        print("[os-watch] " + event + " " + details, flush=True)

    def on_signal(signum, frame):
        stop_signals.append(signum)
        if child and child.poll() is None:
            child.send_signal(signum if len(stop_signals) == 1 else signal.SIGKILL)

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        previous_handlers[signum] = signal.signal(signum, on_signal)
    try:
        while not stop_signals:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                final_code = 10
                break
            # An explicit fresh first launch is not authorization to reset every
            # replacement. Fresh recovery has its own opt-in and retirement proof.
            worker_argv = saved_recovery_argv(argv) if restarts else list(argv)
            command = [sys.executable, "-B", str(repo / "scripts/run_os_goal.py"),
                       *worker_argv, "--worker", "--hours", str(remaining / 3600 if args.hours else 0)]
            if restarts:
                command.append("--recovered")
                if timeout_recovery is not None:
                    command.extend(["--credit-timeout-goal-sha256",
                                    timeout_recovery["goal_after_sha256"]])
                origin = transport_recovery or timeout_recovery
                if origin is not None:
                    if origin.get("require_active") is True:
                        command.append("--recovery-require-active")
                    else:
                        command.extend(["--recovery-goal-sha256", origin["goal_after_sha256"]])
            server_retired, server_retirement_attempted = False, False
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, start_new_session=True)
            child_start = process_start(child.pid)
            record("worker_started", attempt=restarts + 1)
            heartbeat = time.monotonic()
            next_notice = heartbeat + args.heartbeat_seconds
            last_mtime = None
            progress_at, last_progress = heartbeat, None
            current = {}
            shutdown_at = None
            killed_at = None
            watchdog = False
            while child.poll() is None:
                now = time.monotonic()
                try:
                    mtime = state_path.stat().st_mtime_ns
                except FileNotFoundError:
                    mtime = None
                if mtime != last_mtime:
                    heartbeat, last_mtime = now, mtime
                    current = snapshot(state_path)
                    if timeout_recovery is not None and progress_marker(current, child.pid) is not None:
                        timeout_recovery = None
                    if transport_recovery is not None and progress_marker(current, child.pid) is not None:
                        transport_recovery = None
                marker = progress_marker(current, child.pid)
                if marker is None or marker != last_progress:
                    progress_at, last_progress = now, marker
                if now >= next_notice:
                    # Keep the supervisor visible during startup, RPC waits and shutdown.
                    print("[os-watch] HEARTBEAT alive; worker_pid=" + str(child.pid)
                          + "; uptime=" + str(int(now - started))
                          + "s; state_updated=" + str(round(now - heartbeat, 1)) + "s ago", flush=True)
                    next_notice = now + args.heartbeat_seconds
                if not shutdown_at:
                    if stop_signals or now >= deadline:
                        if not stop_signals:
                            stop_signals.append(signal.SIGTERM)
                            child.terminate()
                        shutdown_at = now + min(args.grace_seconds + 15, 615)
                    elif (args.watchdog_seconds and now - heartbeat > args.watchdog_seconds
                          or args.stall_seconds and marker is not None and now - progress_at > args.stall_seconds):
                        watchdog = True
                        kind = "heartbeat_stalled" if args.watchdog_seconds and now - heartbeat > args.watchdog_seconds else "agent_progress_stalled"
                        capture = directory / ("watchdog-" + str(child.pid) + "-" + str(time.time_ns()) + ".json")
                        try:
                            write_json(capture, dict(diagnostics(current, child.pid), reason=kind))
                            record(kind, seconds_without_update=now - heartbeat,
                                   seconds_without_agent_event=now - progress_at, diagnostics=str(capture))
                        finally:
                            # A dedicated, authenticated request distinguishes our
                            # checkpoint from an explicit user SIGTERM. Failure
                            # to persist it retains ordinary signal-stop authority.
                            requested = False
                            try:
                                worker_start = process_start(child.pid)
                                watcher_start = process_start(os.getpid())
                                if (not isinstance(worker_start, str) or not worker_start.isdigit()
                                        or not isinstance(watcher_start, str) or not watcher_start.isdigit()):
                                    raise ValueError("Watchdog process identity is unresolved")
                                request = directory / ("watchdog-request-" + str(child.pid)
                                                       + "-" + worker_start + ".json")
                                write_json(request, {"schema_version": 1,
                                    "watcher_pid": os.getpid(), "watcher_start": watcher_start,
                                    "worker_pid": child.pid, "worker_start": worker_start,
                                    "reason": kind})
                                requested = True
                            except (OSError, ValueError) as error:
                                print("[os-watch] Watchdog request unavailable: " + str(error), flush=True)
                            finally:
                                if requested:
                                    child.send_signal(signal.SIGUSR1)
                                else:
                                    child.terminate()
                        shutdown_at = now + min(args.grace_seconds, 30)
                elif now >= shutdown_at and killed_at is None:
                    child.kill()
                    killed_at = now
                    record("worker_forced_stop", grace_expired=True)
                if len(stop_signals) > 1 and killed_at is None:
                    killed_at = now
                if killed_at is not None and now - killed_at >= 5:
                    record("worker_kill_timed_out", recovery_stopped=True)
                    raise RuntimeError("Worker did not exit after SIGKILL; no replacement was started. Inspect watchdog diagnostics.")
                time.sleep(0.25)
            final_code = child.returncode
            state = snapshot(state_path)
            last_state = state
            record("worker_exited", exit_code=final_code, thread_id=state.get("thread_id"),
                   goal_status=(state.get("goal") or {}).get("status"))
            if state.get("worker_pid") != child.pid:
                record("recovery_stopped_worker_snapshot_mismatch", observed_worker_pid=state.get("worker_pid"))
                final_code = 1
                break
            if (not isinstance(child_start, str) or not child_start.isdigit()
                    or state.get("worker_start") != child_start):
                record("recovery_stopped_worker_birth_mismatch", observed_worker_start=state.get("worker_start"))
                final_code = 1
                break
            server_retirement_attempted = True
            server_retired = retire_server(state, child.pid)
            if not server_retired:
                record("recovery_stopped_server_identity_unresolved")
                final_code = 1
                break
            # Never import approval lineage from a saved worker/campaign record.
            state.pop("_credit_timeout_origin", None)
            state.pop("_transport_origin", None)
            origin = transport_recovery or timeout_recovery
            if origin is not None:
                state["_transport_origin"] = dict(origin, watcher_pid=os.getpid(),
                    watcher_start=process_start(os.getpid()))
            if timeout_recovery is not None:
                state["_credit_timeout_origin"] = dict(timeout_recovery,
                    watcher_pid=os.getpid(), watcher_start=process_start(os.getpid()))
            startup = state.get("credit_timeout_startup") or {}
            if (timeout_startup_owned(state) and startup.get("worker_start") != child_start):
                record("recovery_stopped_startup_worker_birth_mismatch")
                final_code = 1
                break
            if (timeout_pause_owned(state) and
                    state["credit_timeout_shutdown_pause"]["worker_start"] != child_start):
                record("recovery_stopped_worker_birth_mismatch")
                final_code = 1
                break
            if ((transport_failure_owned(state) or transport_startup_owned(state))
                    and state.get("worker_start") != child_start):
                record("recovery_stopped_transport_worker_birth_mismatch")
                final_code = 1
                break
            if not should_restart(final_code, state, watchdog, bool(stop_signals)):
                record("recovery_held_classification", exit_code=final_code,
                       stop_reason=state.get("stop_reason"), goal_status=(state.get("goal") or {}).get("status"))
                break
            if timeout_pause_owned(state) and credit_poll_timeout(state):
                timeout_recovery = dict(state["credit_timeout_shutdown_pause"], approved=True)
                transport_recovery = None
            elif transport_pause_owned(state):
                transport_recovery = dict(state["transport_shutdown_pause"], approved=True)
                timeout_recovery = None
            elif transport_startup_owned(state) or timeout_startup_owned(state):
                pass  # Retain only this same watcher's already approved origin.
            else:
                goal = state.get("goal") or {}
                transport_recovery = dict(schema_version=1, approved=True,
                    thread_id=state.get("thread_id"), worker_pid=child.pid, worker_start=child_start,
                    origin_kind=("authenticated_watchdog" if watchdog and goal.get("status") == "paused"
                                 else "active_goal_snapshot"),
                    require_active=goal.get("status") == "active", goal_after=goal,
                    goal_after_sha256=hashlib.sha256(json.dumps(
                        goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
                timeout_recovery = None
            if args.max_restarts >= 0 and restarts >= args.max_restarts:
                record("restart_limit_reached", max_restarts=args.max_restarts)
                break
            try:
                recovery_handoff = str(write_recovery_handoff(repo, directory, state,
                    remaining_seconds=max(0, deadline-time.monotonic()) if args.hours else None))
            except Exception as error:
                record("recovery_held_handoff_failed", error=str(error))
                final_code = 1
                break
            restarts += 1
            recovery_proof = None
            if getattr(args, "fresh_on_recovery", False):
                record("fresh_recovery_suppressed_saved_cursor", thread_id=state.get("thread_id"))
            delay = restart_delay(args.restart_delay, restarts)
            record("restarting_fresh_session" if recovery_proof else "restarting_saved_session",
                   thread_id=state.get("thread_id"), delay_seconds=delay)
            until = min(time.monotonic() + delay, deadline)
            while not stop_signals and time.monotonic() < until:
                time.sleep(max(0, min(0.25, until - time.monotonic())))
        if stop_signals:
            final_code = 10
        record("watcher_stopped", exit_code=final_code)
        return final_code if final_code >= 0 else 1
    except BaseException as error:
        try:
            record("watcher_failed", error=str(error), recovery_held=True)
        except Exception:
            print("[os-watch] Supervisor failed; recovery held: " + str(error), flush=True)
        raise
    finally:
        # Only this direct MODEL child and its exact recorded MODEL server are
        # eligible. Never signal a process group, native owner or descendant tree.
        worker_retired = child is None
        try:
            if child is not None:
                worker_retired = child.poll() is not None
                if not worker_retired and isinstance(child_start, str) and child_start.isdigit():
                    if process_start(child.pid) == child_start:
                        child.terminate()
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            if process_start(child.pid) == child_start:
                                child.kill()
                                try:
                                    child.wait(timeout=5)
                                except subprocess.TimeoutExpired:
                                    pass
                        worker_retired = child.poll() is not None
                if worker_retired and not server_retirement_attempted:
                    try:
                        observed = snapshot(state_path)
                    except Exception:
                        observed = last_state
                    if (observed.get("worker_pid") == child.pid
                            and isinstance(child_start, str) and child_start.isdigit()
                            and observed.get("worker_start") == child_start):
                        last_state = observed
                        server_retirement_attempted = True
                        server_retired = retire_server(observed, child.pid)
            try:
                record("watcher_retirement", worker_retired=worker_retired,
                       server_retirement_attempted=server_retirement_attempted,
                       server_retired=server_retired, recovery_held=not (worker_retired and server_retired),
                       native_release_authorized=False)
            except Exception as error:
                print("[os-watch] Retirement reporting unavailable: " + str(error), flush=True)
            if last_state:
                try:
                    write_recovery_handoff(repo, directory, last_state,
                        remaining_seconds=max(0, deadline-time.monotonic()) if args.hours else None)
                except Exception as error:
                    try:
                        record("terminal_handoff_failed", error=str(error), recovery_held=True)
                    except Exception:
                        print("[os-watch] Terminal handoff failed: " + str(error), flush=True)
        except Exception as error:
            print("[os-watch] Exact model retirement unresolved; recovery held: " + str(error), flush=True)
            try:
                record("watcher_retirement_unresolved", error=str(error), recovery_held=True,
                       native_release_authorized=False)
            except Exception:
                pass
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            log.close()
            lease.close()
