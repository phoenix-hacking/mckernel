"""Read-only saved-campaign and Codex writer readiness; no writer handoff.

Functional McKernel OS/apps and Rust/allowed assembly; NO SECURITY TESTING.
The probe releases only its own temporary flock. It never creates or removes a
writer file, signals an owner, or establishes runtime cleanup or model authority.
"""
import fcntl
import os
from pathlib import Path
import stat

from os_goal_guard_protocol import read_json


SAVED_ROOT = "01a18bc3-e072-7810-9426-75101b0856c0"


def _holder_pids(info, proc_locks):
    """Match granted FLOCK holders by both device and inode; ignore waiters."""
    try:
        lines = Path(proc_locks).read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return []
    holders = set()
    for line in lines:
        fields = line.split()
        if len(fields) < 6 or fields[1] != "FLOCK":
            continue
        try:
            major, minor, inode = fields[5].split(":")
            if (int(major, 16), int(minor, 16), int(inode)) != (
                    os.major(info.st_dev), os.minor(info.st_dev), info.st_ino):
                continue
            pid = int(fields[4])
            if pid > 0:
                holders.add(pid)
        except ValueError:
            continue
    return sorted(holders)


def probe_writer_lock(*, codex_home=None, proc_locks="/proc/locks"):
    """Observe the exact saved Root's existing lock, without creating a path.

    A free observation is not a reservation: the actual thread/resume RPC must
    still handle another writer winning the race after this descriptor closes.
    """
    home = Path(codex_home) if codex_home is not None else Path(
        os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    path = home.expanduser() / "thread-writer-locks" / (SAVED_ROOT + ".lock")
    result = {"thread_id": SAVED_ROOT, "lock_path": str(path),
              "holder_pids": [], "holder_pid": None}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except FileNotFoundError:
        return dict(result, status="WRITER_READY", lock_present=False)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError("Saved Root writer lock is not an owned regular file: " + str(path))
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held = False
        except BlockingIOError:
            held = True
        named = path.lstat()
        if (named.st_dev, named.st_ino) != (info.st_dev, info.st_ino):
            raise RuntimeError("Saved Root writer lock changed during readiness observation: " + str(path))
        holders = _holder_pids(info, proc_locks) if held else []
        return dict(result, status="WRITER_HELD" if held else "WRITER_READY",
                    lock_present=True, device_major=os.major(info.st_dev),
                    device_minor=os.minor(info.st_dev), inode=info.st_ino,
                    holder_pids=holders, holder_pid=holders[0] if len(holders) == 1 else None)
    finally:
        os.close(fd)


def require_saved_writer_ready(directory, *, expected_repo, expected_objective,
                               codex_home=None, proc_locks="/proc/locks"):
    """Require the saved campaign before any launcher readiness or submission."""
    state_path = Path(directory) / "state.json"
    try:
        state = read_json(state_path)
    except (OSError, ValueError) as error:
        raise RuntimeError("Saved M14/M15 campaign is missing or unreadable; no new goal or controller "
                           "was started: " + str(state_path)) from error
    goal = state.get("goal")
    if (state.get("thread_id") != SAVED_ROOT or not isinstance(goal, dict)
            or goal.get("threadId", SAVED_ROOT) != SAVED_ROOT
            or goal.get("objective") != expected_objective
            or state.get("repo") != str(Path(expected_repo).resolve())):
        raise RuntimeError("Saved campaign does not match the M14/M15 Root/objective/checkout; "
                           "no new goal or controller was started")
    result = probe_writer_lock(codex_home=codex_home, proc_locks=proc_locks)
    if result["status"] == "WRITER_HELD":
        holders = ",".join(str(pid) for pid in result["holder_pids"]) or "unavailable"
        raise RuntimeError("Saved Root " + SAVED_ROOT + " already has an active writer; holder PID="
                           + holders + "; device={:x}:{:x}; inode={}; lock={}. "
                           "No controller was submitted; the existing writer needs its actual orderly handoff."
                           .format(result["device_major"], result["device_minor"], result["inode"],
                                   result["lock_path"]))
    return result
