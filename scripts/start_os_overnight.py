#!/usr/bin/env python3
"""Start the guarded McKernel user service through the existing launcher name.

The CLI now uses an independently watched guardian and GitHub mailbox. Legacy
receipt helpers remain available for inspecting an already detached invocation.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time
from uuid import uuid4

from os_goal_stop_log import write_stop_record


LATEST = "overnight-latest.json"


def process_identity(pid):
    if type(pid) is not int or pid <= 0:
        return None
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    fields = raw[raw.rindex(")") + 2:].split()
    if fields[0] in {"Z", "X"}:
        return None
    return {"pid": pid, "start": fields[19], "session": int(fields[3]),
            "ppid": int(fields[1]), "state": fields[0]}


def _read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Expected a regular JSON file: " + str(path))
        with os.fdopen(fd, "r") as stream:
            fd = None
            text = stream.read(2 * 1024 * 1024 + 1)
        if len(text) > 2 * 1024 * 1024:
            raise ValueError("Oversized status file")
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError("Expected JSON object")
        return result
    finally:
        if fd is not None:
            os.close(fd)


def _save(path, value):
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            fd = None
            json.dump(value, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        temporary.unlink(missing_ok=True)


def lease_held(directory, name):
    try:
        fd = os.open(Path(directory) / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Unsafe lease file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return False
        except BlockingIOError:
            return True
    finally:
        os.close(fd)


def build_command(repo, *, python=None, inhibit=None, taskset=None):
    repo = Path(repo).resolve()
    inhibit = inhibit or shutil.which("systemd-inhibit")
    taskset = taskset or shutil.which("taskset")
    if not inhibit or not taskset:
        raise RuntimeError("systemd-inhibit and taskset are required; no uninhibited fallback")
    return [str(inhibit), "--what=idle:sleep", "--mode=block",
            "--who=McKernel", "--why=Finish original M14 and M15 while the workstation is idle",
            "--", str(taskset), "-c", "0,6,7", str(python or sys.executable), "-B",
            str(repo / "scripts/run_os_goal.py"), "--hours", "0", "--max-restarts", "-1",
            "--repair-agent-failures", "--stop-after-m14-m15", "--profile", "aggressive",
            "--max-agents", "2", "--build-jobs", "3", "--memory-gib", "4",
            "--startup-instruction-file", str(repo / "scripts/m14-m15-overnight-instruction.txt"),
            "--agent-windows", "off"]


def status(directory, receipt=None):
    directory = Path(directory)
    try:
        receipt = _read(directory / LATEST) if receipt is None else dict(receipt)
    except FileNotFoundError:
        return {"status": "NOT_STARTED"}
    except (OSError, ValueError) as error:
        return {"status": "UNKNOWN", "reason": str(error)}
    result = {key: receipt.get(key) for key in ("attempt_id", "log_path", "receipt_path", "launch_pid")}
    try:
        if type(receipt.get("launch_pid")) is not int or receipt["launch_pid"] <= 0:
            return dict(result, status="FAILED" if receipt.get("status") == "FAILED" else "UNKNOWN",
                        reason=receipt.get("error") or "Pending launch has no verified identity; reconcile before another start")
        launch = process_identity(receipt.get("launch_pid"))
        if not launch:
            result.update(status="FAILED" if receipt.get("status") == "FAILED" else "EXITED",
                          reason=receipt.get("error") or "Detached launcher is no longer live")
            return result
        if (launch["start"] != receipt.get("launch_start")
                or launch["session"] != receipt.get("launch_session")
                or receipt.get("launch_session") != receipt.get("launch_pid")):
            return dict(result, status="UNKNOWN", reason="Detached launch identity differs")
        result.update(status="STARTING", launch_start=launch["start"], launch_session=launch["session"])
        try:
            watch = _read(directory / "watcher.json")
        except FileNotFoundError:
            return result
        watcher = process_identity(watch.get("watcher_pid"))
        if not watcher or watcher["start"] != watch.get("watcher_start") or watcher["session"] != launch["session"]:
            return result
        result.update(watcher_pid=watcher["pid"], watcher_start=watcher["start"], watcher_verified=True)
        try:
            worker_state = _read(directory / "state.json")
        except FileNotFoundError:
            return result
        worker = process_identity(worker_state.get("worker_pid"))
        if (not worker or worker["pid"] != watch.get("worker_pid")
                or worker["start"] != worker_state.get("worker_start")
                or worker["ppid"] != watcher["pid"]):
            return result
        result.update(worker_pid=worker["pid"], worker_start=worker["start"],
                      phase=worker_state.get("phase"), goal_status=(worker_state.get("goal") or {}).get("status"))
        if worker_state.get("stop_reason") or worker_state.get("stop_now") or worker_state.get("checkpoint_requested"):
            return dict(result, status="STOPPING", reason=worker_state.get("stop_reason"))
        if not lease_held(directory, "watch.lock") or not lease_held(directory, "run.lock"):
            return result
        if result["phase"] == "running" and result["goal_status"] == "active":
            result["status"] = "ACTIVE"
        elif result["phase"] == "waiting_for_input" and result["goal_status"] == "blocked":
            result["status"] = "WAITING"
        return result
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        return dict(result, status="UNKNOWN", reason="Identity/status verification failed: " + str(error))


def _persist(directory, receipt):
    _save(Path(receipt["receipt_path"]), receipt)
    _save(Path(directory) / LATEST, receipt)


def start(repo, directory, *, wait_seconds=5):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_fd = os.open(directory / "overnight-start.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "EXISTING_OWNER", "reason": "Another overnight start is being verified"}
        if lease_held(directory, "watch.lock") or lease_held(directory, "run.lock"):
            return {"status": "EXISTING_OWNER", "reason": "Existing watcher or worker owns the campaign; no duplicate started"}
        previous = status(directory)
        if previous["status"] not in {"NOT_STARTED", "EXITED", "FAILED"}:
            return dict(previous, status="EXISTING_OWNER", reason="Prior detached attempt remains live or unresolved; no duplicate started")
        attempt_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
        attempt = directory / "overnight" / attempt_id
        attempt.mkdir(mode=0o700, parents=True)
        receipt = {"attempt_id": attempt_id, "launched_at": datetime.now(timezone.utc).isoformat(),
                   "status": "STARTING", "log_path": str(attempt / "overnight.log"),
                   "receipt_path": str(attempt / "receipt.json"), "launch_pid": None,
                   "launch_start": None, "launch_session": None}
        _persist(directory, receipt)
        child = None
        spawn_attempted = False
        log_fd = None
        log = None
        try:
            log_fd = os.open(receipt["log_path"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            log = os.fdopen(log_fd, "ab", buffering=0)
            log_fd = None
            receipt["command"] = build_command(repo)
            spawn_attempted = True
            child = subprocess.Popen(receipt["command"], cwd=repo, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                     close_fds=True)
            receipt["launch_pid"] = child.pid
            identity = process_identity(child.pid)
            if not identity or identity["session"] != child.pid:
                raise RuntimeError("Detached launch identity unavailable; do not start another attempt blindly")
            receipt.update(launch_start=identity["start"], launch_session=identity["session"])
            _persist(directory, receipt)
            deadline = time.monotonic() + wait_seconds
            while True:
                code = child.poll()
                if code is not None:
                    raise RuntimeError("Overnight command exited during startup with code " + str(code) + "; inspect log")
                result = status(directory, receipt)
                if result["status"] in {"ACTIVE", "WAITING"} or time.monotonic() >= deadline:
                    receipt["status"] = result["status"]
                    _persist(directory, receipt)
                    return result
                time.sleep(0.2)
        except (OSError, ValueError, RuntimeError) as error:
            receipt.update(status="FAILED" if (not spawn_attempted or
                           child is not None and child.poll() is not None) else "UNKNOWN", error=str(error))
            _persist(directory, receipt)
            if log is not None:
                try:
                    log.write(("Overnight start: " + str(error) + "\n").encode())
                except (OSError, ValueError):
                    pass
            try:
                write_stop_record(directory, {"log_dir": str(attempt), "invocation": attempt_id},
                                  event="overnight_start_failed", reason="launcher_error", error=error)
            except (OSError, ValueError, TypeError):
                pass
            return {"status": receipt["status"], "reason": str(error),
                    "log_path": receipt["log_path"], "receipt_path": receipt["receipt_path"]}
        finally:
            try:
                if log is not None:
                    log.close()
                elif log_fd is not None:
                    os.close(log_fd)
            except (OSError, ValueError):
                pass
    finally:
        os.close(lock_fd)


def stop(directory):
    result = status(directory)
    if not result.get("watcher_verified"):
        return dict(result, status="REFUSED", reason="No exact live watcher for this detached attempt; no signal sent")
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        return dict(result, status="REFUSED", reason="This host cannot provide identity-safe pidfd stop; no signal sent")
    fd = None
    try:
        fd = os.pidfd_open(result["watcher_pid"])
        identity = process_identity(result["watcher_pid"])
        if (not identity or identity["start"] != result["watcher_start"]
                or identity["session"] != result["launch_session"]):
            return dict(result, status="REFUSED", reason="Watcher identity changed; no signal sent")
        signal.pidfd_send_signal(fd, signal.SIGTERM, None, 0)
    except OSError as error:
        return dict(result, status="REFUSED", reason="Identity-safe watcher stop failed: " + str(error))
    finally:
        if fd is not None:
            os.close(fd)
    return dict(result, status="STOP_REQUESTED", reason="SIGTERM sent only to the verified watcher; checkpoint/join remains in progress")


def launch_legacy(arguments):
    """Preserve run_os_goal.py flags while replacing its old foreground launcher."""
    from os_goal_service import main as service_main
    return service_main(["start"], engine_arguments=list(arguments))


def main(argv=None):
    from os_goal_service import main as service_main
    return service_main(argv)


if __name__ == "__main__":
    sys.exit(main())
