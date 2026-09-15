"""Supervise the OS runner; preserve its thread and work window across crashes."""

import json
import os
from pathlib import Path
import signal
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


def should_restart(code, state, watchdog=False, stopped=False):
    if stopped or (state.get("goal") or {}).get("status") in {
            "complete", "blocked", "usageLimited", "budgetLimited"}:
        return False
    if watchdog:
        return True
    if code in {0, 10, 20, 21, 22, 23}:
        return False
    return code < 0 or code == 24 or code == 1 and state.get("retryable") is True


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
    final_code = 1
    log = (directory / "watcher.jsonl").open("a", buffering=1)

    def record(event, **values):
        data = dict(event=event, at=time.time(), watcher_pid=os.getpid(),
                    worker_pid=child.pid if child else None, restarts=restarts, **values)
        write_json(watch_path, data)
        log.write(json.dumps(data) + "\n")
        print("[os-watch] " + event, flush=True)

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
            command = [sys.executable, "-B", str(repo / "scripts/run_os_goal.py"),
                       *argv, "--worker", "--hours", str(remaining / 3600 if args.hours else 0)]
            if restarts:
                command.append("--recovered")
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, start_new_session=True)
            record("worker_started", attempt=restarts + 1)
            heartbeat = time.monotonic()
            last_mtime = None
            shutdown_at = None
            watchdog = False
            while child.poll() is None:
                now = time.monotonic()
                try:
                    mtime = state_path.stat().st_mtime_ns
                except FileNotFoundError:
                    mtime = None
                if mtime != last_mtime:
                    heartbeat, last_mtime = now, mtime
                if not shutdown_at:
                    if stop_signals or now >= deadline:
                        if not stop_signals:
                            stop_signals.append(signal.SIGTERM)
                            child.terminate()
                        shutdown_at = now + min(args.grace_seconds + 15, 615)
                    elif args.watchdog_seconds and now - heartbeat > args.watchdog_seconds:
                        watchdog = True
                        record("heartbeat_stalled", seconds_without_update=now - heartbeat)
                        child.terminate()
                        shutdown_at = now + 30
                elif now >= shutdown_at:
                    child.kill()
                time.sleep(0.25)
            final_code = child.returncode
            state = snapshot(state_path)
            record("worker_exited", exit_code=final_code, thread_id=state.get("thread_id"),
                   goal_status=(state.get("goal") or {}).get("status"))
            if not retire_server(state, child.pid):
                record("recovery_stopped_server_identity_unresolved")
                final_code = 1
                break
            if not should_restart(final_code, state, watchdog, bool(stop_signals)):
                break
            if restarts >= args.max_restarts:
                record("restart_limit_reached", max_restarts=args.max_restarts)
                break
            restarts += 1
            delay = min(args.restart_delay * (2 ** (restarts - 1)), 60)
            record("restarting_saved_session", thread_id=state.get("thread_id"), delay_seconds=delay)
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
                child.wait(timeout=5)
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        log.close()
        lease.close()
