#!/usr/bin/env python3
"""Independent storage-fault-v2 owner supervisor (source candidate only)."""
import argparse
import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import select
import signal
import stat
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER = (HERE / "witness_owner.py").resolve()
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37
PREFLIGHT_NS = 5_000_000_000
OWNER_WAIT_NS = 220_000_000_000
CLEANUP_NS = 22_000_000_000
PUBLICATION_NS = 6_000_000_000
TOTAL_NS = 248_000_000_000
PREFLIGHT_TOTAL_NS = 33_000_000_000
STREAM_LIMIT = 1 << 20
OWNED_SCAN_PID_LIMIT = 4096
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX32 = re.compile(r"[0-9a-f]{32}")

class PreflightFailure(RuntimeError):
    def __init__(self, stage, error, sentinel_pid=None, sentinel_wait=None,
                 sigchld_default=False, authority_lost=False, trigger_ns=None):
        super().__init__(str(error) or "<empty-%s>" % type(error).__name__)
        if trigger_ns is not None and \
                (type(trigger_ns) is not int or trigger_ns <= 0):
            raise ValueError("preflight failure trigger")
        self.stage = stage
        self.original = error
        self.sentinel_pid = sentinel_pid
        self.sentinel_wait = sentinel_wait
        self.sigchld_default = sigchld_default
        self.authority_lost = authority_lost
        self.trigger_ns = trigger_ns

class PipeOverflow(ValueError):
    """A stream exceeded its retained prefix, but was drained as far as possible."""
    def __init__(self, retained, eof):
        super().__init__("owner stream overflow")
        self.retained, self.eof = retained, eof

class EChildAuthority(RuntimeError):
    """ECHILD is terminal: no later identity-derived signal is authorized."""

def attach_secondary(primary, secondary):
    values = getattr(primary, "_supervisor_secondary", None)
    if values is None:
        values = []
        primary._supervisor_secondary = values
    values.append(secondary)

def strict(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite")))

def complete_write(fd, raw, deadline_ns=None):
    view = memoryview(raw)
    while view:
        check_deadline(deadline_ns, "supervisor publication deadline")
        try:
            count = os.write(fd, view)
        except InterruptedError:
            continue
        if count <= 0:
            raise OSError("short supervisor write")
        view = view[count:]
    check_deadline(deadline_ns, "supervisor publication deadline")

def stable_bytes(path, limit=1 << 26):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("canonical supervisor input")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    primary = None
    result = None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("bounded regular supervisor input")
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                raise OSError("short supervisor input")
            chunks.append(chunk); remaining -= len(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != \
           (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise OSError("supervisor input changed")
        result = b"".join(chunks)
    except Exception as error:
        primary = error
    try:
        os.close(fd)
    except Exception as close_error:
        if primary is None:
            raise
        primary._supervisor_secondary = [close_error]
    if primary is not None:
        raise primary
    return result

def process_identity(pid):
    raw = Path("/proc/%d/stat" % pid).read_bytes()
    close = raw.rfind(b")")
    fields = raw[close + 2:].split() if close >= 0 else []
    open_paren = raw[:close + 1].find(b"(") if close >= 0 else -1
    if open_paren < 1 or len(fields) < 20:
        raise ValueError("proc stat")
    value = {"pid": int(raw[:open_paren - 1]), "ppid": int(fields[1]),
             "startticks": int(fields[19])}
    if any(type(value[key]) is not int or value[key] <= 0 for key in value):
        raise ValueError("proc stat identity")
    return value

def observe_identity(pid):
    now = time.monotonic_ns()
    try:
        value = process_identity(pid)
    except FileNotFoundError:
        return {"observation": "missing", "pid": pid, "ppid": None,
                "startticks": None, "monotonic_ns": now}
    except (OSError, ValueError):
        return {"observation": "error", "pid": pid, "ppid": None,
                "startticks": None, "monotonic_ns": now}
    if value["pid"] != pid:
        return {"observation": "error", "pid": pid, "ppid": None,
                "startticks": None, "monotonic_ns": now}
    return {"observation": "observed", "pid": value["pid"],
            "ppid": value["ppid"], "startticks": value["startticks"],
            "monotonic_ns": now}

def normalized_error(error, stage=None):
    name = type(error).__name__
    value = {"type": name, "message": str(error) or "<empty-%s>" % name,
             "errno": error.errno if isinstance(error, OSError) and
             type(error.errno) is int and error.errno > 0 else None}
    if stage is not None:
        value = {"stage": stage, **value}
    return value

def classify_owner(pid, supervisor_pid, observations, spawn_error=None,
                   preflight_failure=None):
    if preflight_failure is not None:
        return {"state": "NOT_SPAWNED", "pid": None, "ppid": None,
                "startticks": None, "spawn_error": None}
    if spawn_error is not None:
        return {"state": "SPAWN_FAILED", "pid": None, "ppid": None,
                "startticks": None, "spawn_error": normalized_error(spawn_error)}
    if type(pid) is not int or pid <= 0 or type(supervisor_pid) is not int or \
            supervisor_pid <= 0 or type(observations) is not list or \
            len(observations) > 2:
        raise ValueError("owner identity classification")
    observed = [item for item in observations if item.get("observation") == "observed"]
    if any(type(item) is not dict or set(item) != {
            "observation", "pid", "ppid", "startticks", "monotonic_ns"} or
            item["observation"] not in ("observed", "missing", "error") or
            type(item["pid"]) is not int or item["pid"] <= 0 or
            type(item["monotonic_ns"]) is not int or item["monotonic_ns"] <= 0 or
            (item["observation"] == "observed" and
             (type(item["ppid"]) is not int or item["ppid"] <= 0 or
              type(item["startticks"]) is not int or item["startticks"] <= 0)) or
            (item["observation"] != "observed" and
             (item["ppid"] is not None or item["startticks"] is not None))
            for item in observations):
        raise ValueError("owner identity observation")
    if len(observations) == 2 and len(observed) == 2 and \
       observed[0]["pid"] == observed[1]["pid"] == pid and \
       observed[0]["ppid"] == observed[1]["ppid"] == supervisor_pid and \
       observed[0]["startticks"] == observed[1]["startticks"] > 0:
        return {"state": "MATCHED", "pid": pid, "ppid": supervisor_pid,
                "startticks": observed[0]["startticks"], "spawn_error": None}
    conflict = any(item["pid"] != pid or item["ppid"] != supervisor_pid
                   for item in observed)
    if len(observed) >= 2 and any((item["pid"], item["ppid"], item["startticks"]) !=
                                  (observed[0]["pid"], observed[0]["ppid"],
                                   observed[0]["startticks"])
                                  for item in observed[1:]):
        conflict = True
    state = "MISMATCH" if conflict else "UNOBSERVED"
    return {"state": state, "pid": pid, "ppid": None,
            "startticks": None, "spawn_error": None}

def set_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        number = ctypes.get_errno(); raise OSError(number, os.strerror(number))
    current = ctypes.c_int(0)
    if libc.prctl(PR_GET_CHILD_SUBREAPER, ctypes.byref(current), 0, 0, 0) != 0:
        number = ctypes.get_errno(); raise OSError(number, os.strerror(number))
    if current.value != 1:
        raise RuntimeError("subreaper confirmation")

def wait_exact(pid, deadline_ns):
    while time.monotonic_ns() < deadline_ns:
        try:
            actual, raw = os.waitpid(pid, os.WNOHANG)
        except InterruptedError:
            continue
        except ChildProcessError as error:
            raise EChildAuthority("ECHILD during sentinel wait") from error
        if actual == pid:
            return raw
        time.sleep(0.001)
    raise TimeoutError("sentinel wait")

def establish_wait_authority(preflight_started_ns):
    try:
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        if signal.getsignal(signal.SIGCHLD) is not signal.SIG_DFL:
            raise RuntimeError("SIGCHLD confirmation")
        set_subreaper()
    except Exception as error:
        raise PreflightFailure("sigchld-default", error)
    try:
        pid = os.fork()
    except Exception as error:
        raise PreflightFailure("sentinel-fork", error, sigchld_default=True)
    if pid == 0:
        os._exit(73)
    try:
        raw = wait_exact(pid, preflight_started_ns + PREFLIGHT_NS)
        wait_deadline_ns = preflight_started_ns + PREFLIGHT_NS
        waited = {"kind": "wait", "pid": pid, "startticks": None,
                  "raw_wait_status": raw, "direct": True,
                  "monotonic_ns": time.monotonic_ns()}
        if waited["monotonic_ns"] > wait_deadline_ns:
            raise TimeoutError("sentinel wait deadline")
        if raw != 73 << 8:
            raise RuntimeError("sentinel raw wait status")
    except EChildAuthority as error:
        raise PreflightFailure("sentinel-wait", error, pid,
            None, sigchld_default=True, authority_lost=True)
    except Exception as error:
        raise PreflightFailure("sentinel-wait", error, pid,
            waited if "waited" in locals() else None, sigchld_default=True)
    return {"sigchld_default": True, "sentinel_wait_passed": True,
            "sentinel_pid": pid, "sentinel_raw_wait_status": raw,
            "sentinel_wait": waited}

def wait_fields(raw):
    if raw is None:
        return False, None, None
    if type(raw) is not int or raw < 0 or raw > 0xffff:
        raise ValueError("owner wait status")
    if os.WIFEXITED(raw):
        return True, os.WEXITSTATUS(raw), None
    if os.WIFSIGNALED(raw):
        number = os.WTERMSIG(raw)
        if number <= 0 or number >= signal.NSIG:
            raise ValueError("owner wait status")
        return True, None, number
    raise ValueError("owner wait status")

def read_pipe(fd, retained, eof):
    overflow = False
    while not eof:
        try:
            chunk = os.read(fd, 65536)
        except InterruptedError:
            continue
        except BlockingIOError:
            break
        if not chunk:
            if overflow:
                raise PipeOverflow(retained, True)
            return retained, True
        if len(retained) < STREAM_LIMIT:
            keep = min(len(chunk), STREAM_LIMIT - len(retained))
            retained += chunk[:keep]
            overflow = overflow or keep != len(chunk)
        else:
            overflow = True
        if overflow:
            # Return control as soon as the retained prefix is full.  Cleanup
            # owns discard-draining; remaining here would let a continuously
            # writable descendant monopolize the supervisor.
            raise PipeOverflow(retained, False)
    if overflow:
        raise PipeOverflow(retained, eof)
    return retained, eof

def pump_owner(pid, stdout_fd, stderr_fd, deadline_ns, state=None):
    state = state if state is not None else {
        "stdout": b"", "stderr": b"", "stdout_eof": False,
        "stderr_eof": False, "raw_wait_status": None, "waited_ns": None,
        "authority_lost": False, "pipe_overflows": []}
    state.setdefault("authority_lost", False)
    state.setdefault("pipe_overflows", [])
    poller = select.poll()
    poller.register(stdout_fd, select.POLLIN | select.POLLHUP | select.POLLERR)
    poller.register(stderr_fd, select.POLLIN | select.POLLHUP | select.POLLERR)
    while time.monotonic_ns() < deadline_ns:
        if state["raw_wait_status"] is None:
            try:
                actual, raw = os.waitpid(pid, os.WNOHANG)
            except InterruptedError:
                actual = 0
            except ChildProcessError:
                state["authority_lost"] = True
                break
            if actual == pid:
                state["raw_wait_status"] = raw
                state["waited_ns"] = time.monotonic_ns()
            elif actual not in (0, pid):
                raise RuntimeError("exclusive owner wait identity")
        remaining_ms = max(0, min(10, int(
            (deadline_ns - time.monotonic_ns()) / 1000000)))
        for fd, event in poller.poll(remaining_ms):
            if fd == stdout_fd:
                try:
                    state["stdout"], state["stdout_eof"] = read_pipe(
                        fd, state["stdout"], state["stdout_eof"])
                except PipeOverflow as error:
                    state["stdout"] = error.retained
                    state["stdout_eof"] = error.eof
                    state["pipe_overflows"].append(error)
            elif fd == stderr_fd:
                try:
                    state["stderr"], state["stderr_eof"] = read_pipe(
                        fd, state["stderr"], state["stderr_eof"])
                except PipeOverflow as error:
                    state["stderr"] = error.retained
                    state["stderr_eof"] = error.eof
                    state["pipe_overflows"].append(error)
        # A descendant holding a writer cannot extend direct-owner retirement.
        if state["raw_wait_status"] is not None:
            break
    return state

def signal_error(stage, pid, startticks, sig, error, direct):
    return {"kind": "signal-error", "stage": stage, "pid": pid,
            "startticks": startticks, "signal": int(sig),
            "errno": error.errno if type(error.errno) is int and error.errno > 0
                else errno.EIO, "monotonic_ns": time.monotonic_ns(),
            "direct": direct}

def check_deadline(deadline_ns, label):
    if deadline_ns is not None and time.monotonic_ns() >= deadline_ns:
        raise TimeoutError(label)

def durable_file(path, raw, deadline_ns=None):
    check_deadline(deadline_ns, "supervisor publication deadline")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    primary = None
    try:
        check_deadline(deadline_ns, "supervisor publication deadline")
        complete_write(fd, raw, deadline_ns)
        check_deadline(deadline_ns, "supervisor publication deadline")
        os.fsync(fd)
        check_deadline(deadline_ns, "supervisor publication deadline")
    except Exception as error:
        primary = error
    try:
        os.close(fd)
    except Exception as close_error:
        if primary is None:
            raise
        attach_secondary(primary, close_error)
    if primary is not None:
        raise primary

def fsync_directory(path, deadline_ns=None):
    check_deadline(deadline_ns, "supervisor publication deadline")
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    primary = None
    try:
        check_deadline(deadline_ns, "supervisor publication deadline")
        os.fsync(fd)
        check_deadline(deadline_ns, "supervisor publication deadline")
    except Exception as error:
        primary = error
    try:
        os.close(fd)
    except Exception as close_error:
        if primary is None:
            raise
        attach_secondary(primary, close_error)
    if primary is not None:
        raise primary

def ensure_attempt_root(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("canonical attempt root")
    parent = path.parent.resolve(strict=True)
    canonical = parent / path.name
    if path != canonical:
        raise ValueError("canonical attempt root")
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
            raise ValueError("canonical attempt root")
    else:
        os.mkdir(path, 0o700)
        fsync_directory(parent)
    return path

def evidence_record(root, filename):
    path = Path(root) / filename
    try:
        raw = stable_bytes(path, STREAM_LIMIT)
    except FileNotFoundError:
        return False, None
    return True, hashlib.sha256(raw).hexdigest()

def publish_result(root, stdout, stderr, result, deadline_ns):
    root = ensure_attempt_root(root)
    result_path = root / "supervisor-result.json"
    if result_path.exists() or result_path.is_symlink():
        raise FileExistsError("supervisor result exists")
    try:
        durable_file(root / "owner-supervisor.stdout.bin", stdout, deadline_ns)
        durable_file(root / "owner-supervisor.stderr.bin", stderr, deadline_ns)
        fsync_directory(root, deadline_ns)
        raw = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
        durable_file(result_path, raw, deadline_ns)
        fsync_directory(root, deadline_ns)
    except Exception as primary:
        try:
            result_path.unlink()
            fsync_directory(root)
        except FileNotFoundError:
            pass
        except Exception as rollback_error:
            attach_secondary(primary, rollback_error)
        raise primary from None

def validate_inputs(args):
    if OWNER.parent != HERE or OWNER.name != "witness_owner.py" or \
       not Path(sys.executable).is_absolute():
        raise ValueError("supervisor executable binding")
    attempt_root = Path(args.attempt_root)
    if not attempt_root.is_absolute() or attempt_root != \
            attempt_root.parent.resolve(strict=True) / attempt_root.name or \
            attempt_root.exists() or attempt_root.is_symlink():
        raise ValueError("fresh canonical attempt root")
    if type(args.nonce) is not str or HEX32.fullmatch(args.nonce) is None or \
       type(args.owner_sha256) is not str or \
       HEX64.fullmatch(args.owner_sha256) is None:
        raise ValueError("supervisor scalar input")
    owner_raw = stable_bytes(OWNER, 1 << 20)
    if hashlib.sha256(owner_raw).hexdigest() != args.owner_sha256:
        raise ValueError("owner source hash")
    hashes = strict(stable_bytes(args.hashes, 1 << 20))
    expected_hashes = {"source_sha256", "generated_sha256", "header_sha256",
                       "elf_sha256"}
    if type(hashes) is not dict or set(hashes) != expected_hashes or any(
            type(hashes[key]) is not str or HEX64.fullmatch(hashes[key]) is None
            for key in expected_hashes) or hashes["source_sha256"] != \
            "09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f":
        raise ValueError("supervisor hash object")
    names = {"source": args.source, "generated_source": args.generated_source,
             "header": args.header, "elf": args.elf}
    hash_names = {"source": "source_sha256", "generated_source": "generated_sha256",
                  "header": "header_sha256", "elf": "elf_sha256"}
    for name, path in names.items():
        raw = stable_bytes(path, 16 << 20 if name == "elf" else 1 << 20)
        if hashlib.sha256(raw).hexdigest() != hashes[hash_names[name]]:
            raise ValueError("supervisor input hash " + name)
    for path, size, digest in ((args.request, 406,
            "e81b38bbe6116bf1df2807fa968e12dccfd28fe8c3ad225c45f282b36cab6716"),
            (args.selected_inputs, 76,
            "6b8761a9d2094147f02b9fe2a4c709246905a04c5122d68f6b9951162e01317d"),
            (args.fixture, 27448,
            "9ad70dd23d699e72ad805f59446aec371c4e80b955056b845af921b4ce51f725")):
        raw = stable_bytes(path, size)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("supervisor runtime input")
    if Path(args.fixture) != Path("/work/cases/stdin-devnull/inputs/fixture"):
        raise ValueError("supervisor fixture source")
    return hashes

def owner_argv(args):
    return [str(Path(sys.executable).resolve()), str(OWNER),
        "--witness-root", str(args.attempt_root), "--nonce", args.nonce,
        "--selector", str(args.selector), "--hashes", str(args.hashes),
        "--source", str(args.source), "--generated-source", str(args.generated_source),
        "--header", str(args.header), "--elf", str(args.elf),
        "--request", str(args.request), "--selected-inputs", str(args.selected_inputs),
        "--fixture", str(args.fixture)]

def spawn_owner(args):
    opened = []
    try:
        stdout_r, stdout_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        opened.extend((stdout_r, stdout_w))
        stderr_r, stderr_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        opened.extend((stderr_r, stderr_w))
        pid = os.fork()
    except Exception as primary:
        for fd in reversed(opened):
            try:
                os.close(fd)
            except Exception as close_error:
                attach_secondary(primary, close_error)
        raise primary from None
    if pid == 0:
        try:
            os.close(stdout_r); os.close(stderr_r)
            for fd in (stdout_w, stderr_w):
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
            null_fd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
            os.dup2(null_fd, 0); os.dup2(stdout_w, 1); os.dup2(stderr_w, 2)
            os.close(null_fd); os.close(stdout_w); os.close(stderr_w)
            argv = owner_argv(args)
            environment = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
                           "PYTHONDONTWRITEBYTECODE": "1"}
            os.execve(argv[0], argv, environment)
        finally:
            os._exit(127)
    close_errors = []
    for fd in (stdout_w, stderr_w):
        try:
            os.close(fd)
        except Exception as error:
            close_errors.append(error)
    return pid, stdout_r, stderr_r, close_errors

def cleanup_identity(pid, phase, parent_pid, expected_startticks=None):
    observed = observe_identity(pid)
    matched = observed["observation"] == "observed" and \
        observed["pid"] == pid and observed["ppid"] == parent_pid and \
        (expected_startticks is None or
         observed["startticks"] == expected_startticks)
    return {"kind": "identity", "phase": phase,
            "observation": observed["observation"], "pid": pid,
            "ppid": observed["ppid"], "startticks": observed["startticks"],
            "matched": matched, "monotonic_ns": observed["monotonic_ns"]}

def double_identity(pid, phase, parent_pid, expected_startticks=None):
    first = cleanup_identity(pid, phase + "-1", parent_pid,
                             expected_startticks)
    second = cleanup_identity(pid, phase + "-2", parent_pid,
                              expected_startticks)
    same_birth = first["matched"] and second["matched"] and \
        first["startticks"] == second["startticks"]
    if first["matched"] and second["matched"] and not same_birth:
        second = dict(second)
        second["matched"] = False
    birth = second["startticks"] if same_birth else None
    return [first, second], birth

def scan_owned(supervisor_pid, exclude, scan_index, deadline_ns):
    phase = "owned-scan-%d" % scan_index
    identities, events, mismatches = [], [], []
    candidates = 0
    for entry in Path("/proc").iterdir():
        if time.monotonic_ns() >= deadline_ns:
            return identities, events, mismatches, True
        if not entry.name.isdigit() or int(entry.name) in exclude:
            continue
        candidates += 1
        if candidates > OWNED_SCAN_PID_LIMIT:
            raise OverflowError("supervisor owned scan process bound")
        pid = int(entry.name)
        first = cleanup_identity(pid, phase + "-1", supervisor_pid)
        if not first["matched"]:
            continue
        second = cleanup_identity(pid, phase + "-2", supervisor_pid,
                                  first["startticks"])
        events.extend((first, second))
        if second["matched"]:
            identities.append({"pid": pid, "ppid": supervisor_pid,
                               "startticks": second["startticks"]})
        else:
            mismatches.append(second)
    events.append({"kind": "owned-scan", "monotonic_ns": time.monotonic_ns(),
                   "pids": identities})
    return identities, events, mismatches, False

def wait_cleanup_pid(pid, deadline_ns, startticks, direct, progress=None):
    while time.monotonic_ns() < deadline_ns:
        if progress is not None:
            progress()
        try:
            actual, raw = os.waitpid(pid, os.WNOHANG)
        except InterruptedError:
            continue
        except ChildProcessError:
            raise EChildAuthority("ECHILD during cleanup wait")
        if actual == pid:
            return {"kind": "wait", "pid": pid, "startticks": startticks,
                    "raw_wait_status": raw, "direct": direct,
                    "monotonic_ns": time.monotonic_ns()}
        if actual not in (0, pid):
            raise RuntimeError("exclusive cleanup wait identity")
        if progress is not None:
            progress()
        time.sleep(0.001)
    return None

def matching_birth(observations, pid, parent_pid):
    birth = None
    for first, second in zip(observations, observations[1:]):
        if first.get("observation") == second.get("observation") == "observed" and \
           first.get("pid") == second.get("pid") == pid and \
           first.get("ppid") == second.get("ppid") == parent_pid and \
           type(first.get("startticks")) is int and first["startticks"] > 0 and \
           first["startticks"] == second.get("startticks"):
            birth = first["startticks"]
    return birth

def cleanup_tree(direct_pid, initial_observations, direct_wait, supervisor_pid,
                 trigger_ns, deadline_ns, require_direct_birth=False,
                 initial_wait_deadline_ns=None, initial_wait_timed_out=False,
                 progress=None, authority_lost=False, session=None):
    if session is None:
        session = {}
    events = session.setdefault("events", [])
    unresolved = session.setdefault("unresolved", [])
    internal_failures = session.setdefault("internal_failures", [])
    direct_authority = not (authority_lost or
                            session.get("authority_lost", False))
    direct_wait = session.get("direct_wait", direct_wait)
    direct_reaped = True if direct_pid is None else session.get(
        "direct_reaped", direct_wait is not None)
    session["authority_lost"] = not direct_authority
    session["direct_reaped"] = direct_reaped
    session["direct_wait"] = direct_wait
    observed_birth = matching_birth(initial_observations, direct_pid,
                                    supervisor_pid) \
        if direct_pid is not None else None
    last_birth = session.get("last_birth", observed_birth)
    if observed_birth is not None:
        last_birth = observed_birth
    session["last_birth"] = last_birth
    if direct_wait is not None and direct_wait not in events:
        events.append(direct_wait)
    elif direct_pid is not None:
        governing_wait_deadline = min(
            initial_wait_deadline_ns or deadline_ns, deadline_ns)
        if initial_wait_timed_out and not any(
                item.get("kind") == "wait-timeout" and
                item.get("stage") == "direct" and
                item.get("pid") == direct_pid for item in unresolved):
            now = time.monotonic_ns()
            if now < governing_wait_deadline:
                raise ValueError("premature direct wait timeout")
            unresolved.append({"kind": "wait-timeout", "stage": "direct",
                "pid": direct_pid, "startticks": last_birth,
                "monotonic_ns": now, "deadline_ns": governing_wait_deadline})
        for stage, sig, wait_ns in (("term", signal.SIGTERM, 1000000000),
                                    ("kill", signal.SIGKILL, 5000000000)):
            if not direct_authority:
                break
            if progress is not None:
                progress()
            try:
                observations, birth = double_identity(direct_pid,
                    stage + "-identity", supervisor_pid, last_birth)
            except Exception as error:
                # Identity failure is not authority.  Keep the mutable cleanup
                # record and continue bounded wait/reap/pipe progress.
                internal_failures.append(error)
                direct_authority = False
                session["authority_lost"] = True
                break
            events.extend(observations)
            if birth is not None:
                last_birth = birth
                session["last_birth"] = birth
            elif any(not value["matched"] for value in observations):
                unresolved.append(observations[-1])
            # A signal is safe only when this exact, immediately preceding pair
            # established the current birth.  An older birth never authorizes a
            # later signal (in particular for a failed-preflight sentinel).
            if birth is None:
                unavailable = all(value["observation"] in ("missing", "error")
                                  for value in observations)
                if require_direct_birth or last_birth is not None or not unavailable:
                    break
            now = time.monotonic_ns()
            if now >= deadline_ns:
                unresolved.append({"kind": "deadline",
                    "stage": stage + "-pre-signal", "monotonic_ns": now,
                    "deadline_ns": deadline_ns})
                break
            try:
                os.kill(direct_pid, sig)
            except OSError as error:
                unresolved.append(signal_error(stage, direct_pid, last_birth,
                                                sig, error, True))
                break
            signal_observed_ns = time.monotonic_ns()
            events.append({"kind": "signal", "pid": direct_pid,
                "startticks": last_birth, "signal": int(sig),
                "direct_child": True, "monotonic_ns": signal_observed_ns})
            stage_deadline = min(deadline_ns, signal_observed_ns + wait_ns)
            try:
                waited = wait_cleanup_pid(direct_pid, stage_deadline,
                                          last_birth, True, progress)
            except EChildAuthority as error:
                # This is loss of exclusive direct-child wait authority, not
                # packet-4's terminal empty-tree proof.  Preserve it as an
                # internal failure and require the later two scans plus an
                # independent waitpid(-1) ECHILD observation.
                internal_failures.append(error)
                direct_authority = False
                session["authority_lost"] = True
                break
            except Exception as error:
                internal_failures.append(error)
                direct_authority = False
                session["authority_lost"] = True
                break
            if waited is not None:
                events.append(waited)
                direct_wait = waited
                direct_reaped = True
                session["direct_wait"] = direct_wait
                session["direct_reaped"] = True
                break
            now = time.monotonic_ns()
            if now < stage_deadline:
                raise ValueError("premature cleanup wait timeout")
            unresolved.append({"kind": "wait-timeout", "stage": stage,
                "pid": direct_pid, "startticks": last_birth,
                "monotonic_ns": now,
                "deadline_ns": stage_deadline})

    terminal_empty = session.get("terminal_empty", False)
    consecutive_empty = session.get("consecutive_empty", 0)
    scan_index = session.get("scan_index", 0)
    known_births = session.setdefault("known_births", {})
    while not session.get("echild_without_direct", False) and \
            (direct_reaped or direct_pid is not None) and \
            time.monotonic_ns() < deadline_ns and scan_index < 2047:
        if progress is not None:
            progress()
        reaped_any = False
        while time.monotonic_ns() < deadline_ns:
            try:
                child, raw = os.waitpid(-1, os.WNOHANG)
            except InterruptedError:
                continue
            except ChildProcessError:
                session["authority_lost"] = True
                direct_authority = False
                child = -1
                break
            except Exception as error:
                internal_failures.append(error)
                session["authority_lost"] = True
                direct_authority = False
                break
            if child <= 0:
                break
            reaped_any = True
            wait_event = {"kind": "wait", "pid": child,
                "startticks": known_births.pop(child, None),
                "raw_wait_status": raw, "direct": False,
                "monotonic_ns": time.monotonic_ns()}
            if child == direct_pid and not direct_reaped:
                wait_event["direct"] = True
                wait_event["startticks"] = last_birth
                direct_wait = wait_event
                direct_reaped = True
                session["direct_wait"] = direct_wait
                session["direct_reaped"] = True
            events.append(wait_event)
        if reaped_any:
            consecutive_empty = 0
            session["consecutive_empty"] = 0
        now = time.monotonic_ns()
        if now >= deadline_ns:
            unresolved.append({"kind": "deadline", "stage": "owned-scan",
                "monotonic_ns": now, "deadline_ns": deadline_ns})
            break
        scan_index += 1
        session["scan_index"] = scan_index
        try:
            adopted, scan_events, mismatches, scan_timed_out = scan_owned(
                supervisor_pid, {supervisor_pid} | ({direct_pid} if direct_pid else set()),
                scan_index, deadline_ns)
        except Exception as error:
            # A failed scan is not an empty scan and cannot contribute to the
            # terminal proof.  Retain the internal error, revoke all signal
            # authority, and continue waiting/reaping to the fixed deadline.
            internal_failures.append(error)
            session["authority_lost"] = True
            direct_authority = False
            consecutive_empty = 0
            session["consecutive_empty"] = 0
            time.sleep(0.001)
            continue
        events.extend(scan_events)
        unresolved.extend(mismatches)
        if progress is not None:
            progress()
        if scan_timed_out:
            now = time.monotonic_ns()
            unresolved.append({"kind": "deadline", "stage": "owned-scan",
                "monotonic_ns": now, "deadline_ns": deadline_ns})
            break
        if adopted:
            consecutive_empty = 0
            session["consecutive_empty"] = 0
            for identity in adopted:
                known_births[identity["pid"]] = identity["startticks"]
                unresolved.append({"kind": "owned", "phase": "owned-scan-%d" % scan_index,
                    "pid": identity["pid"], "ppid": identity["ppid"],
                    "startticks": identity["startticks"],
                    "monotonic_ns": time.monotonic_ns()})
                pair, birth = double_identity(identity["pid"],
                    "owned-scan-%d" % scan_index, supervisor_pid,
                    identity["startticks"])
                events.extend(pair)
                if birth is None:
                    unresolved.append(pair[-1])
                    continue
                if session.get("authority_lost", False):
                    # ECHILD or uncertain helper completion is irreversible;
                    # later procfs observations cannot restore authority.
                    continue
                now = time.monotonic_ns()
                if now >= deadline_ns:
                    unresolved.append({"kind": "deadline", "stage": "owned-scan",
                        "monotonic_ns": now, "deadline_ns": deadline_ns})
                    break
                try:
                    os.kill(identity["pid"], signal.SIGKILL)
                except OSError as error:
                    unresolved.append(signal_error("kill", identity["pid"], birth,
                                                    signal.SIGKILL, error, False))
                    continue
                events.append({"kind": "signal", "pid": identity["pid"],
                    "startticks": birth, "signal": int(signal.SIGKILL),
                    "monotonic_ns": time.monotonic_ns()})
            continue
        consecutive_empty += 1
        session["consecutive_empty"] = consecutive_empty
        if consecutive_empty < 2:
            time.sleep(0.001)
            continue
        try:
            child, raw = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            events.append({"kind": "echild", "monotonic_ns": time.monotonic_ns(),
                           "return": -1, "errno": errno.ECHILD})
            session["authority_lost"] = True
            direct_authority = False
            if direct_reaped:
                terminal_empty = True
                session["terminal_empty"] = True
                break
            # ECHILD is irreversible, but without the direct wait it is not a
            # successful terminal proof.  Emit no later lifecycle event; only
            # drain progress until the real deadline permits an exact timeout.
            session["echild_without_direct"] = True
            break
        if child > 0:
            wait_event = {"kind": "wait", "pid": child,
                "startticks": known_births.pop(child, None),
                "raw_wait_status": raw, "direct": False,
                "monotonic_ns": time.monotonic_ns()}
            if child == direct_pid and not direct_reaped:
                wait_event["direct"] = True
                wait_event["startticks"] = last_birth
                direct_wait = wait_event
                direct_reaped = True
                session["direct_wait"] = direct_wait
                session["direct_reaped"] = True
            events.append(wait_event)
            consecutive_empty = 0
            session["consecutive_empty"] = 0
        else:
            time.sleep(0.001)
    # The phase namespace is deliberately capped.  Exhausting it is not a
    # cleanup result: continue without acquiring new signal authority, retaining
    # any waits, until the existing terminal proof closes or the real deadline
    # is observed.
    while scan_index >= 2047 and not terminal_empty and \
            not session.get("echild_without_direct", False) and \
            time.monotonic_ns() < deadline_ns:
        if progress is not None:
            progress()
        try:
            child, raw = os.waitpid(-1, os.WNOHANG)
        except InterruptedError:
            continue
        except ChildProcessError:
            events.append({"kind": "echild",
                "monotonic_ns": time.monotonic_ns(),
                "return": -1, "errno": errno.ECHILD})
            session["authority_lost"] = True
            direct_authority = False
            if direct_reaped and consecutive_empty >= 2:
                terminal_empty = True
                session["terminal_empty"] = True
            else:
                session["echild_without_direct"] = True
            break
        except Exception as error:
            internal_failures.append(error)
            session["authority_lost"] = True
            direct_authority = False
            time.sleep(0.001)
            continue
        if child > 0:
            wait_event = {"kind": "wait", "pid": child,
                "startticks": known_births.pop(child, None),
                "raw_wait_status": raw, "direct": False,
                "monotonic_ns": time.monotonic_ns()}
            if child == direct_pid and not direct_reaped:
                wait_event["direct"] = True
                wait_event["startticks"] = last_birth
                direct_wait = wait_event
                direct_reaped = True
                session["direct_wait"] = direct_wait
                session["direct_reaped"] = True
            events.append(wait_event)
            consecutive_empty = 0
            session["consecutive_empty"] = 0
            continue
        time.sleep(0.001)
    while session.get("echild_without_direct", False) and \
            time.monotonic_ns() < deadline_ns:
        if progress is not None:
            progress()
        time.sleep(0.001)
    finished = time.monotonic_ns()
    session["finished_ns"] = finished
    session["terminal_empty"] = terminal_empty
    if direct_pid is not None and not direct_reaped and not any(
            item.get("kind") == "wait-timeout" and item.get("pid") == direct_pid
            and item.get("stage") == "direct"
            for item in unresolved):
        timeout = min(initial_wait_deadline_ns or deadline_ns, deadline_ns)
        if finished >= timeout:
            unresolved.append({"kind": "wait-timeout", "stage": "direct",
                "pid": direct_pid, "startticks": last_birth,
                "monotonic_ns": finished, "deadline_ns": timeout})
        else:
            internal_failures.append(RuntimeError(
                "cleanup returned before direct wait deadline"))
    if not terminal_empty and finished >= deadline_ns and not any(
            item.get("kind") == "deadline" and item.get("stage") == "owned-scan"
            for item in unresolved):
        unresolved.append({"kind": "deadline", "stage": "owned-scan",
            "monotonic_ns": finished, "deadline_ns": deadline_ns})
    return {"complete": direct_reaped and terminal_empty and not unresolved and
                finished <= deadline_ns,
            "events": events, "unresolved": unresolved}, direct_wait

def close_pipe(fd, failures):
    if fd is None or fd < 0:
        return
    try:
        os.close(fd)
    except Exception as error:
        failures.append(error)

def preflight_record(failure):
    return normalized_error(failure.original, failure.stage)

def finalize_cleanup_publication(cleanup, finished_ns, deadline_ns):
    if finished_ns <= deadline_ns:
        return cleanup
    return {"complete": False, "events": cleanup["events"],
        "unresolved": cleanup["unresolved"] + [{
            "kind": "deadline", "stage": "publication-finish",
            "monotonic_ns": finished_ns, "deadline_ns": deadline_ns}]}

def supervisor_result(root, supervisor_pid, started_ns, finished_ns, owner_identity,
                      identity_observations, owner_wait, stdout, stderr,
                      cleanup, preflight_started_ns, sentinel_wait_deadline_ns,
                      owner_wait_deadline_ns, cleanup_trigger_ns,
                      cleanup_deadline_ns, supervisor_deadline_ns,
                      sigchld_default, sentinel_wait_passed,
                      preflight_failure, complete):
    owner_result_present, owner_result_sha = evidence_record(root, "owner-result.json")
    witness_present, witness_sha = evidence_record(root, "witness.jsonl")
    errors_present, errors_sha = evidence_record(root, "owner-errors.jsonl")
    waited, exit_code, owner_signal = wait_fields(
        owner_wait["raw_wait_status"] if owner_wait is not None else None)
    return {"schema_version": 1, "kind": "STORAGE_FAULT_V2_SUPERVISOR",
        "status": "COMPLETE" if complete else "OWNER_ERROR",
        "owner_exit_code": exit_code, "owner_signal": owner_signal,
        "supervisor_pid": supervisor_pid,
        "started_ns": started_ns, "finished_ns": finished_ns,
        "attempt_root": str(Path(root)),
        "owner_result_present": owner_result_present,
        "owner_result_sha256": owner_result_sha,
        "witness_present": witness_present, "witness_sha256": witness_sha,
        "owner_errors_present": errors_present,
        "owner_errors_sha256": errors_sha,
        "owner_stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "owner_stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "owner_identity": owner_identity,
        "owner_identity_observations": identity_observations,
        "owner_wait_observed": waited,
        "owner_wait_deadline_ns": owner_wait_deadline_ns,
        "cleanup_trigger_ns": cleanup_trigger_ns,
        "supervisor_cleanup_deadline_ns": cleanup_deadline_ns,
        "supervisor_deadline_ns": supervisor_deadline_ns,
        "supervisor_cleanup": cleanup,
        "sigchld_default": sigchld_default,
        "sentinel_wait_passed": sentinel_wait_passed,
        "preflight_failure": preflight_failure,
        "preflight_started_ns": preflight_started_ns,
        "sentinel_wait_deadline_ns": sentinel_wait_deadline_ns}

def owner_result_matches(root, pid, startticks):
    try:
        value = strict(stable_bytes(Path(root) / "owner-result.json", 1 << 20))
    except (OSError, ValueError):
        return False
    owner = value.get("owner") if type(value) is dict else None
    return type(owner) is dict and set(owner) == {"pid", "startticks"} and \
        type(owner["pid"]) is int and owner["pid"] == pid and \
        type(owner["startticks"]) is int and owner["startticks"] == startticks

def pump_pipes_once(state, stdout_fd, stderr_fd, failures):
    for name, fd in (("stdout", stdout_fd), ("stderr", stderr_fd)):
        if fd is None or fd < 0 or state[name + "_eof"]:
            continue
        try:
            state[name], state[name + "_eof"] = read_pipe(
                fd, state[name], state[name + "_eof"])
        except PipeOverflow as error:
            state[name] = error.retained
            state[name + "_eof"] = error.eof
            if not any(isinstance(value, PipeOverflow) for value in failures):
                failures.append(error)
        except Exception as error:
            failures.append(error)

def finish_pipes(state, stdout_fd, stderr_fd, failures, deadline_ns=None):
    stop = min(deadline_ns, time.monotonic_ns() + 100_000_000) \
        if deadline_ns is not None else time.monotonic_ns() + 100_000_000
    while not state["stdout_eof"] or not state["stderr_eof"]:
        pump_pipes_once(state, stdout_fd, stderr_fd, failures)
        if state["stdout_eof"] and state["stderr_eof"]:
            break
        if time.monotonic_ns() >= stop:
            break
        time.sleep(0.001)
    for fd in (stdout_fd, stderr_fd):
        close_pipe(fd, failures)

def run_supervisor(args):
    validate_inputs(args)
    preflight_started_ns = time.monotonic_ns()
    sentinel_wait_deadline_ns = preflight_started_ns + PREFLIGHT_NS
    supervisor_pid = os.getpid()
    try:
        authority = establish_wait_authority(preflight_started_ns)
        started_ns = time.monotonic_ns()
        if started_ns > sentinel_wait_deadline_ns:
            raise PreflightFailure("sentinel-wait",
                TimeoutError("owner start deadline"),
                authority["sentinel_pid"], authority["sentinel_wait"],
                sigchld_default=True, trigger_ns=started_ns)
    except PreflightFailure as failure:
        trigger_ns = failure.trigger_ns if failure.trigger_ns is not None else \
            (failure.sentinel_wait["monotonic_ns"]
             if failure.sentinel_wait is not None else time.monotonic_ns())
        cleanup_deadline_ns = trigger_ns + CLEANUP_NS
        cleanup_session = {"events": [], "unresolved": [],
                           "authority_lost": failure.authority_lost,
                           "direct_wait": failure.sentinel_wait,
                           "direct_reaped": failure.sentinel_wait is not None}
        try:
            cleanup, ignored_wait = cleanup_tree(
                failure.sentinel_pid, [], failure.sentinel_wait, supervisor_pid,
                trigger_ns, cleanup_deadline_ns, require_direct_birth=True,
                initial_wait_deadline_ns=sentinel_wait_deadline_ns,
                initial_wait_timed_out=trigger_ns >= sentinel_wait_deadline_ns,
                authority_lost=failure.authority_lost, session=cleanup_session)
        except Exception as cleanup_error:
            cleanup_session.setdefault("internal_failures", []).append(cleanup_error)
            try:
                cleanup, ignored_wait = cleanup_tree(
                    failure.sentinel_pid, [],
                    cleanup_session.get("direct_wait"), supervisor_pid,
                    trigger_ns, cleanup_deadline_ns,
                    require_direct_birth=True,
                    initial_wait_deadline_ns=sentinel_wait_deadline_ns,
                    authority_lost=True, session=cleanup_session)
            except Exception as recovery_error:
                cleanup_session.setdefault("internal_failures", []).append(
                    recovery_error)
                cleanup = {"complete": False,
                           "events": cleanup_session["events"],
                           "unresolved": cleanup_session["unresolved"]}
        # Sentinel retirement is independent of fallible evidence creation.
        root = ensure_attempt_root(args.attempt_root)
        finished_ns = time.monotonic_ns()
        deadline_ns = preflight_started_ns + PREFLIGHT_TOTAL_NS
        cleanup = finalize_cleanup_publication(
            cleanup, finished_ns, cleanup_deadline_ns)
        identity = classify_owner(None, supervisor_pid, [],
                                  preflight_failure=failure)
        result = supervisor_result(root, supervisor_pid, preflight_started_ns, finished_ns,
            identity, [], None, b"", b"", cleanup, preflight_started_ns,
            sentinel_wait_deadline_ns, None, trigger_ns, cleanup_deadline_ns,
            deadline_ns, failure.sigchld_default, False,
            preflight_record(failure), False)
        publish_result(root, b"", b"", result, deadline_ns)
        return result, 125

    owner_wait_deadline_ns = started_ns + OWNER_WAIT_NS
    supervisor_deadline_ns = started_ns + TOTAL_NS
    pid = stdout_fd = stderr_fd = None
    spawn_error = None
    failures = []
    state = {"stdout": b"", "stderr": b"", "stdout_eof": False,
             "stderr_eof": False, "raw_wait_status": None, "waited_ns": None,
             "authority_lost": False, "pipe_overflows": []}
    observations = []
    try:
        pid, stdout_fd, stderr_fd, close_errors = spawn_owner(args)
        failures.extend(close_errors)
    except Exception as error:
        spawn_error = error

    if pid is not None:
        try:
            observations.append(observe_identity(pid))
            observations.append(observe_identity(pid))
            pump_owner(pid, stdout_fd, stderr_fd, owner_wait_deadline_ns, state)
        except Exception as error:
            failures.append(error)
        for error in state.get("pipe_overflows", []):
            if not any(value is error for value in failures):
                failures.append(error)
    trigger_ns = state["waited_ns"] if state["waited_ns"] is not None \
        else time.monotonic_ns()
    cleanup_deadline_ns = trigger_ns + CLEANUP_NS
    initial_birth = matching_birth(observations, pid, supervisor_pid) \
        if pid is not None else None
    direct_wait = None
    if state["raw_wait_status"] is not None:
        direct_wait = {"kind": "wait", "pid": pid, "startticks": initial_birth,
            "raw_wait_status": state["raw_wait_status"], "direct": True,
            "monotonic_ns": state["waited_ns"]}
    cleanup_error = None
    cleanup_session = {"events": [], "unresolved": [],
                       "authority_lost": state.get("authority_lost", False),
                       "direct_wait": direct_wait, "direct_reaped": direct_wait is not None}
    cleanup = cleanup_session
    try:
        cleanup, direct_wait = cleanup_tree(pid, observations, direct_wait,
            supervisor_pid, trigger_ns, cleanup_deadline_ns,
            initial_wait_deadline_ns=owner_wait_deadline_ns,
            initial_wait_timed_out=trigger_ns >= owner_wait_deadline_ns,
            progress=lambda: pump_pipes_once(
                state, stdout_fd, stderr_fd, failures),
            authority_lost=state.get("authority_lost", False),
            session=cleanup_session)
    except Exception as error:
        cleanup_error = error
        # Recover using the caller-owned mutable state.  Authority is sticky
        # after an unexpected helper failure, and cleanup_tree continues to
        # the real deadline without fabricating a future timestamp.
        try:
            cleanup, direct_wait = cleanup_tree(
                pid, observations, cleanup_session.get("direct_wait"),
                supervisor_pid, trigger_ns, cleanup_deadline_ns,
                initial_wait_deadline_ns=owner_wait_deadline_ns,
                progress=lambda: pump_pipes_once(
                    state, stdout_fd, stderr_fd, failures),
                authority_lost=True, session=cleanup_session)
        except Exception as recovery_error:
            failures.append(recovery_error)
            cleanup = {"complete": False, "events": cleanup_session["events"],
                       "unresolved": cleanup_session["unresolved"]}
    finally:
        finish_pipes(state, stdout_fd, stderr_fd, failures,
                     cleanup_deadline_ns)
    for error in cleanup_session.get("internal_failures", []):
        if not any(value is error for value in failures):
            failures.append(error)
    if cleanup_error is not None:
        # Preserve the child-retirement/evidence result and publish an
        # explicit OWNER_ERROR.  Raising here used to discard the only record
        # of a post-fork failure and could strand a direct child.
        failures.append(cleanup_error)
    root = ensure_attempt_root(args.attempt_root)
    identity = classify_owner(pid, supervisor_pid, observations,
                              spawn_error=spawn_error)
    finished_ns = time.monotonic_ns()
    cleanup = finalize_cleanup_publication(
        cleanup, finished_ns, cleanup_deadline_ns)
    result = supervisor_result(root, supervisor_pid, started_ns, finished_ns, identity,
        observations, direct_wait, state["stdout"], state["stderr"], cleanup,
        preflight_started_ns, sentinel_wait_deadline_ns,
        owner_wait_deadline_ns, trigger_ns, cleanup_deadline_ns,
        supervisor_deadline_ns, True, True, None, False)
    complete = not failures and spawn_error is None and \
        identity["state"] == "MATCHED" and direct_wait is not None and \
        direct_wait["monotonic_ns"] <= owner_wait_deadline_ns and \
        result["owner_wait_observed"] is True and \
        result["owner_exit_code"] == 0 and result["owner_signal"] is None and \
        cleanup["complete"] is True and \
        result["owner_result_present"] is True and \
        result["witness_present"] is True and \
        result["owner_errors_present"] is True and \
        stable_bytes(root / "owner-errors.jsonl", 1 << 20) == b"" and \
        owner_result_matches(root, pid, identity["startticks"])
    if complete:
        result["status"] = "COMPLETE"
    publish_result(root, state["stdout"], state["stderr"], result,
                   supervisor_deadline_ns)
    return result, 0 if complete else 125

def parser():
    value = argparse.ArgumentParser()
    value.add_argument("--attempt-root", type=Path, required=True)
    value.add_argument("--owner-sha256", required=True)
    value.add_argument("--nonce", required=True)
    value.add_argument("--selector", type=int, choices=range(7), required=True)
    value.add_argument("--hashes", type=Path, required=True)
    value.add_argument("--source", type=Path, required=True)
    value.add_argument("--generated-source", type=Path, required=True)
    value.add_argument("--header", type=Path, required=True)
    value.add_argument("--elf", type=Path, required=True)
    value.add_argument("--request", type=Path, required=True)
    value.add_argument("--selected-inputs", type=Path, required=True)
    value.add_argument("--fixture", type=Path, required=True)
    return value

def main():
    args = parser().parse_args()
    try:
        result, status = run_supervisor(args)
    except Exception as error:
        print("supervisor input failure: %s: %s" %
              (type(error).__name__, str(error) or "<empty>"), file=sys.stderr)
        return 125
    print(json.dumps(result, sort_keys=True))
    return status

if __name__ == "__main__":
    raise SystemExit(main())
