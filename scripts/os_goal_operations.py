#!/usr/bin/env python3
"""Bounded future HOST operations owned by the existing campaign compositor.

This is an execution API, not an admission issuer. ``OperationRunner`` requires a
trusted, read-only same-Root ``admission_provider``. The provider is called with
the parsed OperationSpec and keyword arguments ``phase``, ``active_charges`` and
``deadline_mono_ns``. It must derive fresh account/source/permission/ownership
evidence from the original owners, fail on every applicable hold, and return a
FreshAdmission bound to this exact spec and phase. Saved JSON, source-work GO,
status output and supplied booleans cannot stand in for that callback.

The journal's short global transaction lock serializes accounting/reservations;
per-operation locks retain the original live runner. Restart reconciliation only
marks abandoned bookkeeping HELD. It never starts, signals, replays or expires an
operation. Native and legacy held operations are outside this module's custody.
Functional McKernel OS/apps and Rust/allowed assembly only; no security testing.
"""

import argparse
import ctypes
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import resource
import select
import signal
import stat
import subprocess
import sys
import threading
import time
from uuid import uuid4

from os_goal_resources import (check_payload_admission, MAX_ADMISSION_AGE_NS,
                               GIB, HOST_MEMORY_GIB, HOST_MAX_JOBS, HOST_CPUS,
                               NON_HOST_RESERVATION_GIB)
from os_goal_progress import load_ledger, validate_ledger, condition_sha256


SCHEMA = "mckernel-host-operation-v1"
GATES = frozenset({"account", "source", "permission", "ownership"})
RESOURCE_FIELDS = frozenset({"CPU", "planning_bytes", "jobs", "host_floor_bytes",
                             "scratch_floor_bytes", "max_age_ns"})
OPTIONAL_RESOURCE_FIELDS = frozenset({"host_memory_ceiling_bytes", "host_cpu_affinity", "host_max_jobs",
                                     "work_memory_ceiling_bytes"})
FIELDS = frozenset({"schema_version", "operation_id", "original_id", "owner_id",
                    "scope", "inputs", "argv", "environment", "ulimits", "cwd",
                    "resources", "execution_timeout_s", "cleanup_timeout_s",
                    "owned_process_group", "expected_exit_codes"})
LIMIT_NAMES = {name[7:].lower(): getattr(resource, name) for name in dir(resource)
               if name.startswith("RLIMIT_") and name != "RLIMIT_NLIMITS"}
# Original live contexts survive a returned HELD result. A new Runner cannot
# adopt them; durable pending_worker blocks it rather than inferring thread death.
_RETAINED_CONTEXTS = {}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value, name):
    _require(isinstance(value, str) and bool(value) and "\0" not in value,
             name + " must be a nonempty string without NUL")
    return value


def _integer(value, name, minimum=0):
    _require(type(value) is int and value >= minimum, name + " must be an integer >= " + str(minimum))
    return value


def _duration(value, name):
    _require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= 86400,
             name + " must be finite, positive and at most one day")
    return value


def _sha(value):
    _require(isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value), "Exact lowercase SHA256 required")
    return value


def _path(value, name):
    _text(value, name)
    _require(Path(value).is_absolute(), name + " must be absolute")
    return value


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=_unique,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def environment_map(rows):
    """Docker Config.Env semantics: exact unique names/values; order is immaterial."""
    _require(isinstance(rows, list), "environment must be an explicit list")
    result = {}
    for row in rows:
        _require(isinstance(row, str) and "=" in row and "\0" not in row,
                 "Malformed environment row")
        key, value = row.split("=", 1)
        _require(bool(re.fullmatch("[A-Za-z_][A-Za-z0-9_]*", key)) and key not in result,
                 "Malformed or duplicate environment name")
        result[key] = value
    return result


def ulimit_map(rows):
    """Docker Ulimits semantics: unique exact Name/Soft/Hard rows keyed by Name."""
    _require(isinstance(rows, list), "ulimits must be an explicit list")
    result = {}
    for row in rows:
        _require(isinstance(row, dict) and set(row) == {"Name", "Soft", "Hard"}, "Malformed ulimit row")
        name = row["Name"]
        _require(isinstance(name, str) and name in LIMIT_NAMES and name not in result,
                 "Unknown or duplicate ulimit Name")
        soft, hard = (_integer(row[key], "ulimit " + key) for key in ("Soft", "Hard"))
        _require(soft <= hard, "ulimit Soft exceeds Hard")
        result[name] = {"Soft": soft, "Hard": hard}
    return result


def profiles_match(expected_environment, actual_environment, expected_ulimits, actual_ulimits):
    return (environment_map(expected_environment) == environment_map(actual_environment)
            and ulimit_map(expected_ulimits) == ulimit_map(actual_ulimits))


@dataclass(frozen=True)
class OperationSpec:
    """Validated immutable-by-value v1 input, with semantic Env/Ulimit digest."""
    encoded: bytes
    digest: str

    @property
    def data(self):
        return json.loads(self.encoded)

    @property
    def operation_id(self):
        return self.data["operation_id"]

    @classmethod
    def parse(cls, value):
        # All structural validation is pure, before mkdir, capture or reservation.
        _require(isinstance(value, dict) and FIELDS <= set(value)
                 and set(value) <= FIELDS | {"closure_target"}, "Missing/extra operation fields")
        _require(type(value["schema_version"]) is int and value["schema_version"] == 1,
                 "Unsupported operation schema_version")
        _require(value["scope"] == "HOST", "Only future HOST operations are supported")
        for key in ("operation_id", "original_id", "owner_id"):
            _text(value[key], key)
        _require(bool(re.fullmatch("[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value["operation_id"])),
                 "operation_id must be a safe original identifier")
        _path(value["cwd"], "cwd")
        argv = value["argv"]
        _require(isinstance(argv, list) and bool(argv), "Explicit ordered argv is required")
        for arg in argv:
            _require(isinstance(arg, str) and "\0" not in arg, "Malformed argv")
        _path(argv[0], "argv executable")
        inputs = value["inputs"]
        _require(isinstance(inputs, list) and bool(inputs), "Exact input digests are required")
        paths = set()
        for row in inputs:
            _require(isinstance(row, dict) and set(row) == {"path", "sha256"}, "Malformed exact input")
            _path(row["path"], "input path")
            _sha(row["sha256"])
            _require(row["path"] not in paths, "Duplicate input path")
            paths.add(row["path"])
        _require(argv[0] in paths, "argv executable must have an exact input digest")
        environment_map(value["environment"])
        ulimit_map(value["ulimits"])
        resources = value["resources"]
        _require(isinstance(resources, dict) and RESOURCE_FIELDS <= set(resources)
                 and set(resources) <= RESOURCE_FIELDS | OPTIONAL_RESOURCE_FIELDS, "Complete resource request required")
        for key in set(resources) - {"CPU", "host_cpu_affinity"}:
            _integer(resources[key], key, 1)
        memory_ceiling = resources.get("host_memory_ceiling_bytes", HOST_MEMORY_GIB * GIB)
        job_limit = resources.get("host_max_jobs", HOST_MAX_JOBS)
        _require(resources["jobs"] <= job_limit and resources["planning_bytes"] <= memory_ceiling,
                 "Requested HOST jobs/memory exceed selected aggregate ceilings")
        if "work_memory_ceiling_bytes" in resources:
            _require("host_memory_ceiling_bytes" in resources
                     and memory_ceiling + NON_HOST_RESERVATION_GIB * GIB <= resources["work_memory_ceiling_bytes"],
                     "Explicit HOST ceiling plus preserved non-HOST reservations must fit shared work pool")
        selected_cpus = resources.get("host_cpu_affinity", sorted(HOST_CPUS))
        _require(isinstance(selected_cpus, list) and bool(selected_cpus)
                 and all(type(cpu) is int and cpu >= 0 for cpu in selected_cpus)
                 and len(set(selected_cpus)) == len(selected_cpus), "Distinct selected HOST CPUs required")
        cpus = resources["CPU"]
        _require(isinstance(cpus, list) and bool(cpus) and all(type(cpu) is int and cpu >= 0 for cpu in cpus)
                 and len(set(cpus)) == len(cpus) and set(cpus) <= set(selected_cpus), "Distinct selected HOST CPUs required")
        _require(resources["max_age_ns"] <= MAX_ADMISSION_AGE_NS, "Admission freshness exceeds 25s")
        _require(resources["host_floor_bytes"] >= 16 * 1024 ** 3
                 and resources["scratch_floor_bytes"] >= 12 * 1024 ** 3, "Resource floors cannot be lowered")
        _duration(value["execution_timeout_s"], "execution_timeout_s")
        _duration(value["cleanup_timeout_s"], "cleanup_timeout_s")
        _require(type(value["owned_process_group"]) is bool, "Explicit process-group ownership is required")
        exits = value["expected_exit_codes"]
        _require(isinstance(exits, list) and bool(exits) and all(type(code) is int and 0 <= code <= 255 for code in exits)
                 and len(set(exits)) == len(exits), "Explicit distinct expected exit codes required")
        if "closure_target" in value:
            target = value["closure_target"]
            _require(isinstance(target, dict) and set(target) == {"original_check", "condition_sha256", "input_bindings"},
                     "Exact closure_target binding required")
            _text(target["original_check"], "original_check")
            _sha(target["condition_sha256"])
            _require(isinstance(target["input_bindings"], dict) and bool(target["input_bindings"]), "Closure inputs required")
            for name, digest in target["input_bindings"].items():
                _text(name, "closure input")
                _sha(digest)
                _require(digest in {row["sha256"] for row in inputs},
                         "Every closure input binding must name an exact executed spec.inputs digest")
        canonical = json.loads(_json_bytes(value))
        canonical["environment"] = [key + "=" + val for key, val in sorted(environment_map(value["environment"]).items())]
        canonical["ulimits"] = [dict(Name=name, **limits) for name, limits in sorted(ulimit_map(value["ulimits"]).items())]
        canonical["inputs"] = sorted(inputs, key=lambda row: row["path"])
        encoded = _json_bytes(canonical)
        return cls(encoded, hashlib.sha256(encoded).hexdigest())


@dataclass(frozen=True)
class FreshAdmission:
    operation_id: str
    spec_sha256: str
    phase: str
    observed_utc_ns: int
    observed_mono_ns: int
    evidence: dict
    resource_snapshot: dict


def verify_inputs(spec):
    for row in spec.data["inputs"]:
        fd = os.open(row["path"], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode), "Input must be a regular non-symlink file")
            digest = hashlib.sha256()
            remaining = before.st_size + 1
            while remaining:
                chunk = os.read(fd, min(1024 * 1024, remaining))
                if not chunk:
                    break
                digest.update(chunk)
                remaining -= len(chunk)
            after = os.fstat(fd)
            _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                     == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                     and digest.hexdigest() == row["sha256"], "Exact operation input changed: " + row["path"])
        finally:
            os.close(fd)
    _require(Path(spec.data["cwd"]).is_dir(), "Operation cwd is absent")


def verify_original(spec, repo):
    rows = validate_ledger(load_ledger(repo))
    ident = spec.data["original_id"]
    _require(ident in rows["tasks"] or ident in rows["requirements"], "Unknown canonical original_id")
    target = spec.data.get("closure_target")
    if target is not None:
        _require(target["original_check"] == ident and ident in rows["tasks"]
                 and target["condition_sha256"] == condition_sha256(rows["tasks"][ident]),
                 "Closure target must match exact counted original_id and canonical condition")


def _process_identity(pid):
    raw = Path("/proc") / str(pid) / "stat"
    fields = raw.read_text(encoding="ascii").rpartition(") ")[2].split()
    return {"pid": pid, "start_ticks": fields[19],
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()}


def _error(stage, error):
    return {"stage": stage, "type": type(error).__name__, "message": str(error)}


class NoStartError(RuntimeError):
    """Backend positively joined its failed constructor and closed all captures."""


class OperationJournalError(OSError):
    """Uncommitted result retains its primary failure; it grants no release."""
    def __init__(self, error, record):
        super().__init__("Operation journal unavailable: " + str(error))
        self.record = json.loads(_json_bytes(record))
        self.record.update(reservation="HELD", release_committed=False)


class HostProcessBackend:
    """Original Linux subreaper supervisor and invocation-bound closure pipe.

    RLIMIT_AS bounds each process, not aggregate descendant memory. The trusted
    source/ownership provider must validate the command's measured family demand;
    this backend does not claim a cgroup-enforced aggregate memory ceiling.
    """
    def start(self, spec, stdout_path, stderr_path):
        row = spec.data
        streams, proof_read, proof_write = [], None, None
        try:
            for path in (stdout_path, stderr_path):
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                streams.append(os.fdopen(fd, "wb", buffering=0))
            # A fresh supervisor applies limits and starts the exact argv,
            # avoiding preexec_fn in the potentially threaded controller.
            proof_read, proof_write = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
            nonce = uuid4().hex
            config = {key: row[key] for key in ("argv", "ulimits", "resources")}
            config.update(proof_fd=proof_write, operation_id=spec.operation_id,
                          spec_sha256=spec.digest, nonce=nonce)
            command = [sys.executable, str(Path(__file__).resolve()), "--host-child", _json_bytes(config).decode()]
            started_utc, started_mono = time.time_ns(), time.monotonic_ns()
            process = subprocess.Popen(command, cwd=row["cwd"], env=environment_map(row["environment"]),
                                       stdin=subprocess.DEVNULL, stdout=streams[0], stderr=streams[1],
                                       start_new_session=row["owned_process_group"], close_fds=True,
                                       pass_fds=(proof_write,))
        except Exception as error:
            for stream in streams:
                stream.close()
            for fd in (proof_read, proof_write):
                if fd is not None:
                    os.close(fd)
            raise NoStartError(str(error)) from error
        # Popen has returned an original live handle. No subsequent setup error
        # may ever be classified as proof that no process was created.
        post_start_error = None
        try:
            os.close(proof_write)
            proof_write = None
        except Exception as error:
            post_start_error = _error("post_start_proof_descriptor_close", error)
        try:
            identity, identity_error = _process_identity(process.pid), None
        except Exception as error:
            identity, identity_error = None, _error("original_identity", error)
        return {"process": process, "streams": streams,
                "pgid": process.pid if row["owned_process_group"] else None,
                "identity": identity, "identity_error": identity_error,
                "post_start_error": post_start_error, "proof_write_retained": proof_write,
                "proof_fd": proof_read, "nonce": nonce, "operation_id": spec.operation_id,
                "spec_sha256": spec.digest,
                "started_utc_ns": started_utc, "started_mono_ns": started_mono,
                "stdout_path": str(stdout_path), "stderr_path": str(stderr_path)}

    def wait(self, handle, timeout):
        return handle["process"].wait(timeout=max(0, timeout))

    def group_closed(self, handle):
        # A direct child receipt alone cannot close an untracked descendant
        # family. Such a spec may run but retains its reservation for its owner.
        if handle["pgid"] is None:
            return False
        try:
            os.killpg(handle["pgid"], 0)
        except ProcessLookupError:
            return True
        return False

    def family_closed(self, handle):
        if handle["process"].returncode is None:
            return False
        if handle.get("family_proof") is None:
            chunks = []
            try:
                while True:
                    chunk = os.read(handle["proof_fd"], 4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if sum(map(len, chunks)) > 4096:
                        return False
            except BlockingIOError:
                return False
            try:
                proof = json.loads(b"".join(chunks))
            except (ValueError, UnicodeError):
                return False
            if not (isinstance(proof, dict) and proof.get("schema") == "mckernel-host-family-closure-v1"
                    and proof.get("operation_id") == handle["operation_id"]
                    and proof.get("spec_sha256") == handle["spec_sha256"]
                    and proof.get("nonce") == handle["nonce"]
                    and proof.get("supervisor") == handle["identity"]
                    and proof.get("waitpid_terminal") == "ECHILD"
                    and type(proof.get("reaped_children")) is int and proof["reaped_children"] >= 1
                    and type(proof.get("payload_returncode")) is int
                    and (proof["payload_returncode"] if proof["payload_returncode"] >= 0 else
                         128 - proof["payload_returncode"]) == handle["process"].returncode):
                return False
            handle["family_proof"] = proof
        return True

    def cleanup(self, handle, deadline_mono_ns):
        process = handle["process"]
        remaining = lambda: max(0, (deadline_mono_ns - time.monotonic_ns()) / 1e9)
        if not self.group_closed(handle):
            # Only the group created by this original start is eligible. A
            # false owned_process_group never becomes authority to signal one.
            if handle["pgid"] is not None:
                self._owned_unreaped_leader(handle)
                try:
                    os.killpg(handle["pgid"], signal.SIGTERM)
                except ProcessLookupError:
                    pass
                # Do not reap the original leader during the grace period: its
                # still-owned PID/birth pins this original group number. Once
                # joined, a numeric PGID is never renewed signal authority.
                proof_ready, _, _ = select.select([handle["proof_fd"]], [], [], min(remaining() / 2, 0.25))
                if not proof_ready and remaining() > 0 and not self.group_closed(handle):
                    self._owned_unreaped_leader(handle)
                    try:
                        os.killpg(handle["pgid"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            elif process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=min(remaining(), 0.05))
                except subprocess.TimeoutExpired:
                    if remaining() > 0:
                        process.kill()
        process.wait(timeout=remaining())
        return self.group_closed(handle) and self.family_closed(handle)

    def _owned_unreaped_leader(self, handle):
        process = handle["process"]
        _require(process.returncode is None and handle["pgid"] == process.pid
                 and _process_identity(process.pid) == handle["identity"]
                 and os.getpgid(process.pid) == handle["pgid"]
                 and os.getsid(process.pid) == handle["pgid"],
                 "Original unreaped process-group leader ownership is unproven; retain custody")

    def close_captures(self, handle):
        errors, captures = [], {}
        handle["diagnostic_tails"] = {}
        if handle.get("proof_write_retained") is not None:
            try:
                os.close(handle["proof_write_retained"])
                handle["proof_write_retained"] = None
            except Exception as error:
                errors.append(_error("retained_family_proof_write_close", error))
        try:
            os.close(handle["proof_fd"])
        except Exception as error:
            errors.append(_error("family_proof_close", error))
        for key, stream in zip(("stdout", "stderr"), handle["streams"]):
            try:
                stream.flush()
                os.fsync(stream.fileno())
            except Exception as error:
                errors.append(_error("capture_" + key, error))
            try:
                stream.close()
            except Exception as error:
                errors.append(_error("capture_close_" + key, error))
            path = Path(handle[key + "_path"])
            try:
                digest, size, tail = hashlib.sha256(), 0, b""
                with path.open("rb") as captured:
                    while True:
                        chunk = captured.read(1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                        size += len(chunk)
                        tail = (tail + chunk)[-8192:]
                captures[key] = {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}
                handle["diagnostic_tails"][key] = tail.decode("utf-8", "replace")
            except Exception as error:
                errors.append(_error("capture_digest_" + key, error))
        return captures, errors


class OperationRunner:
    def __init__(self, journal_dir, admission_provider=None, *, backend=None, repo=None):
        self.directory = Path(journal_dir)
        self.admission_provider = admission_provider
        self.backend = backend if backend is not None else HostProcessBackend()
        self.repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[1]
        self.last_result = None
        self.workers = {}
        self.handles = {}

    def _ensure_directory(self):
        missing, target = [], self.directory
        while not target.exists():
            missing.append(target)
            target = target.parent
        for directory in reversed(missing):
            directory.mkdir(mode=0o700, exist_ok=True)
            # The journal directory's own entry must survive a crash too, not
            # only the record rename within it. Preserve every new ancestor.
            parent = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)

    @contextmanager
    def _lock(self, name, *, blocking=True, deadline=None):
        if deadline is not None and time.monotonic_ns() >= deadline:
            raise TimeoutError("Operation transaction lock deadline expired")
        self._ensure_directory()
        fd = os.open(self.directory / name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            if deadline is None:
                fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            else:
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        remaining = (deadline - time.monotonic_ns()) / 1e9
                        if remaining <= 0:
                            raise TimeoutError("Operation transaction lock deadline expired")
                        threading.Event().wait(min(remaining, 0.01))
            yield
        finally:
            os.close(fd)

    def _records(self):
        records = []
        for path in sorted(self.directory.glob("*.json")):
            row = read_json(path)
            _require(isinstance(row, dict) and row.get("schema") == SCHEMA
                     and path.stem == row.get("operation_id"), "Invalid operation journal; accounting is UNKNOWN")
            _require(row.get("reservation") in {"ACTIVE", "HELD", "RELEASED"}, "Unknown reservation state")
            _require(row.get("spec_sha256") == OperationSpec.parse(row["spec"]).digest, "Changed journal spec")
            if row["reservation"] == "RELEASED":
                proof = row.get("closure_proof")
                _require(row.get("custody_state") == "CLOSED" and isinstance(proof, dict)
                         and proof.get("operation_id") == row["operation_id"]
                         and proof.get("spec_sha256") == row["spec_sha256"]
                         and proof.get("basis") in {"original_wait_subreaper_echild_captures_closed", "positive_no_start"},
                         "Released operation lacks positive original closure proof")
            records.append(row)
        return records

    def _save(self, row):
        path = self.directory / (row["operation_id"] + ".json")
        temporary = self.directory / (row["operation_id"] + ".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(_json_bytes(row) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            parent = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        except BaseException:
            # An uncertain commit never becomes permission to start or release.
            raise

    def _charges(self, records, omit=None):
        return tuple({"owner": "operation:" + row["operation_id"],
                      "planning_bytes": row["spec"]["resources"]["planning_bytes"],
                      "jobs": row["spec"]["resources"]["jobs"],
                      "state": "UNKNOWN" if row["reservation"] == "HELD" else "ACTIVE"}
                     for row in records if row["reservation"] != "RELEASED" and row["operation_id"] != omit)

    def _commit(self, row):
        try:
            self._save(row)
        except BaseException as error:
            row.setdefault("journal_errors", []).append(_error("journal", error))
            failure = OperationJournalError(error, row)
            self.last_result = failure.record
            raise failure from error

    def _worker(self, row, kind, function, deadline):
        _require(not row.get("pending_worker"), "Original bounded worker is still retained")
        _require(time.monotonic_ns() < deadline, kind + " original deadline expired")
        answers = queue.Queue(maxsize=1)
        def work():
            try:
                answers.put((True, function()))
            except BaseException as error:
                answers.put((False, error))
        thread = threading.Thread(target=work, daemon=True, name="host-operation-" + kind)
        row["pending_worker"] = {"kind": kind, "state": "STARTING", "owner_process": row["owner_process"]}
        with self._lock(".transactions.lock", deadline=deadline):
            self._commit(row)  # reserve and retain worker before its first effect
        self.workers[row["operation_id"]] = thread
        _RETAINED_CONTEXTS[(str(self.directory.resolve()), row["operation_id"])] = self
        thread.start()
        row["pending_worker"].update(state="RUNNING", native_thread_id=thread.native_id)
        thread.join(timeout=max(0, (deadline - time.monotonic_ns()) / 1e9))
        if thread.is_alive():
            row["pending_worker"]["state"] = "HELD_UNKNOWN"
            raise TimeoutError(kind + " deadline expired; original worker retained")
        # Only this exact original thread's completed join closes its ownership.
        row["last_worker"] = dict(row["pending_worker"], state="CLOSED")
        row["pending_worker"] = None
        del self.workers[row["operation_id"]]
        okay, result = answers.get_nowait()
        if not okay:
            raise result
        return result

    def _fresh_bookend(self, spec, admission, deadline):
        for observed in (admission, admission["resources"]):
            utc_age = time.time_ns() - observed["observed_utc_ns"]
            mono_age = time.monotonic_ns() - observed["observed_mono_ns"]
            _require(0 <= min(utc_age, mono_age) and max(utc_age, mono_age) <= spec.data["resources"]["max_age_ns"]
                     and abs(utc_age - mono_age) <= 1_000_000_000 and time.monotonic_ns() < deadline,
                     "Actual admission expired before operation effects")

    def _admit(self, spec, phase, records, deadline, row):
        _require(callable(self.admission_provider), "Trusted fresh same-Root admission provider is required")
        charges = self._charges(records)
        # A blocked read-only validator cannot consume an unbounded cleanup
        # window. An abandoned validator has no execution or journal authority.
        proof = self._worker(row, phase + "_admission", lambda: self.admission_provider(
            spec, phase=phase, active_charges=charges, deadline_mono_ns=deadline),
            deadline)
        _require(type(proof) is FreshAdmission, "Provider must return bound FreshAdmission, never supplied flags")
        _require(proof.operation_id == spec.operation_id and proof.spec_sha256 == spec.digest and proof.phase == phase,
                 "Fresh admission does not match exact operation/phase")
        _require(isinstance(proof.evidence, dict) and set(proof.evidence) == GATES, "All four actual admission gates required")
        for gate, evidence in proof.evidence.items():
            _text(evidence, gate + " authoritative evidence")
        now_utc, now_mono = time.time_ns(), time.monotonic_ns()
        for observed, now in ((proof.observed_utc_ns, now_utc), (proof.observed_mono_ns, now_mono)):
            _integer(observed, "admission clock")
            _require(0 <= now - observed <= spec.data["resources"]["max_age_ns"], "Fresh actual gate evidence required")
        _require(abs((now_utc - proof.observed_utc_ns) - (now_mono - proof.observed_mono_ns)) <= 1_000_000_000,
                 "Gate clock pair is incoherent")
        _require(now_mono <= deadline, "Admission consumed original deadline")
        snapshot = json.loads(_json_bytes(proof.resource_snapshot))
        with self._lock(".transactions.lock", deadline=deadline):
            result = self._account(spec, snapshot, self._records())
            self._commit(row)  # exact completed worker joined; no pending thread
        return {"phase": phase, "observed_utc_ns": proof.observed_utc_ns,
                "observed_mono_ns": proof.observed_mono_ns, "evidence": dict(proof.evidence),
                "resource_snapshot": snapshot, "resources": result}

    def _account(self, spec, external_snapshot, records):
        snapshot = json.loads(_json_bytes(external_snapshot))
        _require(isinstance(snapshot.get("retained_charges"), list), "Complete external retained inventory required")
        # Provider owns the external inventory; this journal always contributes
        # every own unresolved charge. For cleanup, its original charge replaces
        # the request rather than being allocated a second time.
        snapshot["retained_charges"].extend(self._charges(records, omit=spec.operation_id))
        return check_payload_admission(snapshot, spec.data["resources"],
                                       now_utc_ns=time.time_ns(), now_mono_ns=time.monotonic_ns())

    def status(self):
        if not self.directory.exists():
            return []
        if not (self.directory / ".transactions.lock").exists():
            _require(not list(self.directory.glob("*.json")), "Journal transaction lock is missing; accounting is UNKNOWN")
            return []
        with self._lock(".transactions.lock"):
            return self._records()

    def reconcile(self):
        """Only preserve abandoned records. No process/control/resource effects."""
        if not self.directory.exists():
            return []
        with self._lock(".transactions.lock"):
            rows = self._records()
            for row in rows:
                if row["reservation"] != "ACTIVE":
                    continue
                try:
                    with self._lock(row["operation_id"] + ".lock", blocking=False):
                        row.update(reservation="HELD", phase="RECONCILED_HELD", custody_state="HELD_UNKNOWN")
                        if row["payload_state"] != "NOT_STARTED":
                            row["payload_state"] = "UNKNOWN"
                        self._save(row)
                except BlockingIOError:
                    pass
            return rows

    def run(self, value):
        spec = OperationSpec.parse(value)
        verify_original(spec, self.repo)
        verify_inputs(spec)
        _require(callable(self.admission_provider), "Trusted fresh same-Root admission provider is required")
        with self._lock(spec.operation_id + ".lock", blocking=False):
            with self._lock(".transactions.lock"):
                records = self._records()
                _require(not any(row["operation_id"] == spec.operation_id for row in records),
                         "Original operation_id already recorded; replay is forbidden")
                _require(not any(row.get("pending_worker") for row in records),
                         "Original pending worker retained; further operations are blocked")
                row = {"schema": SCHEMA, "operation_id": spec.operation_id, "original_id": spec.data["original_id"],
                       "owner_id": spec.data["owner_id"], "spec_sha256": spec.digest, "spec": spec.data,
                       "reservation": "ACTIVE", "phase": "VALIDATING", "payload_state": "NOT_STARTED",
                       "custody_state": "NOT_CREATED", "admissions": [], "primary_error": None,
                       "cleanup_errors": [], "captures": {}, "created_utc_ns": time.time_ns(),
                       "owner_process": _process_identity(os.getpid()), "journal_errors": [],
                       "requested_bounds": {"execution_timeout_s": spec.data["execution_timeout_s"],
                                            "cleanup_timeout_s": spec.data["cleanup_timeout_s"]},
                       "automatic_replay": False}
                self._commit(row)
            admission_deadline = time.monotonic_ns() + spec.data["resources"]["max_age_ns"]
            try:
                admission = self._admit(spec, "execute", records + [row], admission_deadline, row)
                row["admissions"].append(admission)
                verify_inputs(spec)
                self._fresh_bookend(spec, admission, admission_deadline)
            except OperationJournalError:
                raise
            except BaseException as error:
                row.update(primary_error=_error("admission", error), phase="HELD" if row.get("pending_worker") else "FINISHED",
                           reservation="HELD" if row.get("pending_worker") else "RELEASED",
                           custody_state="HELD_UNKNOWN" if row.get("pending_worker") else "CLOSED")
                if not row.get("pending_worker"):
                    row["closure_proof"] = {"operation_id": spec.operation_id, "spec_sha256": spec.digest,
                                            "basis": "positive_no_start"}
                with self._lock(".transactions.lock"):
                    self._commit(row)
                self.last_result = json.loads(_json_bytes(row))
                error.operation_record = self.last_result
                raise
            with self._lock(".transactions.lock", deadline=admission_deadline):
                admission["resources"] = self._account(spec, admission["resource_snapshot"], self._records())
                self._fresh_bookend(spec, admission, admission_deadline)
                execution_deadline = time.monotonic_ns() + int(spec.data["execution_timeout_s"] * 1e9)
                row.update(phase="STARTING", payload_state="UNKNOWN", custody_state="HELD_UNKNOWN",
                           start_attempted_utc_ns=time.time_ns(), execution_deadline_mono_ns=execution_deadline,
                           execution_deadline_utc_ns=time.time_ns() + int(spec.data["execution_timeout_s"] * 1e9))
                self._commit(row)
            handle, closed, start_invoked = None, False, False
            try:
                self._fresh_bookend(spec, admission, min(admission_deadline, execution_deadline))
                start_invoked = True
                handle = self.backend.start(spec, self.directory / (spec.operation_id + ".stdout"),
                                            self.directory / (spec.operation_id + ".stderr"))
                self.handles[spec.operation_id] = handle
                _RETAINED_CONTEXTS[(str(self.directory.resolve()), spec.operation_id)] = {"runner": self, "handle": handle}
                row.update(phase="RUNNING", started_utc_ns=handle["started_utc_ns"],
                           started_mono_ns=handle["started_mono_ns"], original_process=handle["identity"],
                           original_pid=handle["process"].pid, original_pgid=handle["pgid"])
                if handle.get("identity_error"):
                    row["identity_error"] = handle["identity_error"]
                with self._lock(".transactions.lock", deadline=execution_deadline):
                    self._commit(row)
                if handle.get("post_start_error"):
                    raise RuntimeError("Post-start descriptor closure failed: " + handle["post_start_error"]["message"])
                code = self.backend.wait(handle, max(0, (execution_deadline - time.monotonic_ns()) / 1e9))
                row["returncode"] = code
                row["payload_state"] = "PASS" if code in spec.data["expected_exit_codes"] else "FAIL"
                if row["payload_state"] == "FAIL":
                    row["primary_error"] = _error("payload_exit", RuntimeError("Unexpected exit status " + str(code)))
                closed = (self.backend.group_closed(handle) and self.backend.family_closed(handle)
                          and handle.get("identity") is not None)
            except NoStartError as error:
                row.update(payload_state="NOT_STARTED", primary_error=_error("start", error))
                closed = True
            except BaseException as error:
                row["primary_error"] = _error("execution" if handle else "ambiguous_start" if start_invoked else "pre_start", error)
                if not start_invoked:
                    row["payload_state"], closed = "NOT_STARTED", True
            finally:
                deadline = time.monotonic_ns() + int(spec.data["cleanup_timeout_s"] * 1e9)
                row.update(execution_finished_utc_ns=time.time_ns(), cleanup_deadline_mono_ns=deadline,
                           cleanup_deadline_utc_ns=time.time_ns() + int(spec.data["cleanup_timeout_s"] * 1e9))
                if handle is not None and not closed:
                    try:
                        with self._lock(".transactions.lock", deadline=deadline):
                            cleanup_records = self._records()
                        admission = self._admit(spec, "cleanup", cleanup_records, deadline, row)
                        row["admissions"].append(admission)
                        with self._lock(".transactions.lock", deadline=deadline):
                            admission["resources"] = self._account(spec, admission["resource_snapshot"], self._records())
                            self._fresh_bookend(spec, admission, deadline)
                            row["phase"] = "CLEANING"
                            self._commit(row)  # durable exact cleanup admission before signals
                        self._fresh_bookend(spec, admission, deadline)
                        closed = self.backend.cleanup(handle, deadline)
                    except BaseException as error:
                        row["cleanup_errors"].append(_error("cleanup", error))
                if handle is not None:
                    try:
                        captures, errors = self._worker(row, "capture_finalization",
                            lambda: self.backend.close_captures(handle), deadline)
                        row["captures"], row["cleanup_errors"] = captures, row["cleanup_errors"] + errors
                        closed = closed and not errors
                    except BaseException as error:
                        row["cleanup_errors"].append(_error("capture_finalization", error))
                        closed = False
                row.update(phase="FINISHED" if closed else "HELD", finished_utc_ns=time.time_ns(),
                           custody_state="CLOSED" if closed else "HELD_UNKNOWN",
                           reservation="RELEASED" if closed else "HELD")
                row["bounded_result"] = {"execution_timed_out": bool(row["primary_error"] and
                    row["primary_error"]["type"] == "TimeoutExpired"),
                    "cleanup_deadline_exceeded": time.monotonic_ns() > deadline,
                    "custody_closed": closed}
                if closed:
                    row["closure_proof"] = {"operation_id": spec.operation_id, "spec_sha256": spec.digest,
                                            "basis": "positive_no_start" if handle is None else
                                            "original_wait_subreaper_echild_captures_closed"}
                    if handle is not None:
                        row["family_closure"] = handle["family_proof"]
                if ("closure_target" in spec.data and row["payload_state"] == "FAIL"
                        and row["primary_error"] and row["primary_error"]["stage"] == "payload_exit"):
                    failure = row["primary_error"]
                    diagnostic = self._failure_diagnostic(row, handle)
                    row["ordinary_failure"] = dict(spec.data["closure_target"],
                        schema="mckernel-closure-evidence-v1", kind="ordinary_failure", status="failed",
                        stage=failure["stage"], defect=failure["message"] + (": " + diagnostic["text"] if diagnostic["text"] else ""),
                        diagnostic=diagnostic, owner=spec.data["owner_id"],
                        diagnostic_sha256=hashlib.sha256(_json_bytes(
                            {"stage": failure["stage"], "returncode": row["returncode"],
                             "message": failure["message"], "diagnostic": diagnostic["text"]})).hexdigest())
                try:
                    with self._lock(".transactions.lock", deadline=deadline):
                        self._commit(row)  # failure here leaves earlier charge durable
                except OperationJournalError:
                    raise
                except BaseException as error:
                    row["journal_errors"].append(_error("final_transaction", error))
                    failure = OperationJournalError(error, row)
                    self.last_result = failure.record
                    raise failure from error
                self.last_result = json.loads(_json_bytes(row))
                context = (str(self.directory.resolve()), spec.operation_id)
                if closed:
                    self.handles.pop(spec.operation_id, None)
                    _RETAINED_CONTEXTS.pop(context, None)
                else:
                    _RETAINED_CONTEXTS[context] = {"runner": self, "handle": handle}
            return row

    def _failure_diagnostic(self, row, handle):
        """Bounded useful compiler/test defect; exact capture remains separate."""
        for key in ("stderr", "stdout"):
            ref = row["captures"].get(key)
            if not ref:
                continue
            lines = handle.get("diagnostic_tails", {}).get(key, "").splitlines()
            lines = [" ".join(line.split()) for line in lines if line.strip()]
            errors = [line for line in lines if re.search("error|exception|failed|failure|undefined reference|fatal|panic|assert", line, re.I)]
            selected = errors[-1] if errors else lines[-1] if lines and key == "stderr" else ""
            if selected:
                text = selected.replace(row["spec"]["cwd"], "<cwd>")[:512]
                return {"text": text, "stream": key, "capture": dict(ref)}
        return {"text": "", "stream": None, "capture": None}


def _host_child(encoded):
    config = json.loads(encoded)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # Linux PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "Cannot establish original child subreaper")
    # The original supervisor survives the group's TERM long enough to join
    # children and publish proof. Exec resets this caught handler in the payload.
    signal.signal(signal.SIGTERM, lambda *_: None)
    os.sched_setaffinity(0, config["resources"]["CPU"])
    for name, limits in ulimit_map(config["ulimits"]).items():
        resource.setrlimit(LIMIT_NAMES[name], (limits["Soft"], limits["Hard"]))
    memory = config["resources"]["planning_bytes"]
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (min(memory, soft) if soft != resource.RLIM_INFINITY else memory,
                                          min(memory, hard) if hard != resource.RLIM_INFINITY else memory))
    payload = subprocess.Popen(config["argv"], env=dict(os.environ), close_fds=True)
    payload_identity = _process_identity(payload.pid)
    payload_code, reaped = None, 0
    while True:
        try:
            pid, status = os.waitpid(-1, 0)
        except ChildProcessError:
            break
        reaped += 1
        if pid == payload.pid:
            payload_code = os.waitstatus_to_exitcode(status)
            payload.returncode = payload_code
    _require(payload_code is not None, "Original payload terminal wait is missing")
    # The fd is inherited only by this supervisor. Exact payload/descendant
    # subprocesses close it on exec and cannot manufacture a positive receipt.
    proof = {"schema": "mckernel-host-family-closure-v1", "operation_id": config["operation_id"],
             "spec_sha256": config["spec_sha256"], "nonce": config["nonce"],
             "supervisor": _process_identity(os.getpid()), "payload": payload_identity,
             "payload_returncode": payload_code, "reaped_children": reaped, "waitpid_terminal": "ECHILD"}
    os.write(config["proof_fd"], _json_bytes(proof))
    os.close(config["proof_fd"])
    # Preserve ordinary payload status; signal termination is reported as the
    # shell-style bounded status, with its actual signal retained in the proof.
    return payload_code if payload_code >= 0 else 128 - payload_code


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 2 and argv[0] == "--host-child":
        return _host_child(argv[1])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "status", "reconcile"))
    parser.add_argument("path", help="spec JSON for validate; journal directory otherwise")
    args = parser.parse_args(argv)
    if args.action == "validate":
        spec = OperationSpec.parse(read_json(args.path))
        verify_original(spec, Path(__file__).resolve().parents[1])
        verify_inputs(spec)
        result = {"valid": True, "spec_sha256": spec.digest, "execution_admission": False}
    else:
        runner = OperationRunner(args.path)
        result = runner.status() if args.action == "status" else runner.reconcile()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
