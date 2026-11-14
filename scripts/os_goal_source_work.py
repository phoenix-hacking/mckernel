"""Bound one non-executable source attachment to the existing instruction queue.

Functional OS/Rust harness engineering only; no security testing. This module
has no queue, background worker, model call, signal, wait, affinity mutation or
release operation. The existing queue publishes ``prepare_attachment`` output.
The existing consumer calls ``validate_registered_source_work`` immediately
before its normal deduplicated dispatch, then rechecks its stop generation.

Account and terminal callbacks must be the parent's real guarded account read
and original model-turn receipt lookup, never deserializers of narrative claims.
Retained charges, exclusivity scopes and controller roots come from the sole
Root's current registries. Missing/unknown records are not inferred from /proc.
"""
import hashlib
from functools import wraps
import json
import os
from pathlib import Path
import shutil
import stat
import time

from os_goal_repair import blocked_repair_key
from os_goal_resources import (GIB, HOST_CPUS, MAX_ADMISSION_AGE_NS,
                               MAX_PAIRED_CLOCK_SKEW_NS)


MAX_RECORD_BYTES = 65536
MAX_SOURCE_BYTES = 2 * 1024 ** 2
MAX_INPUTS = 16
MAX_PROCESSES = 128
MAX_THREADS = 128
BINDING_FIELDS = ("thread_id", "invocation", "worker_pid", "worker_start", "log_dir", "credit_run_id")
KINDS = {"source", "test_preparation", "read_only_review"}
LANE_HOLDS = {"source_hold", "operation_hold", "native_hold", "resource_hold"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _refuse_incomplete(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (KeyError, TypeError, OSError, UnicodeError) as error:
            raise ValueError("Source registration/accounting is incomplete or changed") from error
    return checked


def _integer(value, name, minimum=0):
    _require(type(value) is int and value >= minimum, name + " must be an explicit integer")
    return value


def _text(value, name, limit=512):
    _require(isinstance(value, str) and 0 < len(value) <= limit and bool(value.strip()),
             name + " must be bounded text")
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _sha(value):
    _require(isinstance(value, str) and len(value) == 64
             and all(c in "0123456789abcdef" for c in value), "Invalid SHA256 binding")
    return value


def _path(value):
    path = Path(_text(str(value), "path", 4096))
    _require(path.is_absolute() and ".." not in path.parts, "Path must be absolute without traversal")
    for part in (path, *path.parents):
        _require(not part.is_symlink(), "Symlink is not an exact source binding")
    return path


def _under(path, root):
    return path == root or root in path.parents


def _source_path(value, allowed_roots, writing=False):
    path = _path(value)
    roots = [_path(root) for root in allowed_roots]
    _require(roots and any(_under(path, root) for root in roots), "Source path is outside approved roots")
    _require(not any(part == ".git" or part.startswith("ROOT-PRIVATE") for part in path.parts),
             "Control/protected records are not source inputs")
    if writing:
        _require(path.parent.is_dir() and (not path.exists() or path.is_file()),
                 "Source write must name one file with an existing parent")
    return path


def _read_bytes(path, limit, private=False):
    path = _path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, "Expected a bounded regular file")
        if private:
            _require(before.st_uid == os.getuid() and stat.S_IMODE(before.st_mode) == 0o600,
                     "Instruction record is not owned/private")
        parts, size = [], 0
        while size <= limit:
            chunk = os.read(fd, min(8192, limit + 1 - size))
            if not chunk:
                break
            parts.append(chunk)
            size += len(chunk)
        after = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        _require(size <= limit and identity(before) == identity(after) == identity(named),
                 "Input changed during its bounded read")
        return b"".join(parts)
    finally:
        os.close(fd)


def _queue_record(path, reader):
    """Use the existing queue protocol's logical-size policy, not another cap."""
    path = _path(path)
    before = os.stat(path, follow_symlinks=False)
    _require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
             and stat.S_IMODE(before.st_mode) == 0o600, "Instruction record is not owned/private")
    value = reader(path)
    after = os.stat(path, follow_symlinks=False)
    identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
    _require(identity(before) == identity(after), "Instruction changed during the protocol read")
    _require(isinstance(value, dict), "Instruction record must be an object")
    return value


def _binding(value):
    _require(isinstance(value, dict) and set(value) == set(BINDING_FIELDS), "Exact Root binding is required")
    result = {name: _text(value[name], name, 4096 if name == "log_dir" else 512)
              for name in BINDING_FIELDS if name != "worker_pid"}
    result["worker_pid"] = _integer(value["worker_pid"], "worker_pid", 1)
    _require(result["worker_start"].isdigit(), "worker_start must be the original /proc birth")
    _path(result["log_dir"])
    return result


def _input_ref(row, allowed_roots):
    _require(isinstance(row, dict) and set(row) == {"id", "kind", "path", "bytes", "sha256"},
             "Exact source reference fields are required")
    path = _source_path(row["path"], allowed_roots)
    _require(row["kind"] in {"source", "review"}, "Only source/review files may be registered")
    size = _integer(row["bytes"], "source bytes")
    _require(size <= MAX_SOURCE_BYTES, "Source input exceeds the finite input bound")
    raw = _read_bytes(path, MAX_SOURCE_BYTES)
    _require(len(raw) == size and hashlib.sha256(raw).hexdigest() == _sha(row["sha256"]),
             "Current source bytes do not match the registered reference")
    return dict(row, id=_text(row["id"], "input id"), path=str(path))


@_refuse_incomplete
def prepare_attachment(spec, *, binding, source_id, text, allowed_roots):
    """Normalize exact current inputs for the EXISTING queue; write nothing.

    Queue publication must include this whole attachment in the existing
    source-ID immutability comparison, as well as its text digest.
    """
    binding = _binding(binding)
    _require(isinstance(spec, dict) and set(spec) == {
        "task_id", "original_check", "kind", "blocker", "inputs", "write_paths", "limits"},
        "Exact source-work specification is required")
    _require(spec["kind"] in KINDS, "Executable/native/payload work is not a source attachment")
    original = _text(spec["original_check"], "original_check")
    _require(original.startswith(("M14-", "M15-")), "Source work must advance an original M14/M15 check")
    blocker = spec["blocker"]
    _require(isinstance(blocker, dict) and set(blocker) == {"task_id", "thread_id", "turn_id", "hold_fields"},
             "Exact blocked model-turn binding is required")
    blocker = dict(blocker)
    for name in ("task_id", "thread_id", "turn_id"):
        _text(blocker[name], "blocker " + name)
    fields = blocker["hold_fields"]
    _require(isinstance(fields, list) and fields and len(set(fields)) == len(fields)
             and set(fields).issubset(LANE_HOLDS), "Blocker scope is not positively lane-scoped")
    blocker["hold_fields"] = sorted(fields)
    task_id = _text(spec["task_id"], "task_id")
    _require(task_id != blocker["task_id"], "A blocked task cannot re-register itself as independent")
    rows = spec["inputs"]
    _require(isinstance(rows, list) and 1 <= len(rows) <= MAX_INPUTS, "Finite named source inputs are required")
    inputs = [_input_ref(row, allowed_roots) for row in rows]
    _require(len({row["id"] for row in inputs}) == len(inputs), "Source input IDs must be distinct")
    writes = spec["write_paths"]
    _require(isinstance(writes, list) and len(writes) <= MAX_INPUTS, "Source writes must be a finite file list")
    writes = sorted(str(_source_path(path, allowed_roots, writing=True)) for path in writes)
    _require(len(set(writes)) == len(writes), "Source write paths must be distinct")
    _require(spec["kind"] != "read_only_review" or not writes, "Read-only review cannot authorize writes")
    limits = spec["limits"]
    _require(isinstance(limits, dict) and set(limits) == {
        "source_overhead_reserve_bytes", "host_floor_bytes", "scratch_floor_bytes", "max_age_ns"},
        "Explicit source-overhead/floor/freshness limits are required")
    limits = {name: _integer(value, name, 1) for name, value in limits.items()}
    _require(limits["max_age_ns"] <= MAX_ADMISSION_AGE_NS
             and limits["host_floor_bytes"] >= 16 * GIB and limits["scratch_floor_bytes"] >= 12 * GIB,
             "Source work cannot relax campaign freshness or disk floors")
    source_id = _text(source_id, "source_id")
    _require(isinstance(text, str) and bool(text.strip()), "Instruction must be nonempty logical text")
    body = {"schema_version": 1, "binding": binding, "source_id": source_id,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "task_id": task_id, "original_check": original, "kind": spec["kind"],
            "blocker": blocker, "inputs": inputs, "write_paths": writes, "limits": limits}
    return {"body": body, "sha256": _digest(body)}


def _clock():
    return time.time_ns(), time.monotonic_ns()


def _fresh(observed, now, max_age):
    _require(isinstance(observed, (tuple, list)) and len(observed) == 2, "Paired clock record is required")
    ages = [_integer(current, "current clock") - _integer(old, "observed clock")
            for old, current in zip(observed, now)]
    _require(min(ages) >= 0 and max(ages) <= max_age
             and abs(ages[0] - ages[1]) <= MAX_PAIRED_CLOCK_SKEW_NS,
             "Source dispatch requires fresh paired UTC/monotonic observations")


def _proc_stat(proc, pid):
    raw = _read_bytes(proc / str(pid) / "stat", MAX_RECORD_BYTES).decode("ascii")
    first, fields = raw.rsplit(") ", 1)
    _require(int(first.split(" (", 1)[0]) == pid, "Process stat identity differs")
    fields = fields.split()
    _require(len(fields) >= 20, "Incomplete process stat")
    return {"start": fields[19], "ppid": int(fields[1])}


def _cpus(value):
    cpus = set()
    for item in value.split(","):
        bounds = item.split("-")
        _require(1 <= len(bounds) <= 2 and all(part.isdigit() for part in bounds), "Invalid CPU affinity")
        low, high = int(bounds[0]), int(bounds[-1])
        _require(low <= high and high <= 4096, "Unbounded CPU affinity")
        cpus.update(range(low, high + 1))
    return cpus


def _process_observation(proc, pid):
    path = proc / str(pid)
    _require(path.stat().st_uid == os.getuid(), "Controller process owner differs")
    identity = _proc_stat(proc, pid)
    fields = {}
    for line in _read_bytes(path / "status", MAX_RECORD_BYTES).decode("ascii").splitlines():
        key, _, value = line.partition(":")
        if key in {"VmRSS", "Cpus_allowed_list"}:
            fields[key] = value.strip()
    rss = fields["VmRSS"].split()
    _require(len(rss) == 2 and rss[0].isdigit() and rss[1] == "kB", "Measured controller RSS is missing")
    affinity = _cpus(fields["Cpus_allowed_list"])
    _require(affinity and affinity.issubset(HOST_CPUS), "Controller/worker is not actually HOST-affinity bound")
    tasks = path / "task"
    tids = sorted(entry.name for entry in tasks.iterdir())
    _require(1 <= len(tids) <= MAX_THREADS and all(tid.isdigit() for tid in tids), "Unbounded controller thread family")
    children = set()
    for tid in tids:
        values = _read_bytes(tasks / tid / "children", MAX_RECORD_BYTES).decode("ascii").split()
        _require(len(values) <= MAX_PROCESSES and all(value.isdigit() for value in values), "Unbounded controller children")
        children.update(int(value) for value in values)
    return dict(identity, rss_bytes=int(rss[0]) * 1024, cpus=sorted(affinity), children=sorted(children))


def _measure(proc, roots, exclusions, controller_pid):
    _require(isinstance(roots, list) and 1 <= len(roots) <= 16, "Explicit controller/worker roots are required")
    expected = {}
    for root in roots:
        _require(isinstance(root, dict) and set(root) == {"pid", "start", "role"}
                 and root["role"] in {"controller", "worker"}, "Invalid process-family root")
        pid = _integer(root["pid"], "process pid", 1)
        _require(isinstance(root["start"], str) and root["start"].isdigit() and pid not in expected,
                 "Original controller birth binding is required")
        expected[pid] = root["start"]
    _require(controller_pid in expected, "The actual controller must be included in overhead")
    _require(not set(expected).intersection(exclusions), "Controller overhead cannot be excluded as a payload")
    pending, measured = [(pid, None) for pid in expected], {}
    while pending:
        pid, parent = pending.pop()
        if pid in measured:
            _require(parent is None or measured[pid]["ppid"] == parent, "Controller parent relation changed")
            continue
        _require(len(measured) < MAX_PROCESSES, "Controller family exceeds finite bound")
        if pid in exclusions:
            _require(_proc_stat(proc, pid)["start"] == exclusions[pid], "Retained payload PID was reused")
            continue  # Its entire retained planning charge remains counted.
        row = _process_observation(proc, pid)
        _require(pid not in expected or row["start"] == expected[pid], "Controller birth changed")
        _require(parent is None or row["ppid"] == parent, "Controller child parent relation differs")
        measured[pid] = row
        pending.extend((child, pid) for child in row["children"])
    for pid, before in measured.items():
        after = _process_observation(proc, pid)
        _require(all(before[key] == after[key] for key in ("start", "ppid", "cpus", "children")),
                 "Controller family/identity/affinity changed during accounting")
        before["rss_bytes"] = max(before["rss_bytes"], after["rss_bytes"])
    total = sum(row["rss_bytes"] for row in measured.values())
    _require(total > 0, "ALL controller/worker overhead must be measured")
    return total, [{"pid": pid, "start": row["start"], "rss_bytes": row["rss_bytes"]}
                   for pid, row in sorted(measured.items())]


@_refuse_incomplete
def validate_registered_source_work(item, *, directory, binding, goal, state, allowed_roots,
                                    terminal_turn_lookup, account_guard, process_roots,
                                    retained_charges, exclusive_scopes, queue_reader, proc_root=Path("/proc"),
                                    scratch_path=Path("/home/holden/mckernel-work/scratch"),
                                    clock=None, affinity_reader=None, disk_usage=None):
    """Revalidate one selected sending item and derive an EPHEMERAL repair view.

    The parent must remove any persisted repair_context before calling, own the
    normal launch lease, and retain its sending-intent/dedup/stop-generation checks.
    Controller and listed tool-runner families must already inherit HOST affinity;
    an external/untracked tool runner needs its own enforcement and is unsupported.
    """
    clock = _clock if clock is None else clock
    affinity_reader = os.sched_getaffinity if affinity_reader is None else affinity_reader
    disk_usage = shutil.disk_usage if disk_usage is None else disk_usage
    started = clock()
    binding = _binding(binding)
    _require(binding["worker_pid"] == os.getpid(), "Only the bound current controller may consume source work")
    _require(isinstance(item, dict) and isinstance(item.get("source_work"), dict), "Source attachment is missing")
    source_id, text = item["source_id"], item["text"]
    digest = hashlib.sha256(_text(source_id, "source_id").encode()).hexdigest()
    _require(item["id"] == "source-" + digest, "Instruction source ID differs")
    base = _path(directory) / "instructions"
    registry = _queue_record(base / "sources" / (digest + ".json"), queue_reader)
    sending = _queue_record(base / "sending" / (item["id"] + ".json"), queue_reader)
    _require(registry.get("status") == "queued" and registry.get("item") == item and sending == item,
             "Source work is not the exact registered selected instruction")
    attachment = item["source_work"]
    _require(set(attachment) == {"body", "sha256"} and _digest(attachment["body"]) == attachment["sha256"],
             "Source attachment changed")
    body = attachment["body"]
    _require(body["binding"] == binding and body["source_id"] == source_id,
             "Source attachment belongs to a different Root/invocation")
    spec = {name: body[name] for name in ("task_id", "original_check", "kind", "blocker", "inputs", "write_paths", "limits")}
    _require(prepare_attachment(spec, binding=binding, source_id=source_id, text=text,
                                allowed_roots=allowed_roots) == attachment,
             "Current source or instruction bytes differ")
    _require(item.get("text_sha256") == body["text_sha256"], "Instruction text digest differs")
    max_age = body["limits"]["max_age_ns"]
    blocker = body["blocker"]
    terminal = terminal_turn_lookup(blocker["thread_id"], blocker["turn_id"])
    _require(isinstance(terminal, dict) and terminal.get("root_thread_id") == binding["thread_id"]
             and terminal.get("invocation") == binding["invocation"]
             and terminal.get("thread_id") == blocker["thread_id"] and terminal.get("turn_id") == blocker["turn_id"]
             and terminal.get("status") in {"completed", "failed", "interrupted"},
             "Original blocked model turn has no bound terminal receipt")
    _require(isinstance(exclusive_scopes, list), "Explicit current exclusivity scopes are required")
    accesses = [Path(row["path"]) for row in body["inputs"]] + [Path(path) for path in body["write_paths"]]
    for scope in exclusive_scopes:
        _require(isinstance(scope, dict) and scope.get("scope") == "operation"
                 and scope.get("source_access") == "disjoint_paths"
                 and isinstance(scope.get("protected_paths"), list) and scope["protected_paths"],
                 "Unknown/global exclusivity cannot admit isolated source work")
        protected = [_path(path) for path in scope["protected_paths"]]
        _require(not any(_under(path, root) or _under(root, path) for path in accesses for root in protected),
                 "Source task overlaps a retained exclusive operation")
    _require(isinstance(retained_charges, list), "Explicit retained charges are required")
    retained_revision, exclusive_revision = _digest(retained_charges), _digest(exclusive_scopes)
    retained_bytes = retained_jobs = 0
    exclusions = {}
    for row in retained_charges:
        _require(isinstance(row, dict) and row.get("state") in {"ACTIVE", "RETAINED", "UNKNOWN"},
                 "Retained charge has unknown accounting")
        _text(row["owner"], "retained owner")
        retained_bytes += _integer(row["planning_bytes"], "retained bytes", 1)
        retained_jobs += _integer(row["jobs"], "retained jobs", 1)
        _require(isinstance(row["process_roots"], list), "Explicit retained payload process cut is required")
        for process in row["process_roots"]:
            pid = _integer(process["pid"], "payload pid", 1)
            start = _text(process["start"], "payload birth")
            _require(start.isdigit() and pid not in exclusions, "Retained payload process cut is ambiguous")
            exclusions[pid] = start
    affinity = set(affinity_reader(0))
    _require(affinity and affinity.issubset(HOST_CPUS), "Current controller must already be bound to HOST CPUs0,6,7")
    proc = _path(proc_root)
    overhead, processes = _measure(proc, process_roots, exclusions, binding["worker_pid"])
    mem = _read_bytes(proc / "meminfo", MAX_RECORD_BYTES).decode("ascii").splitlines()
    available = [line.split() for line in mem if line.startswith("MemAvailable:")]
    _require(len(available) == 1 and len(available[0]) == 3 and available[0][1].isdigit()
             and available[0][2] == "kB" and int(available[0][1]) * 1024 >= 26 * GIB,
             "Source dispatch requires measured26GiB MemAvailable")
    limits = body["limits"]
    total = retained_bytes + overhead + limits["source_overhead_reserve_bytes"]
    _require(total <= 4 * GIB and retained_jobs <= 3, "Retained charges + ALL source overhead exceed4GiB/max3")
    _require(disk_usage(_path(allowed_roots[0])).free >= limits["host_floor_bytes"]
             and disk_usage(_path(scratch_path)).free >= limits["scratch_floor_bytes"],
             "Exact source-dispatch disk floors are not met")
    now = clock()
    _fresh(started, now, max_age)
    account = account_guard(binding, now[0], now[1])
    _require(isinstance(account, dict) and account.get("decision") == "CLEAR_SOURCE_DISPATCH_ONLY"
             and account.get("binding") == binding, "Parent's guarded account receipt is missing")
    _sha(account["receipt_sha256"])
    final_overhead, final_processes = _measure(proc, process_roots, exclusions, binding["worker_pid"])
    _require([(row["pid"], row["start"]) for row in processes] ==
             [(row["pid"], row["start"]) for row in final_processes],
             "Controller membership changed across the account observation")
    _require(_digest(retained_charges) == retained_revision and _digest(exclusive_scopes) == exclusive_revision,
             "Current retained accounting or exclusive scope changed")
    affinity = set(affinity_reader(0))
    _require(affinity and affinity.issubset(HOST_CPUS), "Controller affinity changed before dispatch")
    overhead = max(overhead, final_overhead)
    total = retained_bytes + overhead + limits["source_overhead_reserve_bytes"]
    _require(total <= 4 * GIB, "Source overhead grew beyond the shared HOST ceiling")
    for row in body["inputs"]:
        _input_ref(row, allowed_roots)
    final = clock()
    _fresh((account["observed_utc_ns"], account["observed_mono_ns"]), final, max_age)
    _fresh(started, final, max_age)
    refs = [{"id": row["id"], "kind": row["kind"], "sha256": row["sha256"],
             "status": "registered", "current": True, "thread_id": binding["thread_id"]}
            for row in body["inputs"]]
    context = {"schema_version": 1, "thread_id": binding["thread_id"],
               "account_gate_clear": True, "source_overhead_accounted": True,
               "blocker": {"scope": "task", "task_id": blocker["task_id"],
                           "hold_fields": blocker["hold_fields"], "parked": True,
                           "turn_status": terminal["status"], "runtime_resources_retained": True},
               "task": {"task_id": body["task_id"], "kind": body["kind"],
                        "isolated_from_blocker": True, "requires_execution": False},
               "registered_inputs": refs}
    view = dict(state, repair_context=context)
    _require(all(state.get(name) == binding[name] for name in ("thread_id", "worker_pid", "worker_start", "log_dir")),
             "Current controller identity differs from the attachment")
    key = blocked_repair_key(goal, view)
    _require(key is not None, "Current global stop, activity or delivery gate forbids source dispatch")
    return {"schema_version": 1, "instruction_id": item["id"], "source_work_sha256": attachment["sha256"],
            "repair_context": context, "repair_key": key,
            "account_receipt_sha256": account["receipt_sha256"],
            "resources": {"observed_utc_ns": started[0], "observed_mono_ns": started[1],
                          "account_observed_utc_ns": account["observed_utc_ns"],
                          "account_observed_mono_ns": account["observed_mono_ns"],
                          "retained_bytes": retained_bytes, "retained_jobs": retained_jobs,
                          "measured_overhead_bytes": overhead, "source_reserve_bytes": limits["source_overhead_reserve_bytes"],
                          "accounted_total_bytes": total, "processes": processes},
            "payload_jobs_created": 0, "release_authorized": False,
            "native_or_payload_admission": False}
