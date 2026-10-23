#!/usr/bin/env python3
"""Collect one Linux process tree; a collected exit is not application acceptance.

The private worker is a child subreaper. It never reaps the application group
leader until group cleanup is finished, so a signal cannot target a reused PGID.
Reparented children belong exclusively to that worker, including descendants
that call setsid(). No host-wide process-name or process-group search is used.
"""

import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import time


SCHEMA_VERSION = 1
_READ_SIZE = 65536
_MAX_CHILD_RECORDS = 512


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _identity(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(_READ_SIZE), b""):
            digest.update(block)
            size += len(block)
    return {"path": str(path), "size": size, "sha256": digest.hexdigest()}


def _decode_wait(status):
    if os.WIFEXITED(status):
        return {"kind": "exited", "code": os.WEXITSTATUS(status)}
    if os.WIFSIGNALED(status):
        return {"kind": "signaled", "signal": os.WTERMSIG(status),
                "core_dumped": bool(os.WCOREDUMP(status))}
    return {"kind": "unexpected", "raw": status}


def _worker_command(directory):
    return [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
            "--worker", str(directory)]


def _rescue_worker(process, cleanup_seconds):
    """Bound rescue of our private worker without a numeric-PID ancestry race.

    Stop the unreaped worker before inspecting its direct children. The worker
    sets SIGCHLD=SIG_DFL before creating any child, so those PIDs stay reserved
    while it is stopped. Killing a direct child reparents its descendants to
    this same stopped subreaper; repeat until no live direct child remains.
    """
    rescue = {"reason": "independent worker deadline", "signals": [],
              "cleanup_complete": False}
    deadline = time.monotonic() + cleanup_seconds
    state = None
    try:
        os.kill(process.pid, signal.SIGSTOP)
        while time.monotonic() < deadline:
            state = os.waitid(os.P_PID, process.pid,
                              os.WSTOPPED | os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if state is not None:
                break
            time.sleep(0.005)
        if state is None:
            raise RuntimeError("private worker did not stop before rescue deadline")
        if state.si_code != os.CLD_STOPPED:
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
            rescue["worker_returncode"] = process.returncode
            return rescue
        sent = set()
        while time.monotonic() < deadline:
            live = []
            for pid in _children_of(process.pid):
                identity = _process_identity(pid)
                if identity["state"] in ("Z", "X"):
                    continue
                live.append(pid)
                if pid not in sent:
                    os.kill(pid, signal.SIGKILL)
                    sent.add(pid)
                    if len(rescue["signals"]) < _MAX_CHILD_RECORDS:
                        rescue["signals"].append(identity)
            if not live:
                break
            time.sleep(0.005)
        # Let the worker handle interruption, reap its adopted zombies, and
        # publish its own original collection evidence when it can still run.
        os.kill(process.pid, signal.SIGTERM)
        os.kill(process.pid, signal.SIGCONT)
        try:
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            os.kill(process.pid, signal.SIGKILL)
            process.wait(timeout=0.2)
        rescue["worker_returncode"] = process.returncode
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        rescue["error"] = str(error)
        # A failed rescue is explicit; never claim the attempt's descendants
        # were reaped or that only the worker's disappearance proves cleanup.
        try:
            os.kill(process.pid, signal.SIGKILL)
            process.wait(timeout=0.2)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return rescue


def _validate(argv, cwd, env, attempt_dir, timeout, cleanup, stdout_limit,
              stderr_limit, stdin_path, executable_path):
    if not isinstance(argv, (list, tuple)) or not argv:
        raise ValueError("argv must be a nonempty list or tuple of strings")
    if any(not isinstance(arg, str) or "\0" in arg for arg in argv):
        raise ValueError("argv entries must be strings without NUL")
    if executable_path is not None:
        executable_path = os.fspath(executable_path)
        if not isinstance(executable_path, str) or "\0" in executable_path \
                or not os.path.isabs(executable_path):
            raise ValueError("executable_path must be absolute and contain no NUL")
    elif not argv[0] or not os.path.isabs(argv[0]):
        raise ValueError("nonabsolute argv[0] requires an explicit executable_path")
    if not isinstance(env, dict) or any(
            not isinstance(key, str) or not key or "=" in key or "\0" in key
            or not isinstance(value, str) or "\0" in value
            for key, value in env.items()):
        raise ValueError("env must be an explicit string-to-string dictionary")
    for name, value in (("timeout_seconds", timeout),
                        ("cleanup_timeout_seconds", cleanup)):
        if isinstance(value, bool) or not isinstance(value, (float, int)) \
                or not math.isfinite(value) or value <= 0:
            raise ValueError(name + " must be positive and finite")
    for name, value in (("stdout_limit_bytes", stdout_limit),
                        ("stderr_limit_bytes", stderr_limit)):
        if type(value) is not int or value < 0:
            raise ValueError(name + " must be a nonnegative integer")
    cwd = Path(cwd)
    attempt_dir = Path(attempt_dir)
    if not cwd.is_absolute() or not cwd.is_dir():
        raise ValueError("cwd must name an existing absolute directory")
    if not attempt_dir.is_absolute():
        raise ValueError("attempt_dir must be absolute")
    if stdin_path is not None:
        stdin_path = Path(stdin_path)
        if not stdin_path.is_absolute():
            raise ValueError("stdin_path must be absolute")
    return {
        "schema_version": SCHEMA_VERSION, "argv": list(argv),
        "executable_path": executable_path or argv[0],
        "cwd": str(cwd), "env": dict(env),
        "timeout_seconds": float(timeout),
        "cleanup_timeout_seconds": float(cleanup),
        "stdout_limit_bytes": stdout_limit,
        "stderr_limit_bytes": stderr_limit,
        "stdin_path": str(stdin_path) if stdin_path is not None else None,
    }, attempt_dir


def run_supervised(argv, *, cwd, env, attempt_dir, timeout_seconds,
                   cleanup_timeout_seconds, stdout_limit_bytes,
                   stderr_limit_bytes, stdin_path=None, executable_path=None):
    """Run argv without a shell, preserving bounded artifacts in a fresh directory.

    Bad arguments and an existing attempt raise before launch. Execution/setup
    failures return a report. COMPLETED means collection succeeded, including a
    nonzero exit or signal; the caller must apply its independent oracle. The
    caller also supplies the outer VM/container deadline and resource limits.
    """
    request, directory = _validate(
        argv, cwd, env, attempt_dir, timeout_seconds, cleanup_timeout_seconds,
        stdout_limit_bytes, stderr_limit_bytes, stdin_path, executable_path)
    directory.mkdir(mode=0o700)
    _write_json(directory / "request.json", request)
    # A separate worker keeps subreaper state and descendant waits out of the
    # caller, which may be multithreaded or supervising unrelated processes.
    command = _worker_command(directory)
    rescue = None
    parent_exception = None
    # Reserve part of the declared cleanup allowance for emergency ownership
    # recovery instead of spending that allowance twice after a worker stall.
    normal_cleanup_allowance = min(1.0, cleanup_timeout_seconds / 2.0)
    rescue_allowance = cleanup_timeout_seconds - normal_cleanup_allowance
    with (directory / "worker.stderr").open("xb") as diagnostics:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=diagnostics,
                                   close_fds=True, env={}, start_new_session=True)
        # This deadline remains live if the worker is stopped or fails to enter
        # its normal stream pump. The outer VM deadline remains the caller's
        # responsibility; this timer cannot substitute for that independent OS.
        try:
            code = process.wait(timeout=timeout_seconds + normal_cleanup_allowance + 1.0)
        except subprocess.TimeoutExpired:
            rescue = _rescue_worker(process, rescue_allowance)
            code = process.returncode
        except (KeyboardInterrupt, SystemExit) as error:
            parent_exception = error
            rescue = _rescue_worker(process, cleanup_timeout_seconds)
            rescue["reason"] = "parent interrupted"
            code = process.returncode
        diagnostics.flush()
        os.fsync(diagnostics.fileno())
    report_path = directory / "report.json"
    if rescue is not None or code != 0 or not report_path.is_file():
        report = {"schema_version": SCHEMA_VERSION,
                  "status": "SUPERVISOR_ERROR", "application_acceptance": False,
                  "error": "private worker failed to publish its report",
                  "worker_returncode": code, "cleanup_complete": False,
                  "raw_wait_status": None, "wait_status": None,
                  "diagnostics": _identity(directory / "worker.stderr")}
        if rescue is not None:
            report["watchdog_rescue"] = rescue
        if parent_exception is not None:
            report["status"] = "INTERRUPTED"
            report["error"] = "parent interrupted while collecting private worker"
        if report_path.is_file():
            report["original_worker_report"] = _identity(report_path)
        # Never replace a partial or previously published report.
        _write_json(directory / "worker-failure.json", report)
        if parent_exception is not None:
            raise parent_exception
        return report
    with report_path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _set_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    # PR_SET_CHILD_SUBREAPER is Linux prctl option 36. Confirm the setting via
    # PR_GET_CHILD_SUBREAPER (37), rather than assuming successful adoption.
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER failed")
    active = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(active), 0, 0, 0) != 0 or active.value != 1:
        raise OSError(ctypes.get_errno(), "PR_GET_CHILD_SUBREAPER failed")
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)


def _children_of(pid):
    text = Path("/proc/{}/task/{}/children".format(pid, pid)).read_text()
    return [int(value) for value in text.split()]


def _children():
    return _children_of(os.getpid())


def _exited(pid):
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def _process_identity(pid):
    text = Path("/proc/{}/stat".format(pid)).read_text()
    tail = text[text.rfind(")") + 2:].split()
    return {"pid": pid, "state": tail[0], "ppid": int(tail[1]), "pgid": int(tail[2]),
            "session": int(tail[3]), "starttime_ticks": int(tail[19])}


def _open_stdin(path):
    if path is None:
        return open(os.devnull, "rb"), {"kind": "devnull"}
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(descriptor, "rb")
    try:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("stdin_path must be a regular, nonsymlink file")
        digest = hashlib.sha256()
        remaining = metadata.st_size
        while remaining:
            block = stream.read(min(_READ_SIZE, remaining))
            if not block:
                raise ValueError("stdin file changed during identity capture")
            digest.update(block)
            remaining -= len(block)
        after = os.fstat(stream.fileno())
        if (metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns) != \
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("stdin file changed during identity capture")
        stream.seek(0)
        os.set_blocking(stream.fileno(), True)
        return stream, {"kind": "file", "path": path, "size": metadata.st_size,
                        "sha256": digest.hexdigest()}
    except BaseException:
        stream.close()
        raise


def _worker(directory):
    request = json.loads((directory / "request.json").read_text())
    start = time.monotonic()
    report = dict(request)
    report.update(status="SUPERVISOR_ERROR", application_acceptance=False,
                  raw_wait_status=None, wait_status=None, cleanup_complete=False,
                  monotonic_started=start, events=[], descendants=[],
                  descendant_records_omitted=0, uid=os.getuid(), gid=os.getgid(),
                  groups=os.getgroups(), supervisor_pid=os.getpid(),
                  fd_setup={"stdin": "regular file or /dev/null",
                            "stdout": "owned pipe", "stderr": "separate owned pipe",
                            "close_fds": True, "pass_fds": []},
                  provenance="Linux process collection only; no McKernel evidence")
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("Umask:"):
            report["umask"] = line.split()[1]
    selector = selectors.DefaultSelector()
    streams = {}
    process = None
    stdin = None
    cleanup_started = None
    leader_done = False
    group_signaled = False
    group_killed = False
    killed = set()
    child_records = set()
    interrupted = []

    def interrupt(signum, frame):
        del frame
        interrupted.append(signum)

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)

    def event(kind, **values):
        report["events"].append(dict(kind=kind, monotonic=time.monotonic(), **values))

    def begin_cleanup(reason):
        nonlocal cleanup_started
        if cleanup_started is None:
            cleanup_started = time.monotonic()
            event("cleanup_started", reason=reason)

    def drain(wait):
        for key, _ in selector.select(wait):
            entry = streams[key.data]
            try:
                data = os.read(key.fd, _READ_SIZE)
            except BlockingIOError:
                continue
            if not data:
                selector.unregister(key.fd)
                entry["pipe"].close()
                entry["eof"] = True
                continue
            entry["bytes_observed"] += len(data)
            retained = data[:max(0, entry["limit_bytes"] - entry["bytes_retained"])]
            entry["file"].write(retained)
            entry["file"].flush()
            entry["bytes_retained"] += len(retained)
            if len(retained) != len(data):
                entry["truncated"] = True
                if report["status"] == "COMPLETED":
                    report["status"] = "OUTPUT_LIMIT"
                begin_cleanup("output_limit")

    def signal_group(sig):
        # No Popen.poll()/wait() or waitpid has reaped this leader. Its PID
        # still reserves the process-group number even after its exit.
        try:
            os.killpg(process.pid, sig)
            event("signal_owned_group", pgid=process.pid, signal=sig)
        except ProcessLookupError:
            pass

    def remember_child(pid):
        if pid in child_records:
            return
        child_records.add(pid)
        if len(report["descendants"]) < _MAX_CHILD_RECORDS:
            report["descendants"].append(_process_identity(pid))
        else:
            report["descendant_records_omitted"] += 1

    def collect_children(force):
        remaining = []
        for pid in _children():
            if pid == process.pid:
                continue
            remember_child(pid)
            if _exited(pid):
                _, raw = os.waitpid(pid, os.WNOHANG)
                if len(report["events"]) < 3 * _MAX_CHILD_RECORDS:
                    event("reaped_descendant", pid=pid, raw_wait_status=raw,
                          wait_status=_decode_wait(raw))
                continue
            remaining.append(pid)
            if force and pid not in killed:
                # This is our unreaped direct child in a private worker. No
                # other thread, handler, or wait call can release its PID.
                os.kill(pid, signal.SIGKILL)
                killed.add(pid)
                if len(report["events"]) < 3 * _MAX_CHILD_RECORDS:
                    event("signal_owned_child", pid=pid, signal=signal.SIGKILL)
        return remaining

    try:
        _set_subreaper()
        for name in ("stdout", "stderr"):
            streams[name] = {"file": (directory / (name + ".bin")).open("xb"),
                             "bytes_observed": 0, "bytes_retained": 0,
                             "limit_bytes": request[name + "_limit_bytes"],
                             "truncated": False, "eof": False}
        stdin, report["stdin"] = _open_stdin(request["stdin_path"])
        try:
            report["executable"] = _identity(Path(request["executable_path"]).resolve(strict=True))
            # Start before the child can execute. A delayed Popen return or
            # identity read must not grant additional application runtime.
            report["payload_monotonic_started"] = time.monotonic()
            deadline = report["payload_monotonic_started"] + request["timeout_seconds"]
            report["payload_monotonic_deadline"] = deadline
            process = subprocess.Popen(request["argv"], cwd=request["cwd"],
                                       executable=request["executable_path"],
                                       env=request["env"], stdin=stdin,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       close_fds=True, start_new_session=True)
        except OSError as error:
            report.update(status="LAUNCH_ERROR", error=str(error), errno=error.errno,
                          cleanup_complete=True)
            return report
        report["process"] = _process_identity(process.pid)
        report["status"] = "COMPLETED"
        for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(pipe.fileno(), False)
            streams[name]["pipe"] = pipe
            selector.register(pipe, selectors.EVENT_READ, name)
        while True:
            leader_done = _exited(process.pid)
            now = time.monotonic()
            if leader_done and "payload_completion_observed_monotonic" not in report:
                report["payload_completion_observed_monotonic"] = now
            if interrupted:
                report["status"] = "INTERRUPTED"
                report["interrupt_signal"] = interrupted[0]
                begin_cleanup("supervisor_interrupted")
            if now >= deadline and (not leader_done or
                    report["payload_completion_observed_monotonic"] > deadline):
                if report["status"] == "COMPLETED":
                    report["status"] = "TIMED_OUT"
                begin_cleanup("payload_deadline")
            if leader_done:
                begin_cleanup("leader_exited")
            if cleanup_started is not None:
                force = now >= cleanup_started + min(0.2, request["cleanup_timeout_seconds"] / 4)
                descendants = collect_children(force)
                if child_records and report["status"] == "COMPLETED":
                    report["status"] = "ORPHANED_DESCENDANTS"
                if not group_signaled and (not leader_done or descendants):
                    signal_group(signal.SIGTERM)
                    group_signaled = True
                if force and not leader_done and not group_killed:
                    signal_group(signal.SIGKILL)
                    group_killed = True
                # Session-escaping descendants can reparent in successive
                # generations after each parent is killed. Check again before
                # releasing the leader's identity.
                remaining = [pid for pid in _children() if pid != process.pid]
                if leader_done and not remaining and not selector.get_map():
                    report["cleanup_complete"] = True
                    break
                if now >= cleanup_started + request["cleanup_timeout_seconds"]:
                    report["collection_status_before_cleanup_failure"] = report["status"]
                    report["status"] = "CLEANUP_ERROR"
                    report["unreaped_children"] = _children()
                    break
            next_deadline = (cleanup_started + request["cleanup_timeout_seconds"]
                             if cleanup_started is not None else deadline)
            drain(max(0.0, min(0.02, next_deadline - time.monotonic())))
        if leader_done:
            pid, raw = os.waitpid(process.pid, os.WNOHANG)
            if pid != process.pid:
                raise RuntimeError("exited owned leader could not be reaped")
            report["raw_wait_status"] = raw
            report["wait_status"] = _decode_wait(raw)
            process.returncode = os.waitstatus_to_exitcode(raw)
        return report
    except BaseException as error:
        report.update(status="SUPERVISOR_ERROR", error="{}: {}".format(type(error).__name__, error))
        if process is None:
            report["cleanup_complete"] = True
        # Preserve the first collection error and perform only bounded cleanup.
        if process is not None and process.returncode is None:
            try:
                signal_group(signal.SIGKILL)
                end = time.monotonic() + request["cleanup_timeout_seconds"]
                while time.monotonic() < end:
                    collect_children(True)
                    if _exited(process.pid) and _children() == [process.pid]:
                        _, raw = os.waitpid(process.pid, os.WNOHANG)
                        report["raw_wait_status"] = raw
                        report["wait_status"] = _decode_wait(raw)
                        process.returncode = os.waitstatus_to_exitcode(raw)
                        report["cleanup_complete"] = True
                        break
                    time.sleep(0.01)
            except BaseException as cleanup_error:
                report["cleanup_error"] = str(cleanup_error)
        return report
    finally:
        if stdin is not None:
            stdin.close()
        selector.close()
        report["streams"] = {}
        for name, entry in streams.items():
            if "pipe" in entry and not entry["pipe"].closed:
                entry["pipe"].close()
            entry["file"].flush()
            os.fsync(entry["file"].fileno())
            entry["file"].close()
            report["streams"][name] = {
                key: value for key, value in entry.items() if key not in ("file", "pipe")}
            report["streams"][name]["artifact"] = _identity(directory / (name + ".bin"))
            report["streams"][name]["discarded_observed_bytes"] = (
                entry["bytes_observed"] - entry["bytes_retained"])
        report["monotonic_finished"] = time.monotonic()
        report["elapsed_seconds"] = report["monotonic_finished"] - start
        _write_json(directory / "report.json", report)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--worker":
        raise SystemExit("Use run_supervised(); --worker is a private interface")
    _worker(Path(sys.argv[2]))
