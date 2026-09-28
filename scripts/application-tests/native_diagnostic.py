#!/usr/bin/env python3
"""Manifest-bound, direct-QEMU diagnostic adapter.

This module deliberately has no guest/backend side effects at import time.  The
three stages (prepare, command, evaluate) are separate so review tests can use
fake process and QMP observations.  A diagnostic result is never application
acceptance.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time
import signal
import threading
from contextlib import contextmanager

QEMU = "/usr/libexec/qemu-kvm"
MAX_JSON = 4 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
ARTIFACTS = ("bzImage", "initramfs", "root_base", "mckernel_image", "mcexec", "payload")
MODULE_NAMES = ("ihk.ko", "ihk-smp-x86_64.ko", "mcctrl.ko")
APPEND = "console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1 memmap=4K%0x80000-1"
BAD_MARKERS = re.compile(
    r"panic|oops|BUG:|\bBUG\b|\berror\b|WARNING|soft lockup|hard LOCKUP|"
    r"clear_host_pte failed|rcu_preempt detected stalls|\bFAIL\b|"
    r"cleanup retained|reap_retained|strncpy_from_user:ioctl:|ret: ", re.I)
STAGING_BLOCKER = (
    "guest staging unavailable: the v1 manifest has no bound retained root-tree "
    "inventory, native-boot/runtime library closure, or guest raw-wait/EOF "
    "collector and serial transport; copied initramfs/root files are not staged")


class DiagnosticError(ValueError):
    pass


def _need(ok, message):
    if not ok:
        raise DiagnosticError(message)


def _keys(obj, required, optional=()):
    _need(isinstance(obj, dict), "expected object")
    _need(set(obj) == set(required) | set(optional), "manifest keys differ")


def _ref(ref, name):
    _keys(ref, ("path", "size", "sha256", "mode"))
    path = ref["path"]
    _need(isinstance(path, str) and os.path.isabs(path) and "\0" not in path, name + " path")
    _need(str(Path(path).resolve(strict=True)) == path, name + " path is not canonical")
    _need(type(ref["size"]) is int and 0 <= ref["size"] <= 95 * 1024 * 1024, name + " size")
    _need(isinstance(ref["sha256"], str) and SHA.fullmatch(ref["sha256"]), name + " sha256")
    _need(type(ref["mode"]) is int and stat.S_ISREG(ref["mode"]) and
          0 <= (ref["mode"] & 0o777) <= 0o777,
          name + " mode")
    st = os.lstat(path)
    _need(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode), name + " must be regular, non-symlink")
    _need((st.st_mode & 0o777) == (ref["mode"] & 0o777) and st.st_size == ref["size"], name + " size/mode drift")
    digest = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    _need(digest.hexdigest() == ref["sha256"], name + " hash drift")
    return dict(ref)


def _typed_string(value, label):
    _need(type(value) is str and "\0" not in value, label)
    return value


def load_manifest(path):
    """Load strict canonical JSON and bind every reviewed input."""
    path = os.fspath(path)
    _need(os.path.isabs(path) and str(Path(path).resolve(strict=True)) == path, "manifest path")
    data = Path(path).read_bytes()
    _need(len(data) <= MAX_JSON, "manifest too large")
    try:
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=lambda pairs: _pairs(pairs))
    except (UnicodeError, json.JSONDecodeError, DiagnosticError) as exc:
        raise DiagnosticError("malformed manifest") from exc
    _keys(obj, ("schema_version", "kind", "case_id", "artifacts", "modules", "profile", "payload"))
    _need(type(obj["schema_version"]) is int and obj["schema_version"] == 1 and obj["kind"] == "native-diagnostic-manifest", "manifest identity")
    _need(isinstance(obj["case_id"], str) and obj["case_id"] and "\0" not in obj["case_id"], "case_id")
    _keys(obj["artifacts"], ARTIFACTS)
    bound = {name: _ref(obj["artifacts"][name], name) for name in ARTIFACTS}
    _need(isinstance(obj["modules"], list) and len(obj["modules"]) == 3, "exactly three modules")
    modules = [_ref(ref, "module") for ref in obj["modules"]]
    _need(tuple(Path(ref["path"]).name for ref in modules) == MODULE_NAMES, "module inventory")
    _need(isinstance(obj["profile"], dict) and set(obj["profile"]) <= {"memory_mib", "vcpus", "numa_nodes", "append"}
          and {"memory_mib", "vcpus", "numa_nodes"} <= set(obj["profile"]), "profile keys")
    profile = obj["profile"]
    _need(all(type(profile[k]) is int for k in ("memory_mib", "vcpus", "numa_nodes")) and
          profile["memory_mib"] == 8192 and profile["vcpus"] == 4 and profile["numa_nodes"] == 2, "profile differs")
    append = profile.get("append", APPEND)
    _need(append == APPEND, "kernel append differs from retained profile")
    _keys(obj["payload"], ("cwd", "argv", "env", "oracle", "stdout_limit_bytes", "stderr_limit_bytes"))
    payload = obj["payload"]
    _need(payload["cwd"] == "/case/work" and payload["argv"] == ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"], "payload contract")
    _need(payload["env"] == {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"}, "frozen environment")
    oracle = payload["oracle"]
    _keys(oracle, ("stdout_hex", "stderr_hex", "exit_code"))
    _need(type(oracle["stdout_hex"]) is str and re.fullmatch(r"(?:[0-9a-fA-F]{2})*", oracle["stdout_hex"]), "oracle stdout")
    _need(type(oracle["stderr_hex"]) is str and re.fullmatch(r"(?:[0-9a-fA-F]{2})*", oracle["stderr_hex"]), "oracle stderr")
    _need(type(oracle["exit_code"]) is int and not isinstance(oracle["exit_code"], bool) and 0 <= oracle["exit_code"] <= 255, "oracle exit")
    for name in ("stdout", "stderr"):
        limit = payload[name + "_limit_bytes"]
        _need(type(limit) is int and 0 <= limit <= MAX_JSON and len(bytes.fromhex(oracle[name + "_hex"])) <= limit, "stream limit")
    return {"schema_version": 1, "kind": obj["kind"], "case_id": obj["case_id"], "artifacts": bound,
            "modules": modules, "profile": {"memory_mib": 8192, "vcpus": 4, "numa_nodes": 2, "append": append},
            "payload": dict(payload)}


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        _need(key not in out, "duplicate JSON key")
        out[key] = value
    return out


def prepare_attempt(manifest, parent, name):
    """Reserve evidence space, not a bootable guest; see STAGING_BLOCKER."""
    parent = Path(parent)
    _need(parent.is_absolute() and parent.is_dir() and not parent.is_symlink(), "attempt parent")
    _need(isinstance(name, str) and name and "/" not in name and name not in (".", ".."), "attempt name")
    attempt = parent / name
    _need(not os.path.lexists(attempt), "existing attempt")
    try:
        os.mkdir(attempt, 0o700)
    except FileExistsError as exc:
        raise DiagnosticError("existing attempt") from exc
    try:
        for filename in ("serial.log", "debugcon.log"):
            (attempt / filename).touch(mode=0o600, exist_ok=False)
    except BaseException as exc:
        write_record(attempt, {"status": "FAIL", "application_acceptance": False},
                     {"phase": "prepare", "type": type(exc).__name__, "error": str(exc)})
        raise
    return attempt


def build_command(manifest, attempt):
    """Return a non-executable staging plan matching retained runner-1.py.

    No staged initrd is produced here.  The runtime entry point fails closed.
    """
    attempt = Path(attempt)
    _need(attempt.is_dir() and (attempt.stat().st_mode & 0o777) == 0o700, "attempt not private")
    a = manifest["artifacts"]
    qmp = str(attempt / "qmp.sock")
    _need(not os.path.lexists(qmp), "stale QMP socket")
    argv = [QEMU, "-machine", "q35", "-accel", "tcg,thread=multi", "-cpu", "max,la57=off",
            "-smp", "4,sockets=2,cores=2,threads=1", "-m", "8192",
            "-object", "memory-backend-ram,size=4G,id=ram-node0",
            "-object", "memory-backend-ram,size=4G,id=ram-node1",
            "-numa", "node,nodeid=0,cpus=0-1,memdev=ram-node0",
            "-numa", "node,nodeid=1,cpus=2-3,memdev=ram-node1",
            "-nic", "none", "-display", "none", "-no-reboot", "-no-shutdown", "-monitor", "none",
            "-qmp", "unix:" + qmp + ",server=on,wait=off", "-serial", "file:" + str(attempt / "serial.log"),
            "-debugcon", "file:" + str(attempt / "debugcon.log"), "-global", "isa-debugcon.iobase=0xe9",
            "-kernel", a["bzImage"]["path"], "-initrd", str(attempt / "initramfs.cpio.gz"), "-append", APPEND]
    overlay = {"modules": [m["path"] for m in manifest["modules"]], "mckernel_image": a["mckernel_image"]["path"],
               "mcexec": a["mcexec"]["path"], "payload": a["payload"]["path"], "load_modules": list(MODULE_NAMES),
               "boot_contract": "native-boot-v1", "guest_destinations": {"/images/mckernel.img": a["mckernel_image"]["path"],
               "/bin/mcexec": a["mcexec"]["path"], "/apps/app": a["payload"]["path"]},
               "init_sequence": ["insmod /modules/ihk.ko", "insmod /modules/ihk-smp-x86_64.ko ihk_trampoline=524288",
                                 "insmod /modules/mcctrl.ko", "/bin/native-boot", "cd /case/work"],
               "transport": "guest collector framed serial report; never QEMU stdout"}
    return {"argv": argv, "overlay": overlay, "payload": manifest["payload"], "qmp_socket": qmp,
            "runtime_ready": False, "blocker": STAGING_BLOCKER}


def evaluate(manifest, observation):
    """Validate serial evidence shape only; this is not runtime acceptance.

    The report must originate in a separately reviewed guest collector.  Until
    that collector and staging exist, the sole caller is the fake-backend test
    harness and a passing result is explicitly PROTOCOL_PASS.
    """
    _keys(observation, ("serial", "debugcon", "qmp", "teardown", "started_at", "finished_at", "deadline"))
    for name in ("started_at", "finished_at", "deadline"):
        _need(type(observation[name]) in (int, float) and math.isfinite(observation[name]), "host timestamp")
    _need(0 <= observation["started_at"] <= observation["finished_at"] < observation["deadline"], "late completion")
    serial = observation["serial"]
    _need(type(serial) is str and type(observation["debugcon"]) is str and
          not BAD_MARKERS.search(serial + "\n" + observation["debugcon"]), "kernel failure marker")
    _need(observation["qmp"] == {"status": "shutdown"}, "QMP terminal status")
    _need(observation["teardown"] is True, "teardown uncertain")
    lines = [line[len("ND_PAYLOAD "):] for line in serial.splitlines() if line.startswith("ND_PAYLOAD ")]
    _need(len(lines) == 1 and len(lines[0]) <= MAX_JSON, "missing/duplicate/oversize guest payload report")
    report = json.loads(lines[0], object_pairs_hook=_pairs)
    _keys(report, ("argv", "cwd", "env", "raw_wait_status", "started_ns", "reaped_ns", "finished_ns", "streams", "procfs_empty"))
    for name in ("argv", "cwd", "env"):
        _need(report[name] == manifest["payload"][name], "guest launch contract " + name)
    for name in ("started_ns", "reaped_ns", "finished_ns"):
        _need(type(report[name]) is int and report[name] > 0, "guest timestamp")
    _need(report["started_ns"] <= report["reaped_ns"] <= report["finished_ns"], "guest timestamp ordering")
    raw = report["raw_wait_status"]
    _need(type(raw) is int and 0 <= raw <= 65535 and os.WIFEXITED(raw), "raw wait status")
    _need(os.WEXITSTATUS(raw) == manifest["payload"]["oracle"]["exit_code"], "wrong payload exit")
    _need(report["procfs_empty"] is True, "guest registrations remain")
    _keys(report["streams"], ("stdout", "stderr"))
    for name in ("stdout", "stderr"):
        stream = report["streams"][name]
        _keys(stream, ("hex", "eof", "truncated", "observed", "retained", "discarded", "limit", "eof_ns"))
        _need(type(stream["hex"]) is str and re.fullmatch(r"(?:[0-9a-f]{2})*", stream["hex"]), "stream hex")
        data = bytes.fromhex(stream["hex"])
        limit = manifest["payload"][name + "_limit_bytes"]
        _need(stream["eof"] is True and stream["truncated"] is False, "incomplete stream")
        for field in ("observed", "retained", "discarded", "limit", "eof_ns"):
            _need(type(stream[field]) is int and stream[field] >= 0, "stream accounting type")
        _need(stream["limit"] == limit and stream["observed"] == stream["retained"] == len(data) <= limit
              and stream["discarded"] == 0, "stream accounting")
        _need(report["started_ns"] <= stream["eof_ns"] <= report["finished_ns"], "EOF timestamp")
        _need(data == bytes.fromhex(manifest["payload"]["oracle"][name + "_hex"]), "wrong payload bytes")
    schedules = re.findall(r"application SCHEDULE os=0 generation=1 pid=(\d+) cpu=0\b", serial)
    _need(len(schedules) == 1, "guest scheduling evidence")
    prefix = r"os=0 generation=1 pid=" + schedules[0]
    for pattern in (r"application retirement " + prefix + r" token=\d+ errno=0\b",
                    r"application_process=release " + prefix + r" cleanup_errno=0\b",
                    *[r"application procfs " + op + " " + prefix + " tid=" + schedules[0] + r"\b"
                      for op in ("published", "deleted")]):
        _need(len(re.findall(pattern, serial)) == 1, "retirement/release evidence")
    _check_syscall_trace(serial, prefix)
    return {"schema_version": 1, "kind": "native-diagnostic-result", "case_id": manifest["case_id"],
            "status": "PROTOCOL_PASS", "application_acceptance": False, "mckernel_application_executed": False,
            "guest_report": report, "observation": observation, "runtime_blocker": STAGING_BLOCKER}


def _check_syscall_trace(serial, prefix):
    """Join every sampled delivery; exit_group deliberately has no RET.

    mcctrl_process.rs::return_syscall prints return_route only when the Linux
    worker slot differs from the saved guest CPU, before printing returned.
    mcexec.c::init_worker_threads allocates slots 0..n_threads inclusive: the
    frozen -t 1 invocation therefore permits slots 0 and 1, not host CPU IDs.
    The exit/exit_group branch (and Rust act_exit) retires without RET. This
    single-thread startup fixture requires one final exit_group (231).
    """
    suffixes = {
        "delivered": r"worker=(\d+) delivery=(\d+) cpu=(\d+) number=(\d+)",
        "returned": r"worker=(\d+) delivery=(\d+) cpu=(\d+) value=(-?\d+)",
        "return_route": r"worker=(\d+) delivery=(\d+) launcher_cpu=(-?\d+) guest_cpu=(\d+)",
    }
    records = {name: {} for name in suffixes}
    for position, line in enumerate(serial.splitlines()):
        for name, suffix in suffixes.items():
            marker = "application_syscall=" + name + " "
            if marker not in line:
                continue
            match = re.search(re.escape(marker) + prefix + " " + suffix + r"\s*$", line)
            _need(match is not None, "malformed or foreign syscall trace")
            row = tuple(int(value) for value in match.groups())
            key = row[:2]
            _need(all(0 < value < 2**64 for value in key), "invalid worker/delivery identity")
            _need(key not in records[name], "duplicate syscall " + name)
            records[name][key] = (row[2:], position)
    delivered, returned, routes = (records[name] for name in suffixes)
    exits = {key for key, (row, _) in delivered.items() if row[1] == 231}
    _need(delivered and returned and routes and len(exits) == 1, "missing actual route/exit evidence")
    _need(all(row[1] != 60 for row, _ in delivered.values()), "unexpected non-group exit")
    ordinary = set(delivered) - exits
    _need(set(returned) == ordinary and set(routes) <= ordinary, "incomplete syscall correspondence")
    exit_position = delivered[next(iter(exits))][1]
    _need(all(row[0] == 0 for row, _ in delivered.values()) and
          all(row[0] == 0 for row, _ in returned.values()), "unexpected guest CPU")
    worker_slots = {}
    for key in ordinary:
        begin, end = delivered[key][1], returned[key][1]
        _need(begin < end < exit_position, "syscall/terminal-exit ordering")
        slot = 0
        if key in routes:
            (launcher, guest), position = routes[key]
            _need(launcher == 1 and guest == 0 and begin < position < end,
                  "route identity/CPU mismatch")
            slot = launcher
        # An absent route means equal CPU (slot 0), not unknown. A worker
        # cannot switch its assigned slot between sampled deliveries.
        _need(worker_slots.setdefault(key[0], slot) == slot, "missing/inconsistent worker route")
    for marker in ("application retirement ", "application_process=release "):
        positions = [i for i, line in enumerate(serial.splitlines()) if marker in line]
        _need(positions and all(i > exit_position for i in positions), "retirement precedes terminal exit")


def run_diagnostic(manifest, attempt, process_factory=None, qmp_factory=None, timeout=300):
    """Fail before spawning until real guest staging/collector is implemented."""
    failure = {"phase": "staging", "type": "DiagnosticError", "error": STAGING_BLOCKER}
    write_record(attempt, {"status": "BLOCKED", "application_acceptance": False,
                          "mckernel_application_executed": False, "failure": failure}, failure)
    raise DiagnosticError(STAGING_BLOCKER)


@contextmanager
def _alarm(deadline):
    """Interrupt blocking Python/socket operations, not just check afterwards.

    Main-thread-only Unix test harness. Refuse to steal an existing alarm.
    A future runtime backend needs its own independent reviewed execution gate.
    """
    _need(threading.current_thread() is threading.main_thread(), "deadline requires main thread")
    _need(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), "existing deadline timer")
    remaining = deadline - time.monotonic()
    _need(remaining > 0, "absolute deadline expired")
    old = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise TimeoutError("absolute deadline expired")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, remaining)
    try:
        yield remaining
        _need(time.monotonic() < deadline, "late completion")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _method(deadline, owner, name, *, accepts_timeout=True):
    # Attribute lookup itself can raise or block (properties/proxies). It is
    # part of the protected operation, not an argument evaluated beforehand.
    with _alarm(deadline) as remaining:
        method = getattr(owner, name)
        return method(timeout=remaining) if accepts_timeout else method()


def _cleanup(process, qmp):
    """Keep each cleanup step independent; QMP errors cannot skip reaping."""
    deadline = time.monotonic() + 5
    errors = []
    def step(label, owner, name, allowance=1, accepts_timeout=True):
        try:
            return _method(min(deadline, time.monotonic() + allowance), owner, name,
                           accepts_timeout=accepts_timeout)
        except BaseException as exc:
            errors.append({"phase": label, "type": type(exc).__name__, "error": str(exc)})
            return None
    # Never use QMP as the sole process-lifetime authority.
    if qmp is not None:
        step("qmp-quit", qmp, "terminate", allowance=0.5)
    reaped = process is None
    if process is not None:
        step("terminate", process, "terminate", allowance=0.25, accepts_timeout=False)
        status = step("wait", process, "wait", allowance=1)
        if type(status) is int:
            reaped = True
        else:
            step("kill", process, "kill", allowance=0.25, accepts_timeout=False)
            status = step("reap", process, "wait", allowance=2)
            reaped = type(status) is int
    if qmp is not None:
        step("qmp-close", qmp, "close", allowance=0.5)
    return {"reaped": reaped, "errors": errors}


def exercise_lifecycle(manifest, attempt, process_factory, qmp_factory, timeout=300):
    """Protocol-only injected-backend exercise; never reports a guest PASS.

    This entry point is solely for local tests, not an execution release. Fake
    processes receive no QEMU command, so a raw subprocess factory cannot run
    a guest accidentally. QMP/backend methods accept a remaining timeout; an
    independent SIGALRM bounds them even if they ignore that argument.
    """
    process = qmp = None
    failure = None
    observation = {}
    try:
        _need(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 3600, "finite deadline")
        started = time.monotonic()
        deadline = started + timeout
        # Assign owners inside the alarm context. If a factory returns after
        # the deadline, the post-call check must not lose the returned handle.
        with _alarm(deadline) as remaining:
            process = process_factory(timeout=remaining)
        with _alarm(deadline) as remaining:
            qmp = qmp_factory(timeout=remaining)
        _method(deadline, qmp, "negotiate")
        _method(deadline, qmp, "resume")
        terminal = _method(deadline, qmp, "wait_shutdown")
    except BaseException as exc:
        failure = {"phase": "lifecycle", "type": type(exc).__name__, "error": str(exc)}
    finally:
        # No filesystem journal or capture runs before retirement: blocked
        # storage cannot delay termination/reaping after a QMP failure.
        cleanup = _cleanup(process, qmp)
    try:
        if failure is not None:
            raise DiagnosticError(failure["error"])
        _need(cleanup["reaped"] and not cleanup["errors"], "teardown uncertain")
        # Capture only after QEMU has been reaped, including shutdown/teardown
        # warnings. QEMU stdout/stderr are never payload streams/status.
        host_stdout, host_stderr = _method(deadline, process, "communicate")
        _need(type(host_stdout) is bytes and type(host_stderr) is bytes, "backend log types")
        _need(len(host_stdout) <= MAX_JSON and len(host_stderr) <= MAX_JSON, "host capture limit exceeded")
        with _alarm(deadline):
            for name, data in (("qemu.stdout", host_stdout), ("qemu.stderr", host_stderr)):
                with (Path(attempt) / name).open("xb") as stream:
                    stream.write(data)
            texts = {}
            for name in ("serial", "debugcon"):
                with (Path(attempt) / (name + ".log")).open("rb") as stream:
                    data = stream.read(MAX_JSON + 1)
                _need(len(data) <= MAX_JSON, "capture limit exceeded")
                texts[name] = data.decode("utf-8", errors="strict")
            observation = dict(texts, qmp=terminal, teardown=True, started_at=started,
                               finished_at=time.monotonic(), deadline=deadline)
            record = evaluate(manifest, observation)
    except BaseException as exc:
        if failure is None:
            failure = {"phase": "evaluation", "type": type(exc).__name__, "error": str(exc)}
    if failure is not None:
        record = {"status": "FAIL", "application_acceptance": False,
                  "mckernel_application_executed": False, "failure": failure}
    record["cleanup"] = cleanup
    # The first observed failure survives cleanup failures; journal only after
    # retirement, under its own bounded publication deadline.
    with _alarm(time.monotonic() + 2):
        write_record(attempt, record, failure)
    if failure is not None:
        raise DiagnosticError(failure["error"])
    return record


def _append_failure(attempt, failure):
    journal = Path(attempt) / "first-failure.jsonl"
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(failure, sort_keys=True, allow_nan=False) + "\n")
        stream.flush(); os.fsync(stream.fileno())


def write_record(attempt, record, failure=None):
    """Append failure evidence and atomically link an irreversible final record.

    No replace operation: a concurrent publisher or dangling target symlink
    cannot overwrite the first terminal result. I/O failures remain failures.
    """
    attempt = Path(attempt)
    target = attempt / "result.json"
    _need(not os.path.lexists(target), "final record already published")
    if failure is not None:
        _append_failure(attempt, failure)
    fd, tmp = tempfile.mkstemp(prefix=".result.", dir=attempt)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True, allow_nan=False); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.link(tmp, target, follow_symlinks=False)
        dfd = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY); os.fsync(dfd); os.close(dfd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
