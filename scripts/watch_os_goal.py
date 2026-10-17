"""Supervise the OS runner and preserve its work window across crashes."""

import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time


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


def should_restart(code, state, watchdog=False, stopped=False):
    status = (state.get("goal") or {}).get("status")
    if stopped or status in {
            "complete", "usageLimited", "budgetLimited"}:
        return False
    reason = state.get("stop_reason") or ""
    # Hard service/usage stops retain authority even when a crash leaves a stale
    # phase or a transport exit code. Never reset a session to retry these.
    error = state.get("last_error")
    info = error.get("codexErrorInfo") if isinstance(error, dict) else None
    stop_classes = ("quota", "credit", "auth", "policy", "included_usage")
    if any(word in reason.lower() for word in stop_classes):
        return False
    if isinstance(info, (str, dict)) and any(
            word in json.dumps(info).lower() for word in stop_classes):
        return False
    if code in {21, 22} or reason in {"quota_exhausted", "quota_or_rate_limit",
                                     "needs_user_input", "goal_cleared", "budget_exhausted"}:
        return False
    # A watchdog observation cannot revoke a recorded stop. In particular,
    # signal_* does not prove that this supervisor was the signal's sender.
    if reason == "work_window" or reason.startswith("signal_"):
        return False
    if code in {-signal.SIGINT, -signal.SIGTERM, -signal.SIGHUP} and not watchdog:
        return False
    if reason in {"server_error", "turn_failed"}:
        return isinstance(info, str) and info in {"serverOverloaded", "rateLimitExceeded"}
    if reason == "rate_limit":
        return True
    if reason == "watchdog_recovery":
        return watchdog
    # Transport recovery may pause the goal during shutdown. Recover only from
    # its positive classification, never from paused/blocked status alone.
    if code == 24 or code == 1 and state.get("retryable") is True:
        return True
    if status in {"paused", "blocked"}:
        return False
    if watchdog:
        return True
    return code < 0 or code == 0 and status == "active"


def restart_delay(initial, restarts):
    """Cap the exponent as well as the delay for months of continuous recovery."""
    return min(initial * 2 ** min(max(restarts - 1, 0), 1023), 60)


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


def retire_server(state, worker_pid):
    """Stop only the exact app-server process recorded by the exited worker."""
    pid, birth = state.get("server_pid"), state.get("server_start")
    if not pid:
        return True
    current = process_start(pid)
    if current is None or current != "unknown" and birth and current != birth:
        return True
    if state.get("worker_pid") != worker_pid or not birth or current == "unknown":
        return False
    for sig in (signal.SIGTERM, signal.SIGKILL):
        current = process_start(pid)
        if current == "unknown":
            return False
        if current != birth:
            return True
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return True
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            current = process_start(pid)
            if current == "unknown":
                return False
            if current != birth:
                return True
            time.sleep(0.1)
    return False


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
    final_code = 1
    log = (directory / "watcher.jsonl").open("a", buffering=1)

    def record(event, **values):
        data = dict(event=event, at=time.time(), watcher_pid=os.getpid(),
                    worker_pid=child.pid if child else None, restarts=restarts, **values)
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
            worker_argv = [value for value in argv if not (restarts and value == "--fresh-session")]
            command = [sys.executable, "-B", str(repo / "scripts/run_os_goal.py"),
                       *worker_argv, "--worker", "--hours", str(remaining / 3600 if args.hours else 0)]
            if restarts:
                command.append("--recovered")
                if recovery_proof is not None:
                    command.extend(["--fresh-recovery-proof", str(recovery_proof)])
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, start_new_session=True)
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
            record("worker_exited", exit_code=final_code, thread_id=state.get("thread_id"),
                   goal_status=(state.get("goal") or {}).get("status"))
            if state.get("worker_pid") != child.pid:
                record("recovery_stopped_worker_snapshot_mismatch", observed_worker_pid=state.get("worker_pid"))
                final_code = 1
                break
            if not retire_server(state, child.pid):
                record("recovery_stopped_server_identity_unresolved")
                final_code = 1
                break
            if not should_restart(final_code, state, watchdog, bool(stop_signals)):
                break
            if args.max_restarts >= 0 and restarts >= args.max_restarts:
                record("restart_limit_reached", max_restarts=args.max_restarts)
                break
            restarts += 1
            recovery_proof = None
            saved_goal = state.get("goal")
            has_saved_goal = (isinstance(state.get("thread_id"), str) and bool(state["thread_id"].strip())
                              and isinstance(saved_goal, dict)
                              and saved_goal.get("status") in {"active", "paused", "blocked"})
            if getattr(args, "fresh_on_recovery", False) and has_saved_goal:
                # The worker verifies this receipt under run.lock before archiving
                # state. It binds the exact exited worker snapshot to this live
                # supervisor, after both restart classification and retirement.
                recovery_proof = directory / ("fresh-recovery-" + str(os.getpid())
                                               + "-" + str(time.time_ns()) + ".json")
                write_json(recovery_proof, {
                    "schema_version": 1, "watcher_pid": os.getpid(),
                    "watcher_start": process_start(os.getpid()),
                    "worker_pid": child.pid, "thread_id": state.get("thread_id"),
                    "state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
                    "exit_code": final_code, "watchdog": watchdog, "stopped": False,
                    "server_retired": True,
                })
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
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("[os-watch] Worker is still present after SIGKILL; recovery stopped.", flush=True)
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        log.close()
        lease.close()
