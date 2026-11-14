"""Exact process and recovery receipts shared by the guardian and model worker."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import time
from uuid import uuid4


class EngineLaunchDeferred(RuntimeError):
    """Positive pre-submission busy state; no launch intent or RPC was issued."""


def read_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 4 * 1024 * 1024:
            raise ValueError("Expected owned, bounded regular receipt")
        raw = os.read(fd, info.st_size + 1)
        after = os.fstat(fd)
        if len(raw) != info.st_size or (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Receipt changed while reading")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("Expected receipt object")
        return value
    finally:
        os.close(fd)


def atomic_json(path, value):
    path = Path(path)
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
        base = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(base)
        finally:
            os.close(base)
    finally:
        if fd is not None:
            os.close(fd)
        temporary.unlink(missing_ok=True)


def process_start(pid):
    if type(pid) is not int or pid <= 0:
        return "unknown"
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] in {"Z", "X"} else fields[19]
    except FileNotFoundError:
        return None
    except (OSError, IndexError):
        return "unknown"


def lease_free(directory, name):
    try:
        fd = os.open(Path(directory) / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return True
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Invalid lease destination")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False
    finally:
        os.close(fd)


def signal_exact(pid, birth, signum):
    from watch_os_goal import pidfd_open, pidfd_send_signal
    fd = pidfd_open(pid)
    try:
        if not isinstance(birth, str) or not birth.isdigit() or process_start(pid) != birth:
            raise ValueError("Process birth differs; no signal sent")
        pidfd_send_signal(fd, signum)
    finally:
        os.close(fd)


def goal_digest(goal):
    return hashlib.sha256(json.dumps(goal, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def recovery_blocker(state, *, explicit_user=False):
    """A supervisor repair cannot revoke terminal or uncertain controls."""
    goal = state.get("goal") or {}
    if goal.get("status") in {"complete", "completed", "usageLimited", "budgetLimited"}:
        return "terminal_goal"
    reason = state.get("stop_reason") or ""
    if not isinstance(reason, str):
        return "unknown_stop_reason"
    if reason.startswith("signal_") or reason in {"user_requested", "work_window", "requested_milestones_complete", "goal_cleared", "needs_user_input"}:
        if not explicit_user:
            return "user_or_terminal_stop"
    if any(word in reason.lower() for word in ("policy", "permission", "quota", "usage", "budget", "billing", "credit", "auth")):
        return "account_policy_or_permission_stop"
    if any(state.get(key) for key in ("service_hold", "policy_hold", "auth_hold", "billing_hold", "budget_hold", "permission_hold", "source_hold", "resource_hold", "native_hold", "transport_uncertain", "pending_request")):
        return "binding_hold_or_uncertain_delivery"
    for key in ("resume_instruction", "last_instruction"):
        receipt = state.get(key)
        if receipt and (not isinstance(receipt, dict) or receipt.get("status") not in {"accepted_by_server", "delivered", "completed"}):
            return "instruction_delivery_unreconciled"
    for key in ("last_error", "last_failure"):
        value = state.get(key)
        if value is None:
            continue
        error = value.get("error") if key == "last_failure" and isinstance(value, dict) else value
        provenance = state.get("last_error_provenance") if key == "last_error" else value
        historical = (isinstance(provenance, dict)
                      and (key == "last_failure" or provenance.get("error") == error)
                      and isinstance(provenance.get("log_dir"), str) and state.get("log_dir")
                      and provenance["log_dir"] != state["log_dir"])
        if not historical:
            fields = error if isinstance(error, dict) else {}
            info = str(fields.get("codexErrorInfo") or fields.get("code") or fields.get("error_code") or "").lower()
            message = str(fields.get("message") or "").lower()
            if (any(word in info for word in ("policy", "permission", "quota", "usage", "budget", "billing", "credit", "auth"))
                    or any(word in message for word in ("permission denied", "access denied", "not authenticated"))):
                return "account_policy_or_permission_failure"
            if not explicit_user:
                return "current_or_unattributed_failure"
    return None


def checkpoint_request(directory, state):
    """Read an authenticated guardian request; never infer it from a signal."""
    try:
        guard = read_json(Path(directory) / "guardian.json")
        request = read_json(Path(directory) / "guardian-checkpoint.json")
        run_id = state.get("guardian_run_id")
        if (not isinstance(run_id, str) or request.get("run_id") != run_id or guard.get("run_id") != run_id
                or not isinstance(guard.get("start"), str) or not guard["start"].isdigit()
                or request.get("guardian_pid") != guard.get("pid")
                or request.get("guardian_start") != guard.get("start")
                or process_start(guard.get("pid")) != guard.get("start")
                or lease_free(directory, "guardian.lock")
                or request.get("worker_pid") != os.getpid()
                or request.get("worker_pid") != state.get("worker_pid")
                or request.get("worker_start") != state.get("worker_start")
                or process_start(os.getpid()) != request.get("worker_start")
                or request.get("log_dir") != state.get("log_dir")
                or request.get("thread_id") != state.get("thread_id")
                or not isinstance(request.get("request_id"), str)
                or not isinstance(request.get("expires_at"), (int, float)) or request["expires_at"] < time.time()
                or request.get("reason") != "supervisor_unavailable"
                or recovery_blocker(state)):
            return None
        return request
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def validate_recovery_proof(directory, path, run_id):
    path = Path(path).absolute()
    if path.parent != Path(directory).absolute() or not path.name.startswith("guardian-recovery-"):
        raise ValueError("Recovery proof must be a guardian receipt in the campaign directory")
    proof = read_json(path)
    guard = read_json(Path(directory) / "guardian.json")
    state = read_json(Path(directory) / "state.json")
    final = state.get("guardian_checkpoint") or {}
    if (proof.get("run_id") != run_id or guard.get("run_id") != run_id
            or guard.get("pid") != proof.get("guardian_pid") or guard.get("start") != proof.get("guardian_start")
            or process_start(guard.get("pid")) != guard.get("start") or lease_free(directory, "guardian.lock")
            or proof.get("state_sha256") != goal_digest(state)
            or recovery_blocker(state) or state.get("stop_reason") != "guardian_recovery"
            or state.get("phase") != "stopped" or state.get("active_turns")
            or final.get("request_id") != proof.get("request_id") or final.get("run_id") != run_id
            or proof.get("worker_pid") != state.get("worker_pid") or proof.get("worker_start") != state.get("worker_start")
            or final.get("worker_pid") != state.get("worker_pid") or final.get("worker_start") != state.get("worker_start")
            or state.get("stop_errors") or state.get("server_close_errors")
            or (state.get("goal") or {}).get("status") != "paused"
            or goal_digest(state["goal"]) != proof.get("goal_sha256")
            or proof.get("goal_after") != state.get("goal")
            or proof.get("thread_id") != state.get("thread_id")):
        raise ValueError("Guardian recovery proof does not match a clean checkpoint")
    for name in ("worker", "server"):
        if state.get(name + "_pid") is not None and process_start(state[name + "_pid"]) is not None:
            raise ValueError("Prior model owner not positively retired: " + name)
    if process_start(proof.get("watcher_pid")) is not None or not lease_free(directory, "watch.lock") or not lease_free(directory, "run.lock"):
        raise ValueError("Prior supervisor or model lease remains owned")
    return proof
