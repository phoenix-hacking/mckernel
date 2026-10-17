"""Archive a stopped launcher cursor before an explicitly fresh conversation.

The caller owns run.lock; a recovery caller is the child of the supervisor that
owns watch.lock. This module changes no remote goals and retires no processes.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
from uuid import uuid4


_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_READ = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_MAX_STATE_BYTES = 4 * 1024 * 1024


def _open_directory(stack, parent, name):
    fd = os.open(name, _DIRECTORY, dir_fd=parent)
    stack.callback(os.close, fd)
    return fd


def _base(stack, directory):
    path = Path(directory).absolute()
    if ".." in path.parts:
        raise ValueError("Campaign directory contains parent traversal")
    fd = _open_directory(stack, None, path.anchor)
    for name in path.parts[1:]:
        fd = _open_directory(stack, fd, name)
    if os.fstat(fd).st_uid != os.getuid():
        raise ValueError("Campaign directory is not owned by this user")
    return fd


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(fd, name):
    before = os.stat(name, dir_fd=fd, follow_symlinks=False)
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
            or before.st_size > _MAX_STATE_BYTES):
        raise ValueError("Expected an owned, bounded regular file: " + name)
    stream = os.open(name, _READ, dir_fd=fd)
    try:
        opened = os.fstat(stream)
        if _identity(before) != _identity(opened):
            raise ValueError("File changed while opening: " + name)
        chunks, size = [], 0
        while size <= _MAX_STATE_BYTES:
            chunk = os.read(stream, min(65536, _MAX_STATE_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > _MAX_STATE_BYTES or _identity(opened) != _identity(os.fstat(stream)):
            raise ValueError("File changed while reading: " + name)
        return b"".join(chunks), _identity(opened)
    finally:
        os.close(stream)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def _json(raw):
    value = json.loads(raw, object_pairs_hook=_pairs)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _absent(pid, name, optional=False):
    if pid is None and optional:
        return
    if type(pid) is not int or pid <= 0:
        raise ValueError("Missing or invalid prior " + name + " PID")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return
    except OSError as error:
        raise ValueError("Cannot prove prior " + name + " absent") from error
    raise ValueError("Prior " + name + " is still present")


def _instructions_clear(stack, base, state):
    resume = state.get("resume_instruction")
    if resume is not None and (not isinstance(resume, dict)
            or resume.get("status") != "accepted_by_server"):
        raise ValueError("Resume instruction delivery is unknown or in flight")
    last = state.get("last_instruction")
    if last is not None and (not isinstance(last, dict)
            or last.get("status") != "accepted_by_server"):
        raise ValueError("Instruction delivery is unknown or in flight")
    try:
        control = _open_directory(stack, base, "instructions")
    except FileNotFoundError:
        return
    try:
        sending = _open_directory(stack, control, "sending")
    except FileNotFoundError:
        return
    with os.scandir(sending) as entries:
        if next(entries, None) is not None:
            raise ValueError("Instruction delivery is uncertain; inspect sending/")


def _recovery_allowed(state):
    reason = state.get("stop_reason") or ""
    if not isinstance(reason, str):
        return False
    if reason in {"work_window", "needs_user_input", "goal_cleared", "budget_exhausted"} or reason.startswith("signal_"):
        return False
    if any(word in reason.lower() for word in ("quota", "credit", "auth", "policy", "included_usage")):
        return False
    error = state.get("last_error")
    info = error.get("codexErrorInfo") if isinstance(error, dict) else None
    # Unknown structured failure classifications cannot authorize a new thread.
    if info is not None and info not in ("serverOverloaded", "rateLimitExceeded"):
        return False
    return True


def _validate_proof(base, directory, proof_path, raw, state):
    from watch_os_goal import process_start, should_restart

    if proof_path is None:
        raise ValueError("Fresh recovery requires supervisor classification and retirement proof")
    path = Path(proof_path).absolute()
    if path.parent != Path(directory).absolute():
        raise ValueError("Recovery proof must be in the campaign directory")
    proof_raw, proof_identity = _read(base, path.name)
    proof = _json(proof_raw)
    if (type(proof.get("schema_version")) is not int or proof.get("schema_version") != 1
            or type(proof.get("watcher_pid")) is not int
            or proof.get("watcher_pid") != os.getppid()
            or not isinstance(proof.get("watcher_start"), str)
            or proof["watcher_start"] in {"", "unknown"}
            or process_start(proof["watcher_pid"]) != proof["watcher_start"]
            or type(proof.get("worker_pid")) is not int
            or proof.get("worker_pid") != state.get("worker_pid")
            or proof.get("thread_id") != state.get("thread_id")
            or proof.get("state_sha256") != hashlib.sha256(raw).hexdigest()
            or type(proof.get("exit_code")) is not int
            or type(proof.get("watchdog")) is not bool
            or proof.get("stopped") is not False
            or proof.get("server_retired") is not True):
        raise ValueError("Invalid or stale supervisor recovery proof")
    if not _recovery_allowed(state) or not should_restart(
            proof["exit_code"], state, proof["watchdog"], proof["stopped"]):
        raise ValueError("Recorded stop does not permit automatic fresh recovery")
    return path.name, proof_raw, proof_identity


def validate_prepared_fresh_session(directory: Path, repo: Path, state=None,
                                    *, expected_objective=None) -> dict:
    """Validate an already published fresh seed against its immutable archive."""
    directory = Path(directory).absolute()
    with ExitStack() as stack:
        base = _base(stack, directory)
        saved = _json(_read(base, "state.json")[0])
        if state is not None and saved != state:
            raise ValueError("Prepared fresh state changed during validation")
        previous = saved.get("previous_session")
        if (type(saved.get("schema_version")) is not int or saved.get("schema_version") != 1
                or saved.get("repo") != str(repo) or saved.get("thread_id") is not None
                or not isinstance(previous, dict)
                or not isinstance(previous.get("state_path"), str)):
            raise ValueError("State is not a prepared fresh session")
        path = Path(previous["state_path"])
        if (not path.is_absolute() or path.name != "state.json"
                or path.parent.parent != directory / "session-archives"
                or path.parent.name in {"", ".", ".."}):
            raise ValueError("Prepared fresh archive is outside the session namespace")
        archives = _open_directory(stack, base, "session-archives")
        archive = _open_directory(stack, archives, path.parent.name)
        old = _json(_read(archive, "state.json")[0])
        goal = old.get("goal")
        if (type(old.get("schema_version")) is not int or old.get("schema_version") != 1
                or old.get("repo") != str(repo)
                or not isinstance(old.get("thread_id"), str) or not old["thread_id"].strip()
                or old["thread_id"] != previous.get("thread_id")
                or not isinstance(goal, dict) or not isinstance(goal.get("objective"), str)
                or not goal["objective"].strip()
                or goal.get("status") != previous.get("goal_status")
                or old.get("stop_reason") != previous.get("stop_reason")
                or (expected_objective is not None and goal["objective"] != expected_objective)):
            raise ValueError("Prepared fresh archive ownership or metadata does not match")
        return saved


def prepare_fresh_session(directory: Path, repo: Path, write_json, recovery: bool = False,
                          *, recovery_proof=None, expected_objective=None) -> dict:
    """Durably retain exact state.json bytes, then atomically install schema 1.

    ``write_json`` must atomically replace and fsync its target, as atomic_json
    does. A recovery proof is an immutable supervisor-owned JSON file in the
    campaign directory, bound to the exact old cursor and the live parent.
    Historical logs, queues, budgets, goals and runtime files stay untouched.
    All ordinary validation precedes any filesystem mutation. Failed publication
    may leave an unreferenced archive, which remains useful recovery evidence.
    """
    if type(recovery) is not bool or not callable(write_json):
        raise ValueError("Expected a recovery boolean and atomic JSON writer")
    if not recovery and recovery_proof is not None:
        raise ValueError("Supervisor recovery proof requires recovery mode")
    if expected_objective is not None and (not isinstance(expected_objective, str)
            or not expected_objective.strip()):
        raise ValueError("Expected objective must be a nonempty string")
    directory, repo = Path(directory).absolute(), Path(repo)
    with ExitStack() as stack:
        base = _base(stack, directory)
        raw, identity = _read(base, "state.json")
        state = _json(raw)
        if state.get("thread_id") is None and state.get("previous_session"):
            validate_prepared_fresh_session(directory, repo, state, expected_objective=expected_objective)
            for name in ("worker", "server"):
                if state.get(name + "_pid") is not None:
                    _absent(state[name + "_pid"], name)
            _instructions_clear(stack, base, state)
            if recovery:
                _validate_proof(base, directory, recovery_proof, raw, state)
            if _read(base, "state.json") != (raw, identity):
                raise ValueError("Prepared fresh state changed before reuse")
            return state
        goal = state.get("goal")
        if (type(state.get("schema_version")) is not int or state.get("schema_version") != 1
                or state.get("repo") != str(repo)
                or not isinstance(state.get("thread_id"), str) or not state["thread_id"].strip()
                or not isinstance(goal, dict)
                or not isinstance(goal.get("objective"), str) or not goal["objective"].strip()
                or not isinstance(goal.get("status"), str)
                or goal["status"] not in {"active", "paused", "blocked"}
                or (state.get("stop_reason") is not None
                    and not isinstance(state["stop_reason"], str))):
            raise ValueError("Fresh session requires an owned unfinished saved goal and supported schema")
        if not recovery and (state.get("phase") != "stopped" or goal["status"] not in {"paused", "blocked"}):
            raise ValueError("Explicit fresh session requires a stopped paused or blocked campaign")
        if expected_objective is not None and goal["objective"] != expected_objective:
            raise ValueError("Saved goal belongs to a different objective")
        _absent(state.get("worker_pid"), "worker")
        if "server_pid" not in state:
            raise ValueError("Missing prior server identity")
        _absent(state["server_pid"], "server", optional=True)
        _instructions_clear(stack, base, state)
        proof = _validate_proof(base, directory, recovery_proof, raw, state) if recovery else None
        # Validate existing archive namespace before any mkdir or state change.
        try:
            archives = _open_directory(stack, base, "session-archives")
        except FileNotFoundError:
            archives = None
        if _read(base, "state.json") != (raw, identity):
            raise ValueError("Saved state changed before archival")
        if archives is None:
            os.mkdir("session-archives", 0o700, dir_fd=base)
            os.fsync(base)
            archives = _open_directory(stack, base, "session-archives")
        ident = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex
        os.mkdir(ident, 0o700, dir_fd=archives)
        archive = _open_directory(stack, archives, ident)
        stream = os.open("state.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=archive)
        try:
            view = memoryview(raw)
            while view:
                written = os.write(stream, view)
                if written <= 0:
                    raise OSError("Could not write session archive")
                view = view[written:]
            os.fsync(stream)
        finally:
            os.close(stream)
        os.fsync(archive)
        os.fsync(archives)
        fresh = {"schema_version": 1, "repo": str(repo), "thread_id": None,
                 "created_at": datetime.now(timezone.utc).isoformat(),
                 "previous_session": {
                     "state_path": str(directory / "session-archives" / ident / "state.json"),
                     "thread_id": state["thread_id"], "goal_status": goal["status"],
                     "stop_reason": state.get("stop_reason")}}
        if "last_rate_limits" in state:
            fresh["last_rate_limits"] = state["last_rate_limits"]
        _instructions_clear(stack, base, state)
        if _read(base, "state.json") != (raw, identity):
            raise ValueError("Saved state changed before fresh publication; archive retained")
        if proof and _read(base, proof[0]) != (proof[1], proof[2]):
            raise ValueError("Recovery proof changed before publication; archive retained")
        _absent(state.get("worker_pid"), "worker")
        _absent(state["server_pid"], "server", optional=True)
        if recovery:
            _validate_proof(base, directory, recovery_proof, raw, state)
        # Anchor the callback to the already verified directory even if an
        # ancestor pathname is renamed during archival.
        write_json(Path("/proc/self/fd") / str(base) / "state.json", fresh)
        return fresh
