#!/usr/bin/env python3
"""Direct, durable owner for the storage-fault-v2 collector (not a release)."""
import argparse
import ctypes
import errno
import hashlib
import itertools
import json
import os
import select
import signal
import socket
import stat
import sys
import time
from pathlib import Path

WITNESS_FD = 198
PACKET_MAX = 4096
PACKET_LIMIT = 32
ACK_SECONDS = 2
OUTER_CLEANUP_SECONDS = 22
OWNED_SCAN_PID_LIMIT = 4096
PR_SET_CHILD_SUBREAPER = 36
RUNTIME_SPECS = {
    "request": (406, "e81b38bbe6116bf1df2807fa968e12dccfd28fe8c3ad225c45f282b36cab6716",
                "request.bin"),
    "selected_inputs": (76, "6b8761a9d2094147f02b9fe2a4c709246905a04c5122d68f6b9951162e01317d",
                        "selected-inputs.json"),
    "fixture": (27448, "9ad70dd23d699e72ad805f59446aec371c4e80b955056b845af921b4ce51f725",
                "fixture"),
}
FIXTURE_SOURCE = Path("/work/cases/stdin-devnull/inputs/fixture")
U64_MAX = (1 << 64) - 1
U32_MAX = (1 << 32) - 1
I64_MIN, I64_MAX = -(1 << 63), (1 << 63) - 1
LONG_MAX = (1 << 63) - 1

def attach_secondary(primary, secondary):
    values = list(getattr(primary, "_owner_secondary_exceptions", []))
    values.append(secondary)
    primary._owner_secondary_exceptions = values

def exception_sequence(error):
    values, seen = [], set()
    def visit(current):
        if id(current) in seen:
            return
        seen.add(id(current))
        values.append(current)
        for secondary in getattr(current, "_owner_secondary_exceptions", []):
            visit(secondary)
    visit(error)
    return values

def chain_exceptions(values):
    unique, seen = [], set()
    for value in values:
        if id(value) not in seen:
            seen.add(id(value)); unique.append(value)
    for value in unique:
        value.__context__ = None
    for earlier, later in zip(unique, unique[1:]):
        earlier.__context__ = later
    return unique[0] if unique else None

COMMON_KEYS = {"schema_version", "nonce", "selector", "sequence", "kind",
    "phase", "monotonic_ns", "site", "object", "occurrence",
    "collector_pid", "collector_startticks", "source_sha256",
    "generated_sha256", "header_sha256", "elf_sha256"}
CREATE_KEYS = {"dirfd", "dir_stat", "fd", "target_stat", "acquisition_id",
               "return", "errno_authoritative", "errno"}
WRITE_BEFORE_KEYS = {"fd", "target_stat", "acquisition_id", "requested_bytes",
                     "return", "errno_authoritative", "errno"}
WRITE_AFTER_KEYS = WRITE_BEFORE_KEYS | {"actual_bytes"}
IO_KEYS = {"fd", "target_stat", "acquisition_id", "return",
           "errno_authoritative", "errno"}
BIND_KEYS = {"acquisition_id", "old_fd", "old_stat", "new_fd", "new_stat"}
OBSERVATION_KEYS = {
    "SETUP": {"setup_words", "cwd_stat", "stdin_stat", "stdout_pipe_stat", "stderr_pipe_stat",
        "executable_backing", "executable_seals", "leader_pid", "leader_startticks"},
    "REAP": {"pid", "startticks", "raw_wait_status"},
    "EOF": {"closed_fd"},
    "CLEANUP_READY": {"waitid_return", "waitid_errno", "leader_reaped",
        "stdout_eof", "stderr_eof", "setup_eof"},
    "CLEANUP_FINAL": {"cleanup_start_ns", "cleanup_deadline_ns",
        "cleanup_finished_ns", "cleanup_complete", "group_pinned",
        "owned_count", "owned_records_omitted", "first_failure",
        "first_failure_errno"}}

def pair(site, object_name, occurrence=1):
    return [("BEFORE", site, object_name, occurrence),
            ("AFTER", site, object_name, occurrence)]

def fixed_schedule(selector):
    e = pair("events-create", "events.jsonl")
    eb = [("BIND", "events-create", "events.jsonl", 1)]
    w1 = pair("request-write", "request.bin", 1)
    w2 = pair("request-write", "request.bin", 2)
    a = pair("request-sync", "request.bin")
    r = pair("report-create", "report.json")
    rb = [("BIND", "report-create", "report.json", 1)]
    f = pair("report-flush", "report.json")
    s = pair("report-sync", "report.json")
    schedules = {0: e + eb + w1 + ["O"] + a + r + rb + f + s,
        1: e + r + rb + f + s,
        2: e + eb + w1 + w2 + a + r + rb + f + s,
        3: e + eb + w1 + ["O"] + a + r + rb + f + s,
        4: e + eb + w1 + ["O"] + a + r,
        5: e + eb + w1 + ["O"] + a + r + rb + f + s,
        6: e + eb + w1 + w2 + a + r + rb + f + s}
    return schedules[selector]

def schedules(selector):
    base = fixed_schedule(selector)
    if "O" not in base:
        return [[("READY", "startup", "collector", 0)] + base]
    index = base.index("O")
    observations = [("REAP", "reap", "leader", 1),
        ("EOF", "pump", "stdout", 1), ("EOF", "pump", "stderr", 2),
        ("EOF", "pump", "setup", 3)]
    tail = [("CLEANUP_READY", "cleanup", "owned-tree", 1),
            ("CLEANUP_FINAL", "cleanup", "owned-tree", 1),
            ("SETUP", "setup", "collector", 1)]
    return [[("READY", "startup", "collector", 0)] + base[:index] +
            list(order) + tail + base[index + 1:]
            for order in itertools.permutations(observations)]

def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError("nonfinite")))

def process_identity(pid):
    raw = Path("/proc/%d/stat" % pid).read_bytes()
    close = raw.rfind(b")")
    if close < 0:
        raise ValueError("proc stat")
    prefix = raw[:close + 1]
    open_paren = prefix.find(b"(")
    fields = raw[close + 2:].split()
    if open_paren < 1 or len(fields) < 20:
        raise ValueError("proc stat")
    return {"pid": int(prefix[:open_paren - 1]), "ppid": int(fields[1]),
            "startticks": int(fields[19])}

def complete_write(fd, raw):
    view = memoryview(raw)
    while view:
        try:
            count = os.write(fd, view)
        except InterruptedError:
            continue
        if count <= 0:
            raise OSError("short durable write")
        view = view[count:]

def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    primary = None
    try:
        os.fsync(fd)
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

def stable_bytes(path, limit=1 << 26):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    primary = None
    result = None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("bounded regular evidence required")
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                raise OSError("short evidence read")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != \
           (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise OSError("evidence changed during read")
        result = b"".join(chunks)
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
    return result

def file_record(path, shown_path):
    path = Path(path)
    try:
        raw = stable_bytes(path)
    except FileNotFoundError:
        return {"path": str(shown_path), "present": False,
                "size": None, "sha256": None}
    return {"path": str(shown_path), "present": True, "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}

def durable_file(path, raw, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, mode)
    primary = None
    try:
        complete_write(fd, raw)
        os.fsync(fd)
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

def effective_environment(nonce, hashes):
    return {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
            "M02_SF_NONCE": nonce,
            "M02_SF_SOURCE_SHA256": hashes["source_sha256"],
            "M02_SF_GENERATED_SHA256": hashes["generated_sha256"],
            "M02_SF_HEADER_SHA256": hashes["header_sha256"],
            "M02_SF_ELF_SHA256": hashes["elf_sha256"]}

def bind_inputs(paths, hashes):
    limits = {"source": 1 << 20, "generated_source": 1 << 20,
              "header": 1 << 20, "elf": 16 << 20}
    hash_keys = {"source": "source_sha256",
                 "generated_source": "generated_sha256",
                 "header": "header_sha256", "elf": "elf_sha256"}
    records = {}
    for name in ("source", "generated_source", "header", "elf"):
        path = Path(paths[name])
        if not path.is_absolute() or path.resolve() != path:
            raise ValueError("canonical input path")
        raw = stable_bytes(path, limits[name])
        digest = hashlib.sha256(raw).hexdigest()
        if digest != hashes[hash_keys[name]]:
            raise ValueError("input hash " + name)
        records[name] = {"path": str(path), "present": True,
                         "size": len(raw), "sha256": digest}
    return records

def bind_runtime_sources(paths):
    bound = {}
    for name in ("request", "selected_inputs", "fixture"):
        path = Path(paths[name])
        if not path.is_absolute() or path.resolve() != path:
            raise ValueError("canonical runtime input " + name)
        if name == "fixture" and path != FIXTURE_SOURCE:
            raise ValueError("fixture source path")
        size, digest, filename = RUNTIME_SPECS[name]
        raw = stable_bytes(path, size)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("runtime input " + name)
        bound[name] = {"source_path": str(path), "raw": raw,
                       "filename": filename, "size": size, "sha256": digest}
    return bound

def retain_runtime_inputs(root, bound):
    retained = root / "retained-inputs"
    retained.mkdir(mode=0o700)
    records = {}
    for name in ("request", "selected_inputs", "fixture"):
        source = bound[name]
        destination = (retained / source["filename"]).resolve()
        durable_file(destination, source["raw"])
        if stable_bytes(destination, source["size"]) != source["raw"]:
            raise OSError("retained runtime input mismatch")
        records[name] = {"source_path": source["source_path"],
            "destination_path": str(destination), "size": source["size"],
            "sha256": source["sha256"]}
    fsync_directory(retained)
    fsync_directory(root)
    return records

def validate_executable(argv, inputs):
    if not argv or Path(argv[0]).resolve() != Path(argv[0]) or \
       argv[0] != inputs["elf"]["path"]:
        raise ValueError("executed ELF path")

def canonical_fresh_root(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("canonical witness root")
    parent = path.parent.resolve(strict=True)
    canonical = parent / path.name
    if path != canonical or path.exists() or path.is_symlink():
        raise FileExistsError("witness root exists") if path.exists() or \
            path.is_symlink() else ValueError("canonical witness root")
    os.mkdir(canonical, mode=0o700)
    fsync_directory(parent)
    return canonical

class DurableJournal:
    def __init__(self, root, create_root=False):
        self.root = Path(root)
        if create_root:
            self.root = canonical_fresh_root(self.root)
        if not self.root.is_dir() or self.root.is_symlink() or \
           self.root.resolve() != self.root:
            raise ValueError("canonical witness root")
        self.fd = -1
        try:
            self.fd = os.open(self.root / "witness.jsonl",
                              os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                              0o600)
            fsync_directory(self.root.parent)
        except Exception as primary:
            try:
                self.close()
            except Exception as close_error:
                attach_secondary(primary, close_error)
            chain_exceptions(exception_sequence(primary))
            raise primary from None

    def append(self, packet, receipt_ns):
        record = json.dumps({"packet": packet, "receipt_monotonic_ns": receipt_ns},
                            sort_keys=True, separators=(",", ":")).encode() + b"\n"
        complete_write(self.fd, record)
        os.fsync(self.fd)
        fsync_directory(self.root)

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

class OwnerErrorJournal:
    STAGES = {"receive", "pre-ack", "journal-packet", "release", "ack",
        "cleanup", "capture-fsync", "artifact-read", "owner-result-write",
        "journal-result", "directory-fsync"}

    def __init__(self, root):
        self.root = Path(root)
        self.fd = -1
        self.records = []
        self.next_ordinal = 0
        self.last_monotonic_ns = 0
        self.poisoned = False
        try:
            self.fd = os.open(self.root / "owner-errors.jsonl",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
            os.fsync(self.fd)
            fsync_directory(self.root)
        except Exception as primary:
            try:
                self.close()
            except Exception as close_error:
                attach_secondary(primary, close_error)
            chain_exceptions(exception_sequence(primary))
            raise primary from None

    def append(self, error, stage, packet=None):
        if stage not in self.STAGES:
            raise ValueError("owner error stage")
        if self.poisoned or self.fd < 0:
            raise OSError("owner error journal unavailable")
        name = type(error).__name__
        message = str(error) or "<empty-%s>" % name
        canonical = None if packet is None else json.dumps(packet, sort_keys=True,
            separators=(",", ":")).encode()
        sequence = packet.get("sequence") if type(packet) is dict and \
            type(packet.get("sequence")) is int and packet["sequence"] >= 0 else None
        ordinal = self.next_ordinal
        self.next_ordinal += 1
        now = time.monotonic_ns()
        if now <= self.last_monotonic_ns:
            now = self.last_monotonic_ns + 1
        self.last_monotonic_ns = now
        record = {"schema_version": 2, "kind": "OWNER_ERROR",
            "ordinal": ordinal, "primary": ordinal == 0,
            "stage": stage, "type": name, "message": message,
            "monotonic_ns": now, "packet_sequence": sequence,
            "packet_sha256": hashlib.sha256(canonical).hexdigest()
                if canonical is not None else None}
        raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        try:
            complete_write(self.fd, raw)
            os.fsync(self.fd)
            fsync_directory(self.root)
        except Exception:
            self.poisoned = True
            raise
        self.records.append(record)
        return record

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

class FailureLedger:
    """Owns exception order independently of the fallible durable journal."""
    def __init__(self, journal):
        self.journal = journal
        self.exceptions = []

    def record(self, error, stage, packet=None):
        observed = exception_sequence(error)
        self.exceptions.extend(observed)
        first_record = None
        for index, observed_error in enumerate(observed):
            if self.journal.poisoned or self.journal.fd < 0:
                continue
            try:
                record = self.journal.append(observed_error, stage,
                                             packet if index == 0 else None)
                if index == 0:
                    first_record = record
            except Exception as journal_error:
                self.exceptions.extend(exception_sequence(journal_error))
        return first_record

    def raise_first(self):
        if not self.exceptions:
            return
        primary = chain_exceptions(self.exceptions)
        raise primary

    @property
    def failed(self):
        return bool(self.exceptions)

def close_owned(close, ledger, stage):
    try:
        close()
    except Exception as error:
        ledger.record(error, stage)

def close_fd_owned(fd, ledger, stage):
    if fd >= 0:
        close_owned(lambda: os.close(fd), ledger, stage)

def result_serialization_cutoff(error_journal):
    cutoff = max(time.monotonic_ns(), error_journal.last_monotonic_ns)
    error_journal.last_monotonic_ns = cutoff
    return cutoff

def publish_owner_result(root, result_raw, result, journal, ledger):
    persisted = terminal = False
    try:
        durable_file(Path(root) / "owner-result.json", result_raw)
        persisted = True
    except Exception as error:
        ledger.record(error, "owner-result-write")
    if persisted:
        try:
            fsync_directory(root)
        except Exception as error:
            persisted = False
            ledger.record(error, "directory-fsync")
    if persisted:
        try:
            journal.append(result, time.monotonic_ns())
            terminal = True
        except Exception as error:
            ledger.record(error, "journal-result")
    return persisted, terminal

def subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))

def observe_identity(pid, phase, expected=None, parent_pid=None):
    now = time.monotonic_ns()
    try:
        current = process_identity(pid)
    except FileNotFoundError:
        return {"kind": "identity", "phase": phase, "observation": "missing",
                "pid": pid, "ppid": None, "startticks": None,
                "matched": False, "monotonic_ns": now}
    except (OSError, ValueError):
        return {"kind": "identity", "phase": phase, "observation": "error",
                "pid": pid, "ppid": None, "startticks": None,
                "matched": False, "monotonic_ns": now}
    valid = all(type(current.get(key)) is int and current[key] > 0
                for key in ("pid", "ppid", "startticks"))
    if not valid or current["pid"] != pid:
        return {"kind": "identity", "phase": phase, "observation": "error",
                "pid": pid, "ppid": None, "startticks": None,
                "matched": False, "monotonic_ns": now}
    matched = (expected is None or current["startticks"] == expected["startticks"]) and \
        (parent_pid is None or current["ppid"] == parent_pid)
    return {"kind": "identity", "phase": phase, "observation": "observed",
            "pid": current["pid"], "ppid": current["ppid"],
            "startticks": current["startticks"], "matched": matched,
            "monotonic_ns": now}

def matching_identity(pid, expected, parent_pid):
    return observe_identity(pid, "match", expected, parent_pid)["matched"]

def wait_direct(pid, deadline_ns, startticks=None, direct=True):
    while time.monotonic_ns() < deadline_ns:
        try:
            actual, raw = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            # Missing exclusive wait authority is not a timeout observation.
            raise
        if actual == pid:
            return {"kind": "wait", "pid": pid, "startticks": startticks,
                    "raw_wait_status": raw, "direct": direct,
                    "monotonic_ns": time.monotonic_ns()}
        time.sleep(0.01)
    return None

def owned_scan(owner_pid, exclude, phase):
    identities, reads, mismatches = [], [], []
    candidates = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) in exclude:
            continue
        candidates += 1
        if candidates > OWNED_SCAN_PID_LIMIT:
            raise OverflowError("owned scan process bound")
        first = observe_identity(int(entry.name), phase + "-1",
                                 parent_pid=owner_pid)
        if not first["matched"]:
            continue
        expected = {"startticks": first["startticks"]}
        second = observe_identity(int(entry.name), phase + "-2",
                                  expected, owner_pid)
        reads.extend((first, second))
        if second["matched"]:
            identities.append({"pid": second["pid"], "ppid": second["ppid"],
                               "startticks": second["startticks"]})
        else:
            mismatches.append(second)
    reads.append({"kind": "owned-scan", "monotonic_ns": time.monotonic_ns(),
                  "pids": identities})
    return identities, reads, mismatches

def bounded_cleanup(pid, identity, owner_pid, trigger_kind, trigger_ns,
                    on_error=None, session=None):
    now_ns = time.monotonic_ns()
    default_deadline_ns = trigger_ns + OUTER_CLEANUP_SECONDS * 1000000000
    if session is None:
        session = {"events": [], "adopted_reaps": [], "unresolved": [],
                   "waited": None, "evidence_invalidated": False,
                   "direct_authority": True, "terminal_empty": False,
                   "cleanup_start_ns": now_ns, "cleanup_deadline_ns": default_deadline_ns,
                   "consecutive_empty": 0, "scan_index": 0, "known_adopted": {}}
    start_ns = session.setdefault("cleanup_start_ns", now_ns)
    deadline_ns = session.setdefault("cleanup_deadline_ns", default_deadline_ns)
    events = session["events"]
    adopted_reaps = session["adopted_reaps"]
    unresolved = session["unresolved"]
    # These locals are deliberately initialized before any fallible wait or
    # scan.  Cleanup errors must not erase the retirement state already earned.
    waited = session.get("waited")
    evidence_invalidated = session.get("evidence_invalidated", False)
    direct_wait_fault = False
    direct_authority = session.get("direct_authority", True)
    terminal_empty = session.get("terminal_empty", False)
    ticks = identity.get("startticks") if identity else None
    direct_deadline_ns = session.setdefault("direct_deadline_ns",
                                            min(deadline_ns, start_ns + 16000000000))
    had_waited = waited is not None
    try:
        if not had_waited and direct_authority:
            waited = wait_direct(pid, direct_deadline_ns, ticks)
            session["waited"] = waited
    except ChildProcessError as error:
        direct_wait_fault = True
        if on_error is not None:
            on_error(error, "cleanup")
        # ECHILD proves that this owner no longer has exclusive wait
        # authority.  It does not prove a reap and can never authorize a
        # later signal to the numeric PID.
        direct_authority = False
        session["direct_authority"] = False
        missing = observe_identity(pid, "term-identity-1", identity, owner_pid)
        events.append(missing)
        unresolved.append(missing)
    except Exception as error:
        direct_wait_fault = True
        evidence_invalidated = True
        session["evidence_invalidated"] = True
        direct_authority = False
        session["direct_authority"] = False
        if on_error is not None:
            on_error(error, "cleanup")
    if waited:
        if not had_waited:
            events.append(waited)
    else:
        if not direct_wait_fault:
            unresolved.append({"kind": "wait-timeout", "stage": "direct",
                "pid": pid, "startticks": ticks,
                "monotonic_ns": time.monotonic_ns(),
                "deadline_ns": direct_deadline_ns})
        for phase, sig, wait_ns in (("term", signal.SIGTERM, 1000000000),
                                    ("kill", signal.SIGKILL, 5000000000)):
            if not direct_authority:
                break
            first = observe_identity(pid, phase + "-identity-1", identity, owner_pid)
            second = observe_identity(pid, phase + "-identity-2", identity, owner_pid)
            events.extend((first, second))
            same_birth = first["startticks"] is not None and \
                first["startticks"] == second["startticks"]
            if not first["matched"] or not second["matched"] or not same_birth:
                unresolved.append(second)
                break
            if time.monotonic_ns() >= deadline_ns:
                unresolved.append({"kind": "deadline", "stage": phase + "-pre-signal",
                    "monotonic_ns": time.monotonic_ns(), "deadline_ns": deadline_ns})
                break
            signal_ticks = second["startticks"]
            ticks = signal_ticks
            try:
                os.kill(pid, sig)
            except ProcessLookupError as error:
                unresolved.append({"kind": "signal-error", "stage": phase,
                    "pid": pid, "startticks": signal_ticks, "signal": int(sig),
                    "errno": error.errno or errno.ESRCH,
                    "monotonic_ns": time.monotonic_ns()})
                break
            except OSError as error:
                unresolved.append({"kind": "signal-error", "stage": phase,
                    "pid": pid, "startticks": signal_ticks, "signal": int(sig),
                    "errno": error.errno or errno.EIO,
                    "monotonic_ns": time.monotonic_ns()})
                break
            events.append({"kind": "signal", "pid": pid,
                           "startticks": signal_ticks, "signal": int(sig),
                           "monotonic_ns": time.monotonic_ns()})
            stage_deadline_ns = min(deadline_ns,
                                    time.monotonic_ns() + wait_ns)
            phase_wait_fault = False
            try:
                waited = wait_direct(pid, stage_deadline_ns, signal_ticks)
            except ChildProcessError:
                if on_error is not None:
                    on_error(ChildProcessError("cleanup direct ECHILD"),
                             "cleanup")
                direct_authority = False
                session["direct_authority"] = False
                break
            except Exception as error:
                phase_wait_fault = True
                evidence_invalidated = True
                session["evidence_invalidated"] = True
                direct_authority = False
                session["direct_authority"] = False
                if on_error is not None:
                    on_error(error, "cleanup")
                # Wait completion is uncertain.  Never signal this numeric PID
                # again, even after a later matching procfs observation.
                break
            if waited:
                events.append(waited)
                session["waited"] = waited
                break
            if not phase_wait_fault:
                unresolved.append({"kind": "wait-timeout", "stage": phase,
                    "pid": pid, "startticks": ticks,
                    "monotonic_ns": time.monotonic_ns(),
                    "deadline_ns": stage_deadline_ns})
    consecutive_empty = session.get("consecutive_empty", 0)
    scan_index = session.get("scan_index", 0)
    known_adopted = session.setdefault("known_adopted", {})
    while waited is not None and not terminal_empty and time.monotonic_ns() < deadline_ns and \
            scan_index < 2047:
        deadline_reached = False
        while True:
            now = time.monotonic_ns()
            if now >= deadline_ns:
                unresolved.append({"kind": "deadline", "stage": "owned-scan",
                    "monotonic_ns": now, "deadline_ns": deadline_ns})
                deadline_reached = True
                break
            try:
                child, raw = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                child = -1
                break
            except Exception as error:
                evidence_invalidated = True
                session["evidence_invalidated"] = True
                if on_error is not None:
                    on_error(error, "cleanup")
                break
            if child <= 0:
                break
            record = {"kind": "wait", "pid": child,
                      "startticks": known_adopted.pop(child, None),
                      "raw_wait_status": raw, "direct": False,
                      "monotonic_ns": time.monotonic_ns()}
            events.append(record); adopted_reaps.append(record)
            session["known_adopted"] = known_adopted
            consecutive_empty = 0
            session["consecutive_empty"] = consecutive_empty
        if deadline_reached:
            break
        scan_index += 1
        session["scan_index"] = scan_index
        try:
            adopted, scan_events, mismatches = owned_scan(
                owner_pid, {owner_pid, pid}, "owned-scan-%d" % scan_index)
        except Exception as error:
            evidence_invalidated = True
            session["evidence_invalidated"] = True
            if on_error is not None:
                on_error(error, "cleanup")
            time.sleep(0.01)
            continue
        events.extend(scan_events)
        unresolved.extend(mismatches)
        known_adopted.update({item["pid"]: item["startticks"] for item in adopted})
        session["known_adopted"] = known_adopted
        if not adopted:
            consecutive_empty += 1
            session["consecutive_empty"] = consecutive_empty
            if consecutive_empty < 2:
                time.sleep(0.01)
                continue
            try:
                child, raw = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                events.append({"kind": "echild", "monotonic_ns": time.monotonic_ns(),
                               "return": -1, "errno": errno.ECHILD})
                terminal_empty = True
                session["terminal_empty"] = True
                break
            except Exception as error:
                evidence_invalidated = True
                session["evidence_invalidated"] = True
                if on_error is not None:
                    on_error(error, "cleanup")
                time.sleep(0.01)
                continue
            if child > 0:
                record = {"kind": "wait", "pid": child,
                          "startticks": known_adopted.pop(child, None),
                          "raw_wait_status": raw, "direct": False,
                          "monotonic_ns": time.monotonic_ns()}
                events.append(record); adopted_reaps.append(record)
                session["known_adopted"] = known_adopted
                consecutive_empty = 0
                session["consecutive_empty"] = consecutive_empty
                continue
            time.sleep(0.01)
            continue
        consecutive_empty = 0
        session["consecutive_empty"] = consecutive_empty
        for adopted in adopted:
            unresolved.append({"kind": "owned", "phase": "owned-scan-%d" % scan_index,
                "pid": adopted["pid"], "ppid": adopted["ppid"],
                "startticks": adopted["startticks"],
                "monotonic_ns": time.monotonic_ns()})
            if time.monotonic_ns() >= deadline_ns:
                unresolved.append({"kind": "deadline", "stage": "owned-scan",
                    "monotonic_ns": time.monotonic_ns(), "deadline_ns": deadline_ns})
                break
            first = observe_identity(adopted["pid"],
                                     "owned-scan-%d-1" % scan_index,
                                     adopted, owner_pid)
            second = observe_identity(adopted["pid"],
                                      "owned-scan-%d-2" % scan_index,
                                      adopted, owner_pid)
            events.extend((first, second))
            if not first["matched"] or not second["matched"]:
                unresolved.append(second)
                continue
            if time.monotonic_ns() >= deadline_ns:
                unresolved.append({"kind": "deadline", "stage": "owned-scan",
                    "monotonic_ns": time.monotonic_ns(),
                    "deadline_ns": deadline_ns})
                break
            try:
                os.kill(adopted["pid"], signal.SIGKILL)
            except ProcessLookupError as error:
                unresolved.append({"kind": "signal-error", "stage": "kill",
                    "pid": adopted["pid"], "startticks": adopted["startticks"],
                    "signal": int(signal.SIGKILL),
                    "errno": error.errno or errno.ESRCH,
                    "monotonic_ns": time.monotonic_ns()})
                continue
            except OSError as error:
                unresolved.append({"kind": "signal-error", "stage": "kill",
                    "pid": adopted["pid"], "startticks": adopted["startticks"],
                    "signal": int(signal.SIGKILL), "errno": error.errno or errno.EIO,
                    "monotonic_ns": time.monotonic_ns()})
                continue
            events.append({"kind": "signal", "pid": adopted["pid"],
                           "startticks": adopted["startticks"],
                           "signal": int(signal.SIGKILL),
                           "monotonic_ns": time.monotonic_ns()})
    finished_ns = time.monotonic_ns()
    # The closed packet-8 unresolved union has no generic exception variant.
    # If an observation operation failed, keep retrying/draining to the real
    # cleanup bound and retain the exact deadline variant rather than inventing
    # an unsupported tag or a future timestamp.
    while evidence_invalidated and finished_ns < deadline_ns:
        time.sleep(min(0.01, (deadline_ns - finished_ns) / 1000000000))
        finished_ns = time.monotonic_ns()
    if evidence_invalidated and not any(item.get("kind") == "deadline" and
            item.get("stage") == "owned-scan" for item in unresolved):
        unresolved.append({"kind": "deadline", "stage": "owned-scan",
            "monotonic_ns": finished_ns, "deadline_ns": deadline_ns})
    if waited is None and finished_ns >= direct_deadline_ns and not any(
            item.get("kind") == "wait-timeout" and item.get("stage") == "direct"
            for item in unresolved):
        unresolved.append({"kind": "wait-timeout", "stage": "direct",
            "pid": pid, "startticks": ticks, "monotonic_ns": finished_ns,
            "deadline_ns": direct_deadline_ns})
    if waited is not None and not terminal_empty and finished_ns >= deadline_ns and \
       not any(item.get("kind") == "deadline" and
               item.get("stage") == "owned-scan" for item in unresolved):
        unresolved.append({"kind": "deadline", "stage": "owned-scan",
            "monotonic_ns": finished_ns, "deadline_ns": deadline_ns})
    complete = waited is not None and terminal_empty and not unresolved and \
        not evidence_invalidated and \
        finished_ns <= deadline_ns
    session.update(waited=waited, evidence_invalidated=evidence_invalidated,
                   direct_authority=direct_authority,
                   terminal_empty=terminal_empty,
                   cleanup_start_ns=start_ns, cleanup_deadline_ns=deadline_ns,
                   direct_deadline_ns=direct_deadline_ns,
                   consecutive_empty=consecutive_empty, scan_index=scan_index,
                   known_adopted=known_adopted)
    return {"complete": complete, "trigger_kind": trigger_kind,
            "trigger_ns": trigger_ns, "cleanup_start_ns": start_ns,
            "cleanup_deadline_ns": deadline_ns,
            "cleanup_finished_ns": finished_ns, "events": events,
            "adopted_reaps": adopted_reaps, "unresolved": unresolved}, waited

def receive(endpoint, deadline):
    poller = select.poll()
    poller.register(endpoint.fileno(), select.POLLIN | select.POLLHUP | select.POLLERR)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not poller.poll(max(1, int(remaining * 1000))):
            raise TimeoutError("witness packet timeout")
        try:
            raw = endpoint.recv(PACKET_MAX + 1, socket.MSG_DONTWAIT)
            break
        except (InterruptedError, BlockingIOError):
            continue
    if not raw:
        return None
    if len(raw) > PACKET_MAX:
        raise ValueError("oversized witness packet")
    return strict_json(raw)

def send_packet(endpoint, raw, deadline):
    poller = select.poll()
    poller.register(endpoint.fileno(), select.POLLOUT | select.POLLHUP | select.POLLERR)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not poller.poll(max(1, int(remaining * 1000))):
            raise TimeoutError("witness acknowledgement timeout")
        try:
            sent = endpoint.send(raw, socket.MSG_DONTWAIT)
        except InterruptedError:
            continue
        except BlockingIOError:
            continue
        if sent != len(raw):
            raise OSError("short witness acknowledgement")
        return

def validate_common(packet, nonce, selector, sequence, hashes):
    if not COMMON_KEYS <= set(packet):
        raise ValueError("witness fields")
    if type(packet["schema_version"]) is not int or type(packet["nonce"]) is not str or \
       type(packet["selector"]) is not int or type(packet["sequence"]) is not int or \
       type(packet["kind"]) is not str or packet["schema_version"] != 2 or packet["nonce"] != nonce or \
       packet["selector"] != selector or packet["sequence"] != sequence:
        raise ValueError("witness identity")
    if type(packet["monotonic_ns"]) is not int or packet["monotonic_ns"] <= 0:
        raise ValueError("witness time")
    if packet["phase"] not in ("pre-fork", "post-fork") or \
       type(packet["site"]) is not str or type(packet["object"]) is not str or \
       type(packet["occurrence"]) is not int or packet["occurrence"] < 0 or \
       type(packet["collector_pid"]) is not int or packet["collector_pid"] <= 0 or \
       type(packet["collector_startticks"]) is not int or \
       packet["collector_startticks"] <= 0:
        raise ValueError("witness common types")
    for key, value in hashes.items():
        if type(packet[key]) is not str or packet[key] != value:
            raise ValueError("witness hash")

def validate_stat(value):
    if type(value) is not dict or set(value) != {"dev", "ino", "mode", "size"} or \
       any(type(value[key]) is not int for key in value):
        raise ValueError("witness stat")
    if any(not 0 <= value[key] <= U64_MAX for key in ("dev", "ino", "mode")) or \
       not I64_MIN <= value["size"] <= I64_MAX:
        raise ValueError("witness stat range")

def expected_phase(selector, site, kind):
    if kind == "READY" or site in ("events-create", "request-write"):
        return "pre-fork"
    if kind in OBSERVATION_KEYS:
        return "post-fork"
    return "pre-fork" if selector in (1, 2, 6) else "post-fork"

def validate_packet_schema(packet, selector, executable_size=None):
    kind, site = packet["kind"], packet["site"]
    if kind == "READY":
        extras = set()
    elif kind in ("BEFORE", "AFTER") and site in ("events-create", "report-create"):
        extras = CREATE_KEYS
    elif kind == "BEFORE" and site == "request-write":
        extras = WRITE_BEFORE_KEYS
    elif kind == "AFTER" and site == "request-write":
        extras = WRITE_AFTER_KEYS
    elif kind in ("BEFORE", "AFTER") and site in (
            "request-sync", "report-flush", "report-sync"):
        extras = IO_KEYS
    elif kind == "BIND":
        extras = BIND_KEYS
    elif kind in OBSERVATION_KEYS:
        extras = OBSERVATION_KEYS[kind]
    else:
        raise ValueError("witness kind")
    if set(packet) != COMMON_KEYS | extras:
        raise ValueError("witness exact fields")
    for descriptor in ("dirfd", "fd", "old_fd", "new_fd", "closed_fd"):
        if descriptor in packet and packet[descriptor] is not None and \
                packet[descriptor] == WITNESS_FD:
            raise ValueError("witness transport descriptor")
    if (type(packet.get("dirfd")) is int and 0 <= packet["dirfd"] < 3) or \
       (kind == "BIND" and type(packet["new_fd"]) is int and
        0 <= packet["new_fd"] < 3) or \
       (kind == "EOF" and type(packet["closed_fd"]) is int and
        0 <= packet["closed_fd"] < 3) or \
       (site in ("request-write", "request-sync", "report-flush", "report-sync") and
        type(packet.get("fd")) is int and 0 <= packet["fd"] < 3):
        raise ValueError("witness high descriptor")
    if packet["phase"] != expected_phase(selector, site, kind):
        raise ValueError("witness phase")
    if kind == "BEFORE":
        if packet["return"] is not None or packet["errno_authoritative"] is not False or \
           packet["errno"] is not None:
            raise ValueError("witness before result")
    if kind == "AFTER":
        returned = packet["return"]
        if type(returned) is not int or \
           packet["errno_authoritative"] is not (returned < 0) or \
           (returned < 0 and (type(packet["errno"]) is not int or packet["errno"] <= 0)) or \
           (returned >= 0 and packet["errno"] is not None):
            raise ValueError("witness after result")
    for name in ("target_stat", "dir_stat", "old_stat", "new_stat"):
        if name in packet and packet[name] is not None:
            validate_stat(packet[name])
    if kind in ("BEFORE", "AFTER") and site in ("events-create", "report-create"):
        if type(packet["dirfd"]) is not int or packet["dirfd"] < 0 or \
                type(packet["dir_stat"]) is not dict:
            raise ValueError("witness create types")
        if not stat.S_ISDIR(packet["dir_stat"]["mode"]):
            raise ValueError("witness directory type")
        if kind == "BEFORE" and any(packet[name] is not None for name in (
                "fd", "target_stat", "acquisition_id")):
            raise ValueError("witness create before")
        if kind == "AFTER" and packet["return"] >= 0 and (
                type(packet["fd"]) is not int or packet["fd"] != packet["return"] or
                type(packet["target_stat"]) is not dict or
                type(packet["acquisition_id"]) is not int or
                packet["acquisition_id"] <= 0):
            raise ValueError("witness create after")
        if kind == "AFTER" and packet["return"] < 0 and any(
                packet[name] is not None for name in ("fd", "target_stat", "acquisition_id")):
            raise ValueError("witness create failure")
    if site == "request-write":
        if type(packet["fd"]) is not int or packet["fd"] < 0 or \
           type(packet["target_stat"]) is not dict or \
           type(packet["acquisition_id"]) is not int or packet["acquisition_id"] != 0 or \
           type(packet["requested_bytes"]) is not int or \
           packet["requested_bytes"] <= 0 or (kind == "AFTER" and
           (type(packet["actual_bytes"]) is not int or packet["actual_bytes"] < 0)):
            raise ValueError("witness write types")
    if site in ("request-sync", "report-flush", "report-sync") and (
            type(packet["fd"]) is not int or packet["fd"] < 0 or \
            type(packet["target_stat"]) is not dict or
            type(packet["acquisition_id"]) is not int or packet["acquisition_id"] < 0):
        raise ValueError("witness io types")
    if kind == "BIND" and (type(packet["acquisition_id"]) is not int or
            packet["acquisition_id"] <= 0 or type(packet["old_fd"]) is not int or
            packet["old_fd"] < 0 or type(packet["new_fd"]) is not int or
            packet["new_fd"] < 0 or type(packet["old_stat"]) is not dict or
            type(packet["new_stat"]) is not dict):
        raise ValueError("witness bind types")
    if kind == "CLEANUP_READY" and (type(packet["waitid_return"]) is not int or
            packet["waitid_return"] != -1 or
            type(packet["waitid_errno"]) is not int or
            packet["waitid_errno"] != errno.ECHILD or
            any(packet[name] is not True for name in
                ("leader_reaped", "stdout_eof", "stderr_eof", "setup_eof"))):
        raise ValueError("witness cleanup ready")
    if kind == "REAP" and (type(packet["pid"]) is not int or packet["pid"] <= 0 or
            type(packet["startticks"]) is not int or packet["startticks"] <= 0 or
            type(packet["raw_wait_status"]) is not int):
        raise ValueError("witness reap types")
    if kind == "EOF" and (type(packet["closed_fd"]) is not int or
                           packet["closed_fd"] < 0):
        raise ValueError("witness eof types")
    if kind == "CLEANUP_FINAL" and (any(type(packet[name]) is not int for name in (
            "cleanup_start_ns", "cleanup_deadline_ns", "cleanup_finished_ns",
            "owned_count", "owned_records_omitted", "first_failure_errno")) or
            any(type(packet[name]) is not bool for name in (
                "cleanup_complete", "group_pinned")) or
            type(packet["first_failure"]) is not str):
        raise ValueError("witness cleanup final types")
    if kind == "SETUP":
        if type(packet["setup_words"]) is not list or len(packet["setup_words"]) != 48 or \
           any(type(word) is not int or not 0 <= word <= (1 << 64) - 1 for word in packet["setup_words"]) or \
           type(packet["executable_seals"]) is not int or not 0 <= packet["executable_seals"] <= U32_MAX or \
           type(packet["leader_pid"]) is not int or not 0 < packet["leader_pid"] <= LONG_MAX or \
           type(packet["leader_startticks"]) is not int or not 0 < packet["leader_startticks"] <= U64_MAX:
            raise ValueError("witness setup types")
        for key in ("cwd_stat", "stdin_stat", "stdout_pipe_stat", "stderr_pipe_stat", "executable_backing"):
            validate_stat(packet[key])
        backing = packet["executable_backing"]
        if not stat.S_ISREG(backing["mode"]) or stat.S_IMODE(backing["mode"]) != 0o500 or \
                (executable_size is not None and
                 (type(executable_size) is not int or executable_size < 0 or
                  backing["size"] != executable_size)):
            raise ValueError("witness executable backing")

def validate_schedule_prefix(packets, selector):
    signatures = [(packet["kind"], packet["site"], packet["object"],
                   packet["occurrence"]) for packet in packets]
    if not any(candidate[:len(signatures)] == signatures for candidate in schedules(selector)):
        raise ValueError("witness schedule")

def validate_schedule_complete(packets, selector):
    signatures = [(packet["kind"], packet["site"], packet["object"],
                   packet["occurrence"]) for packet in packets]
    if signatures not in schedules(selector):
        raise ValueError("incomplete witness schedule")

class PacketState:
    def __init__(self, selector):
        self.selector = selector
        self.creates = {}
        self.attempt_dir = None
        self.positive_ids = set()
        # Descriptor numbers are process-local capabilities.  A successful
        # open owns its returned number until a BIND relocates that same
        # acquisition; the old number must then be retired immediately.
        self.live_fds = {}
        self.request_identity = None
        self.request_size = 0
        self.report_identity = None
        self.report_id = None
        self.report_prefix_size = None
        self.report_full_size = None

    def validate(self, packet):
        kind, site = packet["kind"], packet["site"]
        # Keep this guard here as well as in the wire-schema validator: tests
        # and callers may exercise PacketState directly.  ``bool`` is an
        # ``int`` subclass, but is never a valid descriptor/numeric ID.
        for name in ("dirfd", "fd", "old_fd", "new_fd", "acquisition_id",
                     "requested_bytes", "actual_bytes", "return", "errno"):
            if name in packet and packet[name] is not None and \
                    type(packet[name]) is not int:
                raise ValueError("packet numeric types")
        if self.attempt_dir is not None:
            for stat_name in ("target_stat", "old_stat", "new_stat"):
                value = packet.get(stat_name)
                if value is not None and stat.S_ISREG(value["mode"]) and \
                        (value["dev"], value["ino"]) == self.attempt_dir[1:3]:
                    raise ValueError("directory inode collision")
        if kind == "EOF":
            # Numeric reuse is legal only after retirement; reject the
            # persistent directory and every capability live at this point.
            if packet["closed_fd"] == (self.attempt_dir[0]
                                        if self.attempt_dir is not None else None) or \
                    packet["closed_fd"] in self.live_fds:
                raise ValueError("eof descriptor collision")
        elif kind == "BEFORE" and site in ("events-create", "report-create"):
            if packet["fd"] is not None or packet["target_stat"] is not None or \
               packet["acquisition_id"] is not None or \
               not stat.S_ISDIR(packet["dir_stat"]["mode"]):
                raise ValueError("create before")
            identity = (packet["dirfd"], packet["dir_stat"]["dev"],
                        packet["dir_stat"]["ino"], packet["dir_stat"]["mode"])
            if self.attempt_dir is None:
                self.attempt_dir = identity
            elif identity != self.attempt_dir:
                raise ValueError("create directory identity")
        elif kind == "AFTER" and site in ("events-create", "report-create"):
            if self.attempt_dir is None or \
               (packet["dirfd"], packet["dir_stat"]["dev"], packet["dir_stat"]["ino"],
                packet["dir_stat"]["mode"]) != self.attempt_dir:
                raise ValueError("create directory identity")
            failed = (site == "events-create" and self.selector == 1) or \
                     (site == "report-create" and self.selector == 4)
            if failed:
                if (packet["return"], packet["errno"], packet["fd"],
                    packet["target_stat"], packet["acquisition_id"]) != \
                   (-1, errno.ENOSPC, None, None, None):
                    raise ValueError("create failure")
            else:
                target = packet["target_stat"]
                if packet["fd"] == self.attempt_dir[0] or packet["fd"] in self.live_fds:
                    raise ValueError("descriptor collision")
                if packet["return"] < 0 or packet["fd"] != packet["return"] or \
                   type(packet["acquisition_id"]) is not int or \
                   packet["acquisition_id"] <= 0 or \
                   packet["acquisition_id"] in self.positive_ids or \
                   not stat.S_ISREG(target["mode"]) or \
                   target["mode"] & 0o170777 != 0o100600 or target["size"] != 0:
                    raise ValueError("create success")
                self.positive_ids.add(packet["acquisition_id"])
                self.creates[site] = packet
                self.live_fds[packet["fd"]] = (site, packet["acquisition_id"])
        elif kind == "BIND":
            create = self.creates.get(site)
            if (packet["old_fd"] >= 3 and packet["new_fd"] != packet["old_fd"]) or \
               (packet["old_fd"] < 3 and packet["new_fd"] < 3):
                raise ValueError("bind descriptor")
            if create is None or packet["acquisition_id"] != create["acquisition_id"] or \
               packet["old_fd"] != create["fd"] or \
               self.live_fds.get(packet["old_fd"]) != \
               (site, packet["acquisition_id"]) or \
               (packet["new_fd"] in self.live_fds and
                packet["new_fd"] != packet["old_fd"]) or \
               not stat.S_ISREG(packet["old_stat"]["mode"]) or \
               not stat.S_ISREG(packet["new_stat"]["mode"]):
                raise ValueError("bind acquisition")
            for key in ("dev", "ino", "mode", "size"):
                if packet["old_stat"][key] != packet["new_stat"][key] or \
                   packet["old_stat"][key] != create["target_stat"][key]:
                    raise ValueError("bind identity")
            if packet["new_fd"] == self.attempt_dir[0]:
                raise ValueError("directory descriptor collision")
            del self.live_fds[packet["old_fd"]]
            self.live_fds[packet["new_fd"]] = (site, packet["acquisition_id"])
            if site == "report-create":
                self.report_identity = (packet["new_fd"], packet["new_stat"]["dev"],
                    packet["new_stat"]["ino"], packet["new_stat"]["mode"])
                self.report_id = packet["acquisition_id"]
        elif site == "request-write":
            target = packet["target_stat"]
            identity = (packet["fd"], target["dev"], target["ino"], target["mode"])
            if self.attempt_dir is not None and packet["fd"] == self.attempt_dir[0]:
                raise ValueError("directory descriptor collision")
            occurrence = packet["occurrence"]
            injected = self.selector in (2, 6)
            requested = 406 if occurrence == 1 else 399
            before_size = 0 if occurrence == 1 else 7
            if type(packet["acquisition_id"]) is not int or \
               packet["acquisition_id"] != 0 or not stat.S_ISREG(target["mode"]) or \
               (self.request_identity is not None and identity != self.request_identity) or \
               packet["requested_bytes"] != requested:
                raise ValueError("request acquisition")
            owner = self.live_fds.get(packet["fd"])
            if owner is None:
                self.live_fds[packet["fd"]] = ("request-write", 0)
            elif owner != ("request-write", 0):
                raise ValueError("request descriptor collision")
            self.request_identity = identity
            if kind == "BEFORE" and target["size"] != before_size:
                raise ValueError("request before size")
            if kind == "AFTER":
                returned = 7 if injected and occurrence == 1 else \
                    -1 if occurrence == 2 else 406
                expected_size = 7 if injected else 406
                if packet["return"] != returned or \
                   packet["errno"] != (errno.ENOSPC if returned < 0 else None) or \
                   packet["actual_bytes"] != max(returned, 0) or \
                   target["size"] != expected_size:
                    raise ValueError("request write result")
                self.request_size = expected_size
        elif site == "request-sync":
            target = packet["target_stat"]
            identity = (packet["fd"], target["dev"], target["ino"], target["mode"])
            returned = -1 if self.selector in (3, 6) else 0
            if type(packet["acquisition_id"]) is not int or \
               packet["acquisition_id"] != 0 or identity != self.request_identity or \
               self.live_fds.get(packet["fd"]) != ("request-write", 0) or \
               not stat.S_ISREG(target["mode"]) or \
               target["size"] != self.request_size or (kind == "AFTER" and (
               packet["return"] != returned or
               packet["errno"] != (errno.EIO if returned < 0 else None))):
                raise ValueError("request sync result")
        elif site in ("report-flush", "report-sync"):
            target = packet["target_stat"]
            identity = (packet["fd"], target["dev"], target["ino"], target["mode"])
            if identity != self.report_identity or packet["acquisition_id"] != \
                    self.report_id or self.live_fds.get(packet["fd"]) != \
                    ("report-create", self.report_id) or \
                    not stat.S_ISREG(target["mode"]):
                raise ValueError("report acquisition")
            if site == "report-flush" and kind == "BEFORE":
                self.report_prefix_size = target["size"]
            elif site == "report-flush" and kind == "AFTER":
                if packet["return"] != 0 or packet["errno"] is not None or \
                   self.report_prefix_size is None or target["size"] < \
                        self.report_prefix_size:
                    raise ValueError("report flush result")
                self.report_full_size = target["size"]
            else:
                if self.report_full_size is None or target["size"] != \
                        self.report_full_size:
                    raise ValueError("report sync size")
                if kind == "AFTER":
                    returned = -1 if self.selector in (5, 6) else 0
                    if packet["return"] != returned or packet["errno"] != \
                            (errno.EIO if returned < 0 else None):
                        raise ValueError("report sync result")
        elif kind == "CLEANUP_READY":
            if (packet["waitid_return"], packet["waitid_errno"],
                packet["leader_reaped"], packet["stdout_eof"],
                packet["stderr_eof"], packet["setup_eof"]) != \
               (-1, errno.ECHILD, True, True, True, True):
                raise ValueError("collector cleanup ready")
        elif kind == "CLEANUP_FINAL":
            if packet["cleanup_complete"] is not True or \
               packet["group_pinned"] is not True or \
               not packet["cleanup_start_ns"] < packet["cleanup_finished_ns"] < \
                   packet["cleanup_deadline_ns"] or packet["owned_count"] != 0 or \
               packet["owned_records_omitted"] != 0 or \
               packet["first_failure"] != "none" or \
               packet["first_failure_errno"] != 0:
                raise ValueError("collector cleanup result")

def launch(witness_root, nonce, selector, hashes, input_paths, runtime_paths):
    owner_start_ns = time.monotonic_ns()
    if len(nonce) != 32 or any(char not in "0123456789abcdef" for char in nonce):
        raise ValueError("nonce")
    if selector not in range(7):
        raise ValueError("launch inputs")
    inputs = bind_inputs(input_paths, hashes)
    runtime_sources = bind_runtime_sources(runtime_paths)
    subreaper()
    owner_pid = os.getpid()
    owner_first = process_identity(owner_pid)
    owner_second = process_identity(owner_pid)
    if owner_first["pid"] != owner_pid or owner_first["startticks"] <= 0 or \
       owner_first != owner_second:
        raise RuntimeError("owner identity")
    owner_identity = {"pid": owner_pid, "startticks": owner_first["startticks"]}
    witness_root = canonical_fresh_root(witness_root)
    journal = DurableJournal(witness_root)
    try:
        error_journal = OwnerErrorJournal(witness_root)
    except Exception as primary:
        secondary = None
        try:
            journal.close()
        except Exception as close_error:
            secondary = close_error
        if secondary is not None:
            attach_secondary(primary, secondary)
        chain_exceptions(exception_sequence(primary))
        raise primary from None
    ledger = FailureLedger(error_journal)
    stdout_fd = stderr_fd = -1
    parent_endpoint = child_endpoint = None
    pid = None
    environment = effective_environment(nonce, hashes)
    try:
        runtime_inputs = retain_runtime_inputs(witness_root, runtime_sources)
        collection = (witness_root / "collection").resolve()
        if collection.exists():
            raise FileExistsError("collection exists")
        argv = [inputs["elf"]["path"], "--linux-sealed-infrastructure-v1",
            runtime_inputs["request"]["destination_path"],
            runtime_inputs["selected_inputs"]["destination_path"], str(collection)]
        validate_executable(argv, inputs)
        stdout_fd = os.open(witness_root / "stdout.bin",
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        stderr_fd = os.open(witness_root / "stderr.bin",
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        fsync_directory(witness_root)
        parent_endpoint, child_endpoint = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC)
        pid = os.fork()
    except Exception as error:
        ledger.record(error, "pre-ack")
        if child_endpoint is not None:
            endpoint, child_endpoint = child_endpoint, None
            close_owned(endpoint.close, ledger, "pre-ack")
        if parent_endpoint is not None:
            endpoint, parent_endpoint = parent_endpoint, None
            close_owned(endpoint.close, ledger, "pre-ack")
        fd, stderr_fd = stderr_fd, -1
        close_fd_owned(fd, ledger, "capture-fsync")
        fd, stdout_fd = stdout_fd, -1
        close_fd_owned(fd, ledger, "capture-fsync")
        close_owned(journal.close, ledger, "journal-result")
        try:
            error_journal.close()
        except Exception as close_error:
            ledger.exceptions.append(close_error)
        ledger.raise_first()
    identity, initial_identity = None, None
    packets, owner_failure = [], None
    if pid == 0:
        try:
            parent_endpoint.close()
            os.dup2(child_endpoint.fileno(), WITNESS_FD, inheritable=True)
            os.dup2(stdout_fd, 1, inheritable=True)
            os.dup2(stderr_fd, 2, inheritable=True)
            child_endpoint.close()
            os.close(stdout_fd); os.close(stderr_fd)
            os.execve(argv[0], argv, environment)
        finally:
            os._exit(127)
    trigger_ns = time.monotonic_ns()
    trigger_kind = "normal-eof"
    ready_deadline_ns = owner_start_ns + 10000000000
    release_send_start_ns = collection_deadline_ns = None
    first_postfork_receipt_ns = postfork_deadline_ns = None
    active_stage, current_packet = "receive", None
    cleanup = waited = result = None
    result_persisted = terminal_published = False
    cleanup_session = {"events": [], "adopted_reaps": [], "unresolved": [],
                       "waited": None, "evidence_invalidated": False,
                       "direct_authority": True, "terminal_empty": False}
    try:
        # The parent enters this protected region immediately after successful fork.
        endpoint, child_endpoint = child_endpoint, None
        close_owned(endpoint.close, ledger, "pre-ack")
        fd, stdout_fd = stdout_fd, -1
        close_fd_owned(fd, ledger, "capture-fsync")
        fd, stderr_fd = stderr_fd, -1
        close_fd_owned(fd, ledger, "capture-fsync")
        if not ledger.failed:
            initial_identity = observe_identity(pid, "initial", parent_pid=owner_pid)
            if initial_identity["matched"]:
                identity = {"pid": pid, "ppid": initial_identity["ppid"],
                            "startticks": initial_identity["startticks"]}
            else:
                raise RuntimeError("collector identity")
            sequence = 0
            packet_state = PacketState(selector)
            while len(packets) <= PACKET_LIMIT:
                active_deadline_ns = ready_deadline_ns if sequence == 0 else \
                    (postfork_deadline_ns or collection_deadline_ns)
                packet = receive(parent_endpoint, active_deadline_ns / 1000000000)
                receipt_ns = time.monotonic_ns()
                current_packet = packet
                if packet is None:
                    validate_schedule_complete(packets, selector)
                    trigger_ns = receipt_ns
                    break
                if len(packets) == PACKET_LIMIT:
                    raise ValueError("witness packet limit")
                active_stage = "pre-ack"
                validate_common(packet, nonce, selector, sequence, hashes)
                # SETUP executable backing describes the authenticated runtime
                # payload, not the collector ELF used to produce the packets.
                validate_packet_schema(packet, selector,
                    runtime_inputs["fixture"]["size"])
                validate_schedule_prefix(packets + [packet], selector)
                packet_state.validate(packet)
                if packet["collector_pid"] != pid or \
                   packet["collector_startticks"] != identity["startticks"]:
                    raise ValueError("collector witness identity")
                if packet["phase"] == "post-fork" and first_postfork_receipt_ns is None:
                    first_postfork_receipt_ns = receipt_ns
                    postfork_deadline_ns = min(collection_deadline_ns,
                        first_postfork_receipt_ns + 60000000000)
                active_stage = "journal-packet"
                journal.append(packet, receipt_ns)
                packets.append(packet)
                if sequence == 0:
                    if packet["kind"] != "READY" or not matching_identity(
                            pid, identity, owner_pid):
                        raise ValueError("ready identity")
                    active_stage = "release"
                    release_send_start_ns = time.monotonic_ns()
                    collection_deadline_ns = release_send_start_ns + 180000000000
                    send_packet(parent_endpoint, ("RELEASE %s\n" % nonce).encode(),
                                time.monotonic() + ACK_SECONDS)
                else:
                    active_stage = "ack"
                    send_packet(parent_endpoint,
                                ("ACK %s %d\n" % (nonce, sequence)).encode(),
                                time.monotonic() + ACK_SECONDS)
                sequence += 1
                active_stage, current_packet = "receive", None
    except Exception as error:
        ledger.record(error, active_stage, current_packet)
        trigger_kind = "owner-failure"
        trigger_ns = time.monotonic_ns()
    finally:
        if parent_endpoint is not None:
            endpoint, parent_endpoint = parent_endpoint, None
            close_owned(endpoint.close, ledger, "cleanup")
        if ledger.failed and trigger_kind != "owner-failure":
            trigger_kind = "owner-failure"
            trigger_ns = time.monotonic_ns()
        try:
            cleanup, waited = bounded_cleanup(pid, identity, owner_pid,
                trigger_kind, trigger_ns,
                on_error=lambda error, stage: ledger.record(error, stage),
                session=cleanup_session)
        except Exception as error:
            ledger.record(error, "cleanup")
            # Retry with the same caller-owned append-only state and fixed
            # deadline.  The helper records only packet-8 unresolved variants;
            # this exception remains in owner-errors.jsonl.
            recovery_deadline_ns = trigger_ns + OUTER_CLEANUP_SECONDS * 1000000000
            while time.monotonic_ns() < recovery_deadline_ns:
                try:
                    cleanup, waited = bounded_cleanup(
                        pid, identity, owner_pid, trigger_kind, trigger_ns,
                        on_error=lambda failure, stage: ledger.record(failure, stage),
                        session=cleanup_session)
                    break
                except Exception as recovery_error:
                    ledger.record(recovery_error, "cleanup")
                    time.sleep(0.01)
            else:
                finished_ns = time.monotonic_ns()
                if not any(item.get("kind") == "deadline" and
                           item.get("stage") == "owned-scan"
                           for item in cleanup_session["unresolved"]):
                    cleanup_session["unresolved"].append({
                        "kind": "deadline", "stage": "owned-scan",
                        "monotonic_ns": finished_ns,
                        "deadline_ns": recovery_deadline_ns})
                cleanup = {"complete": False, "trigger_kind": trigger_kind,
                    "trigger_ns": trigger_ns, "cleanup_start_ns": trigger_ns,
                    "cleanup_deadline_ns": recovery_deadline_ns,
                    "cleanup_finished_ns": finished_ns,
                    "events": cleanup_session["events"],
                    "adopted_reaps": cleanup_session["adopted_reaps"],
                    "unresolved": cleanup_session["unresolved"]}
        if cleanup is not None and not cleanup["complete"]:
            ledger.record(RuntimeError("incomplete collector cleanup"), "cleanup")
        for capture in (witness_root / "stdout.bin", witness_root / "stderr.bin"):
            try:
                fd = os.open(capture, os.O_RDONLY | os.O_CLOEXEC)
                close_error = None
                try:
                    os.fsync(fd)
                except Exception as error:
                    ledger.record(error, "capture-fsync")
                try:
                    os.close(fd)
                except Exception as error:
                    ledger.record(error, "capture-fsync")
            except Exception as error:
                ledger.record(error, "capture-fsync")
        try:
            fsync_directory(witness_root)
        except Exception as error:
            ledger.record(error, "directory-fsync")
        captures = artifacts = None
        try:
            captures = {
                "stdout": file_record(witness_root / "stdout.bin", "stdout.bin"),
                "stderr": file_record(witness_root / "stderr.bin", "stderr.bin")}
            artifacts = {name: file_record(collection / filename,
                collection / filename) for name, filename in
                (("events", "events.jsonl"), ("request", "request.bin"),
                 ("report", "report.json"))}
        except Exception as error:
            ledger.record(error, "artifact-read")
        result_raw = None
        if cleanup is not None and captures is not None and artifacts is not None and \
           not error_journal.poisoned:
            result_serialized_ns = result_serialization_cutoff(error_journal)
            frozen_errors = list(error_journal.records)
            result = {"schema_version": 2, "kind": "OWNER_RESULT",
                  "nonce": nonce, "selector": selector, "argv": list(argv),
                  "owner": owner_identity,
                  "environment": environment,
                  "collector": {"pid": pid,
                      "identity_observed": identity is not None,
                      "ppid": identity["ppid"] if identity else None,
                      "startticks": identity["startticks"] if identity else None,
                      "reaped": waited is not None,
                      "raw_wait_status": waited["raw_wait_status"] if waited else None},
                  "packet_count": len(packets),
                  "hashes": {key: hashes[key] for key in
                      ("source_sha256", "generated_sha256", "header_sha256", "elf_sha256")},
                  "inputs": inputs,
                  "runtime_inputs": runtime_inputs,
                  "captures": captures, "artifacts": artifacts,
                  "owner_failure": frozen_errors[0] if frozen_errors else None,
                  "secondary_failures": frozen_errors[1:],
                  "result_serialized_ns": result_serialized_ns,
                  "cleanup": cleanup,
                  "deadlines": {"owner_start_ns": owner_start_ns,
                      "ready_deadline_ns": ready_deadline_ns,
                      "release_send_start_ns": release_send_start_ns,
                      "collection_deadline_ns": collection_deadline_ns,
                      "first_postfork_receipt_ns": first_postfork_receipt_ns,
                      "postfork_deadline_ns": postfork_deadline_ns,
                      "cleanup_trigger_ns": trigger_ns,
                      "cleanup_deadline_ns": trigger_ns + 22000000000},
                  "backend_enabled": False, "application_acceptance": False}
            try:
                result_raw = (json.dumps(result, sort_keys=True,
                              separators=(",", ":")) + "\n").encode()
            except Exception as error:
                ledger.record(error, "owner-result-write")
        if result_raw is not None:
            result_persisted, terminal_published = publish_owner_result(
                witness_root, result_raw, result, journal, ledger)
        close_owned(journal.close, ledger, "journal-result")
        try:
            error_journal.close()
        except Exception as close_error:
            ledger.exceptions.append(close_error)
        if cleanup is None or not cleanup["complete"] or not result_persisted or \
           not terminal_published:
            if not ledger.failed:
                ledger.exceptions.append(RuntimeError("owner publication incomplete"))
        ledger.raise_first()
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--witness-root", type=Path, required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--selector", type=int, choices=range(7), required=True)
    parser.add_argument("--hashes", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--generated-source", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--selected-inputs", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    try:
        hashes = strict_json(args.hashes.read_bytes())
        input_paths = {"source": args.source,
                       "generated_source": args.generated_source,
                       "header": args.header, "elf": args.elf}
        runtime_paths = {"request": args.request,
                         "selected_inputs": args.selected_inputs,
                         "fixture": args.fixture}
        result = launch(args.witness_root, args.nonce, args.selector,
                        hashes, input_paths, runtime_paths)
    except Exception as error:
        name = type(error).__name__
        message = str(error) or "<empty-%s>" % name
        print("owner infrastructure failure: %s: %s" % (name, message),
              file=sys.stderr)
        return 125
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
