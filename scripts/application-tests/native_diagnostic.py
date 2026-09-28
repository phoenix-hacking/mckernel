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
from types import MappingProxyType

QEMU = "/usr/libexec/qemu-kvm"
MAX_JSON = 4 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
ARTIFACTS = ("bzImage", "initramfs", "root_base", "mckernel_image", "mcexec", "payload",
             "native_boot", "loader", "libc")
MODULE_NAMES = ("ihk.ko", "ihk-smp-x86_64.ko", "mcctrl.ko")
APPEND = "console=ttyS0,115200n8 rdinit=/init nokaslr panic=-1 memmap=4K%0x80000-1"
# These are diagnostic records, not generic words.  In particular, the boot
# command line contains ``panic=-1``, PCI firmware prose can say "report a
# bug", and the collector emits successful fields such as ``error=0``.  None
# of those is a kernel/service failure.  Keep the actual failure spellings
# specific so normal boot output cannot poison an otherwise valid capture.
BAD_MARKERS = re.compile(
    r"(?i:\bpanic\b(?!\s*=\s*-1\b))|Oops:|BUG:|WARNING:|soft lockup\b|hard LOCKUP\b|"
    r"clear_host_pte failed\b|rcu_preempt detected stalls\b|\bFAIL\b|"
    r"continuing service error\b|cleanup retained\b|reap_retained\b|"
    r"strncpy_from_user:ioctl:|ret:\s")
STAGING_BLOCKER = "guest staging unavailable: exact derived initramfs join is incomplete"
DIAGNOSTIC_LIMITATION = "protocol observation only; independent guest execution review is pending"
FINAL_MEMBERS = {
    "init": "collector", "apps/app": "payload", "bin/mcexec": "mcexec",
    "bin/native-boot": "native_boot", "lib64/ld-linux-x86-64.so.2": "loader",
    "lib64/libc.so.6": "libc", "images/mckernel.img": "mckernel_image",
    "modules/ihk.ko": "ihk.ko", "modules/ihk-smp-x86_64.ko": "ihk-smp-x86_64.ko",
    "modules/mcctrl.ko": "mcctrl.ko",
}
OVERLAY_MEMBERS = ("apps", "case", "case/work", "init", "apps/app", "bin/mcexec")
MAP_FIELDS = ("mode", "uid", "gid", "nlink", "mtime", "size", "sha256", "rdevmajor", "rdevminor")
IDENTITY_FIELDS = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                   "st_size", "st_mtime_ns", "st_ctime_ns")


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


def _identity(path):
    st = os.stat(path, follow_symlinks=False)
    return {key: getattr(st, key) for key in IDENTITY_FIELDS}


def _staging(obj, artifacts, modules):
    _keys(obj, ("base_initramfs", "derived_initramfs", "collector", "overlay_source", "overlay_manifest"))
    refs = {name: _ref(obj[name], name) for name in obj}
    _need(refs["base_initramfs"] == artifacts["initramfs"], "base initramfs join")
    _need(refs["base_initramfs"]["path"] != refs["derived_initramfs"]["path"] and
          refs["base_initramfs"]["sha256"] != refs["derived_initramfs"]["sha256"],
          "derived initramfs must differ from base")
    raw = Path(refs["overlay_manifest"]["path"]).read_bytes()
    _need(hashlib.sha256(raw).hexdigest() == refs["overlay_manifest"]["sha256"],
          "overlay manifest changed during read")
    _need(len(raw) <= MAX_JSON, "overlay manifest too large")
    try:
        overlay = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError, DiagnosticError) as exc:
        raise DiagnosticError("malformed overlay manifest") from exc
    _keys(overlay, ("base_cpio_sha256", "base_cpio_size", "base_sha256", "collector_sha256",
                    "final_map", "output_identity", "output_sha256", "overlay_sha256",
                    "payload_sha256", "mcexec_sha256", "size", "sources"))
    _need(type(overlay["base_cpio_size"]) is int and overlay["base_cpio_size"] > 0 and
          type(overlay["base_cpio_sha256"]) is str and SHA.fullmatch(overlay["base_cpio_sha256"]) and
          type(overlay["overlay_sha256"]) is str and SHA.fullmatch(overlay["overlay_sha256"]),
          "overlay archive metadata")
    _need(overlay["base_sha256"] == refs["base_initramfs"]["sha256"] and
          overlay["collector_sha256"] == refs["collector"]["sha256"] and
          overlay["payload_sha256"] == artifacts["payload"]["sha256"] and
          overlay["mcexec_sha256"] == artifacts["mcexec"]["sha256"] and
          overlay["output_sha256"] == refs["derived_initramfs"]["sha256"] and
          overlay["size"] == refs["derived_initramfs"]["size"], "overlay identity join")
    _keys(overlay["sources"], ("base", "collector", "payload", "mcexec"))
    for source, ref in (("base", refs["base_initramfs"]), ("collector", refs["collector"]),
                        ("payload", artifacts["payload"]), ("mcexec", artifacts["mcexec"])):
        row = overlay["sources"][source]
        _keys(row, ("path", "sha256", "identity"))
        _keys(row["identity"], IDENTITY_FIELDS)
        _need(row["path"] == ref["path"] and row["sha256"] == ref["sha256"] and
              row["identity"] == _identity(ref["path"]), "overlay source join " + source)
    _keys(overlay["output_identity"], IDENTITY_FIELDS)
    _need(overlay["output_identity"] == _identity(refs["derived_initramfs"]["path"]),
          "overlay output identity")
    final = overlay["final_map"]
    _need(isinstance(final, dict), "overlay final map")
    names = {**{name: artifacts[name] for name in ("mcexec", "native_boot", "loader", "libc", "mckernel_image", "payload")},
             "collector": refs["collector"], **dict(zip(MODULE_NAMES, modules))}
    for member, source in FINAL_MEMBERS.items():
        _need(member in final, "missing final member " + member)
        row = final[member]
        _keys(row, MAP_FIELDS)
        ref = names[source]
        expected_mode = stat.S_IFREG | 0o755 if member in ("init", "apps/app") else ref["mode"]
        _need(row["sha256"] == ref["sha256"] and row["size"] == ref["size"] and
              row["mode"] == expected_mode, "final member join " + member)
    for member in OVERLAY_MEMBERS:
        _need(member in final, "missing overlay member " + member)
    for member in ("apps", "case", "case/work"):
        row = final[member]
        _keys(row, MAP_FIELDS)
        _need(row["mode"] == stat.S_IFDIR | 0o755 and row["size"] == 0 and
              row["sha256"] == hashlib.sha256(b"").hexdigest(), "overlay directory " + member)
    return refs


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
    return _validate_manifest(obj)


def _validate_manifest(obj):
    _keys(obj, ("schema_version", "kind", "case_id", "artifacts", "modules", "profile", "payload", "staging"))
    _need(type(obj["schema_version"]) is int and obj["schema_version"] == 1 and obj["kind"] == "native-diagnostic-manifest", "manifest identity")
    _need(isinstance(obj["case_id"], str) and obj["case_id"] and "\0" not in obj["case_id"], "case_id")
    _keys(obj["artifacts"], ARTIFACTS)
    bound = {name: _ref(obj["artifacts"][name], name) for name in ARTIFACTS}
    _need(isinstance(obj["modules"], list) and len(obj["modules"]) == 3, "exactly three modules")
    modules = [_ref(ref, "module") for ref in obj["modules"]]
    _need(tuple(Path(ref["path"]).name for ref in modules) == MODULE_NAMES, "module inventory")
    staging = _staging(obj["staging"], bound, modules)
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
            "modules": modules, "staging": staging,
            "profile": {"memory_mib": 8192, "vcpus": 4, "numa_nodes": 2, "append": append},
            "payload": dict(payload)}


def _freeze(value):
    """Own an immutable, strictly typed copy, with no caller-owned containers."""
    if type(value) is dict:
        _need(all(type(key) is str for key in value), "plan keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    _need(type(value) in (str, int, bool, type(None)), "unsupported plan value")
    return value


def _thaw(value):
    if type(value) is MappingProxyType:
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _same_plan(left, right):
    # bool/int equality must not admit a changed type in a bound contract.
    if type(left) is not type(right):
        return False
    if type(left) is MappingProxyType:
        return left.keys() == right.keys() and all(_same_plan(left[k], right[k]) for k in left)
    if type(left) is tuple:
        return len(left) == len(right) and all(_same_plan(a, b) for a, b in zip(left, right))
    return left == right


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
        record_failure(attempt, exc, "prepare")
        raise
    return attempt


def build_command(manifest, attempt):
    """Return the exact QEMU argv only after the derived-image join is READY."""
    attempt = Path(attempt)
    _need(attempt.is_dir() and (attempt.stat().st_mode & 0o777) == 0o700, "attempt not private")
    manifest = _validate_manifest(_thaw(_freeze(manifest)))
    a = manifest["artifacts"]
    qmp = str(attempt / "qmp.sock")
    _need(not os.path.lexists(qmp), "stale QMP socket")
    for name in ("serial.log", "debugcon.log"):
        path = attempt / name
        _need(path.exists() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode),
              "invalid capture path: " + name)
    for name in ("qemu.stdout", "qemu.stderr", "qmp.transcript.json", "result.json", "first-failure.jsonl"):
        _need(not os.path.lexists(attempt / name), "stale diagnostic output: " + name)
    argv = expected_qemu_argv(manifest, attempt)
    overlay = {"modules": [m["path"] for m in manifest["modules"]], "mckernel_image": a["mckernel_image"]["path"],
               "mcexec": a["mcexec"]["path"], "payload": a["payload"]["path"], "load_modules": list(MODULE_NAMES),
               "boot_contract": "native-boot-v1", "guest_destinations": {"/images/mckernel.img": a["mckernel_image"]["path"],
               "/bin/mcexec": a["mcexec"]["path"], "/apps/app": a["payload"]["path"]},
               "init_sequence": ["insmod /modules/ihk.ko", "insmod /modules/ihk-smp-x86_64.ko ihk_trampoline=524288",
                                 "insmod /modules/mcctrl.ko", "/bin/native-boot", "cd /case/work"],
               "transport": "guest collector framed serial report; never QEMU stdout"}
    return _freeze({"argv": argv, "overlay": overlay, "payload": manifest["payload"], "qmp_socket": qmp,
                    "runtime_ready": True, "staging": manifest["staging"], "manifest": manifest})


def expected_qemu_argv(manifest, attempt):
    """Derive the exact command from an already validated manifest and path.

    This pure helper intentionally does not inspect generated output paths, so
    the outer owner can retain the admitted argv before the inner run creates
    qemu.stdout/qemu.stderr and makes build_command correctly reject staleness.
    """
    attempt = Path(attempt)
    _need(attempt.is_absolute(), "attempt path")
    manifest = _validate_manifest(_thaw(_freeze(manifest)))
    a = manifest["artifacts"]
    qmp = str(attempt / "qmp.sock")
    return [QEMU, "-machine", "q35", "-accel", "tcg,thread=multi", "-cpu", "max,la57=off",
            "-smp", "4,sockets=2,cores=2,threads=1", "-m", "8192",
            "-object", "memory-backend-ram,size=4G,id=ram-node0",
            "-object", "memory-backend-ram,size=4G,id=ram-node1",
            "-numa", "node,nodeid=0,cpus=0-1,memdev=ram-node0",
            "-numa", "node,nodeid=1,cpus=2-3,memdev=ram-node1",
            "-nic", "none", "-display", "none", "-no-reboot", "-no-shutdown", "-S", "-monitor", "none",
            "-qmp", "unix:" + qmp + ",server=on,wait=off", "-serial", "file:" + str(attempt / "serial.log"),
            "-debugcon", "file:" + str(attempt / "debugcon.log"), "-global", "isa-debugcon.iobase=0xe9",
            "-kernel", a["bzImage"]["path"], "-initrd", manifest["staging"]["derived_initramfs"]["path"], "-append", APPEND]


def _validate_qemu_evidence(evidence, admitted_argv=None):
    _keys(evidence, ("argv", "pid", "pgid", "sid", "starttime_ticks", "returncode"))
    _need(type(evidence["argv"]) is list and evidence["argv"] and
          all(type(item) is str for item in evidence["argv"]), "QEMU evidence argv")
    if admitted_argv is not None:
        _need(type(admitted_argv) is tuple and admitted_argv and
              all(type(item) is str for item in admitted_argv), "admitted QEMU argv")
        _need(tuple(evidence["argv"]) == admitted_argv,
              "QEMU evidence argv/admitted command mismatch")
    _need(all(type(evidence[name]) is int for name in
              ("pid", "pgid", "sid", "starttime_ticks", "returncode")),
          "QEMU evidence identity/status types")
    _need(evidence["pid"] == evidence["pgid"] == evidence["sid"] and
          evidence["pid"] > 0 and evidence["starttime_ticks"] > 0,
          "QEMU evidence process identity")


def evaluate(manifest, observation):
    """Validate serial evidence shape; PROTOCOL_PASS is not guest acceptance."""
    observation_keys = ("serial", "debugcon", "qmp", "teardown", "started_at", "finished_at", "deadline",
                        "process_identity")
    if "qemu_evidence" in observation:
        observation_keys += ("qemu_evidence",)
    _keys(observation, observation_keys)
    if "qemu_evidence" in observation:
        _validate_qemu_evidence(observation["qemu_evidence"])
    identity = observation["process_identity"]
    _keys(identity, ("pid", "pgid", "sid", "starttime_ticks"))
    _need(all(type(identity[name]) is int and identity[name] > 0
              for name in ("pid", "pgid", "sid", "starttime_ticks")),
          "invalid process identity types")
    _need(identity["pid"] == identity["pgid"] == identity["sid"],
          "process group/session identity mismatch")
    if "qemu_evidence" in observation:
        evidence_identity = {name: observation["qemu_evidence"][name]
                             for name in ("pid", "pgid", "sid", "starttime_ticks")}
        _need(evidence_identity == identity, "QEMU evidence/observation identity mismatch")
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
            "guest_report": report, "observation": observation, "runtime_blocker": DIAGNOSTIC_LIMITATION}


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


def run_diagnostic(manifest, attempt, process_factory=None, qmp_factory=None, timeout=300,
                   expected_plan=None):
    """Exercise only explicit injected factories after the staging join."""
    try:
        _need(process_factory is not None and qmp_factory is not None and
              callable(process_factory) and callable(qmp_factory), "explicit diagnostic factories required")
        plan = build_command(manifest, attempt)
        if expected_plan is not None:
            _need(_same_plan(plan, expected_plan),
                  "diagnostic build plan changed after factory binding")
        _need(plan["runtime_ready"] is True, STAGING_BLOCKER)
    except BaseException as exc:
        record_failure(attempt, exc, "staging")
        raise
    # The lifecycle/evaluator own their own validated snapshot too: neither a
    # factory closure nor the caller can change the oracle through an alias.
    args = (_thaw(plan["manifest"]), attempt, process_factory, qmp_factory, timeout)
    # The reviewed runner supplies its frozen plan back as expected_plan. Unit
    # injection remains useful for lifecycle mechanics without pretending a
    # synthetic Process object is an admitted QEMU command.
    if expected_plan is not None:
        return exercise_lifecycle(*args, admitted_argv=tuple(plan["argv"]))
    return exercise_lifecycle(*args)


def _failure(exc, phase):
    """Total metadata conversion: reporting must never abort retirement.

    Do not dispatch on exception attributes, str/repr, or custom metaclasses.
    Unknown metadata uses literals. Read args through the built-in descriptor,
    and render only bounded exact primitives; a timer cannot make arbitrary
    formatting safe. Keep the original exception separately from this record.
    """
    fallback = {"phase": phase if type(phase) is str else "failure",
                "type": "BaseException", "error": "<exception metadata unavailable>"}
    try:
        cls = type(exc)
        if type(cls) is not type:
            return fallback
        name = type.__getattribute__(cls, "__name__")
        parts = []
        for arg in BaseException.args.__get__(exc)[:4]:
            if type(arg) is str:
                parts.append(arg[:2048])
            elif type(arg) is int and arg.bit_length() <= 64:
                parts.append(str(arg))
            elif arg is None or type(arg) is bool:
                parts.append(str(arg))
            else:
                parts.append("<exception argument omitted>")
        return {"phase": fallback["phase"], "type": name,
                "error": ": ".join(parts) or "<no exception message>"}
    except BaseException:
        return fallback


def failure_text(exc):
    return _failure(exc, "reporting")["error"]


def record_failure(attempt, exc, phase, *, writer=None):
    """Best effort terminal evidence; never mask the authoritative exception.

    If the main-thread timer cannot be exclusively acquired, do not call the
    writer. In particular, an ambient deadline is never stolen or treated as
    our own bound. No unbounded publication fallback is permitted.
    """
    try:
        with _alarm(time.monotonic() + 2):
            failure = _failure(exc, phase)
            record = {"status": "BLOCKED", "application_acceptance": False,
                      "mckernel_application_executed": False, "failure": failure}
            (write_record if writer is None else writer)(attempt, record, failure)
    except BaseException:
        pass


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
    try:
        signal.setitimer(signal.ITIMER_REAL, remaining)
        yield remaining
        _need(time.monotonic() < deadline, "late completion")
    finally:
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
        finally:
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
    original = None
    def step(label, owner, name, allowance=1, accepts_timeout=True):
        nonlocal original
        try:
            return _method(min(deadline, time.monotonic() + allowance), owner, name,
                           accepts_timeout=accepts_timeout)
        except BaseException as exc:
            if original is None:
                original = exc
            errors.append(_failure(exc, label))
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
    return {"reaped": reaped, "errors": errors}, original


def _acquisition_failure_evidence(exc):
    """Copy only the primitive evidence attached by the backend recovery."""
    try:
        value = object.__getattribute__(exc, "_mckernel_qemu_acquisition_evidence")
    except BaseException:
        return None
    if type(value) is not dict or set(value) != {
            "argv", "pid", "pgid", "sid", "starttime_ticks", "identity_complete",
            "reaped", "returncode"}:
        return None
    if (type(value["argv"]) is not list or not value["argv"] or
            any(type(item) is not str for item in value["argv"]) or
            type(value["identity_complete"]) is not bool or type(value["reaped"]) is not bool):
        return None
    for name in ("pid", "pgid", "sid", "starttime_ticks", "returncode"):
        if value[name] is not None and type(value[name]) is not int:
            return None
    if value["reaped"] != (type(value["returncode"]) is int):
        return None
    return {name: value[name] if name != "argv" else list(value[name]) for name in value}


def _acquisition_original(exc):
    """Read a trusted carrier's original exception without user hooks."""
    try:
        original = object.__getattribute__(exc, "_mckernel_acquisition_original")
    except BaseException:
        return None
    return original if isinstance(original, BaseException) else None


def exercise_lifecycle(manifest, attempt, process_factory, qmp_factory, timeout=300, *, admitted_argv=None):
    """Injected-backend lifecycle exercise; never reports guest acceptance.

    This entry point grants no execution release. QMP/backend methods accept a
    remaining timeout; an independent SIGALRM bounds ignored timeout arguments.
    """
    process = qmp = None
    failure = None
    original = None
    observation = {}
    acquisition_failure = None
    if admitted_argv is not None:
        _need(type(admitted_argv) is tuple and admitted_argv and
              all(type(item) is str for item in admitted_argv), "admitted QEMU argv")
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
        carried_original = _acquisition_original(exc)
        original = carried_original if carried_original is not None else exc
        failure = _failure(original, "lifecycle")
        acquisition_failure = _acquisition_failure_evidence(exc)
    finally:
        # No filesystem journal or capture runs before retirement: blocked
        # storage cannot delay termination/reaping after a QMP failure.
        cleanup, cleanup_original = _cleanup(process, qmp)
        if acquisition_failure is not None and not acquisition_failure["reaped"]:
            cleanup["reaped"] = False
            cleanup["errors"].append({"phase": "acquisition-retirement", "type": "DiagnosticError",
                                      "error": "QEMU acquisition child was not exactly reaped"})
        if original is None:
            original = cleanup_original
    # Retain controls and host streams after teardown even if a lifecycle or
    # cleanup operation failed. Evidence capture has its own bounded deadline;
    # the original error keeps priority over any later capture/evaluation error.
    capture_errors = []
    qemu_evidence_error = None
    qemu_evidence = None
    # Process evidence is first and has its own budget. QMP transcript and
    # host streams get independent fresh budgets: a timeout in one class must
    # not consume another class's evidence opportunity.
    if process is not None and cleanup["reaped"]:
        try:
            with _alarm(time.monotonic() + 2):
                evidence_getter = getattr(process, "qemu_evidence", None)
                _need(callable(evidence_getter), "QEMU evidence accessor unavailable")
                candidate = evidence_getter()
                _need(type(candidate) is dict, "QEMU evidence record type")
                _validate_qemu_evidence(candidate, admitted_argv)
                qemu_evidence = candidate
        except BaseException as exc:
            qemu_evidence_error = _failure(exc, "qemu-evidence")
            capture_errors.append(qemu_evidence_error)
            # This capture is first after exact reaping. Retain its actual
            # exception now, before QMP/host evidence continues independently.
            if original is None:
                original = exc
                failure = dict(qemu_evidence_error)
    elif process is not None:
        error = RuntimeError("QEMU process was not exactly reaped")
        qemu_evidence_error = _failure(error, "qemu-evidence")
        capture_errors.append(qemu_evidence_error)
    if qmp is not None:
        try:
            with _alarm(time.monotonic() + 2):
                session = getattr(qmp, "session", None)
                transcript = getattr(session, "transcript", []) if session is not None else []
                raw = json.dumps(transcript, sort_keys=True, allow_nan=False).encode("utf-8")
                _need(len(raw) <= 24 * 1024 * 1024, "QMP transcript capture limit")
                with (Path(attempt) / "qmp.transcript.json").open("xb") as stream:
                    stream.write(raw)
        except BaseException as exc:
            if original is None:
                original = exc
            capture_errors.append(_failure(exc, "qmp-transcript"))
    if process is not None and cleanup["reaped"]:
        try:
            host_stdout, host_stderr = _method(time.monotonic() + 2, process, "communicate")
            _need(type(host_stdout) is bytes and type(host_stderr) is bytes, "backend log types")
            for name, data in (("qemu.stdout", host_stdout), ("qemu.stderr", host_stderr)):
                path = Path(attempt) / name
                if not os.path.lexists(path):
                    with _alarm(time.monotonic() + 2):
                        with path.open("xb") as stream:
                            stream.write(data[:MAX_JSON + 1])
            _need(len(host_stdout) <= MAX_JSON and len(host_stderr) <= MAX_JSON, "host capture limit exceeded")
        except BaseException as exc:
            if original is None:
                original = exc
            capture_errors.append(_failure(exc, "host-capture"))
    if failure is None:
        if cleanup["errors"] or not cleanup["reaped"]:
            failure = {"phase": "cleanup", "type": "DiagnosticError", "error": "teardown uncertain"}
        else:
            non_evidence = [item for item in capture_errors if item is not qemu_evidence_error]
            if non_evidence:
                failure = dict(non_evidence[0])
    if failure is None:
        try:
            with _alarm(deadline):
                texts = {}
                for name in ("serial", "debugcon"):
                    with (Path(attempt) / (name + ".log")).open("rb") as stream:
                        data = stream.read(MAX_JSON + 1)
                    _need(len(data) <= MAX_JSON, "capture limit exceeded")
                    texts[name] = data.decode("utf-8", errors="strict")
                identity_getter = getattr(process, "process_identity", None)
                _need(callable(identity_getter), "process identity unavailable")
                process_identity = identity_getter()
                observation = dict(texts, qmp=terminal, teardown=True, started_at=started,
                                   finished_at=time.monotonic(), deadline=deadline,
                                   process_identity=process_identity)
                if qemu_evidence is not None:
                    observation["qemu_evidence"] = qemu_evidence
                record = evaluate(manifest, observation)
        except BaseException as exc:
            original = exc
            failure = _failure(exc, "evaluation")
    if failure is None and qemu_evidence_error is not None:
        failure = dict(qemu_evidence_error)
    if failure is not None:
        record = {"status": "FAIL", "application_acceptance": False,
                  "mckernel_application_executed": False, "failure": failure}
    record["cleanup"] = cleanup
    record["capture_errors"] = capture_errors
    if qemu_evidence is not None:
        record["qemu_evidence"] = qemu_evidence
    if admitted_argv is not None:
        record["admitted_qemu_argv"] = list(admitted_argv)
    if acquisition_failure is not None:
        record["qemu_acquisition_failure"] = {"evidence": acquisition_failure,
                                               "failure": _failure(original, "acquisition")}
    # The first observed failure survives cleanup failures; journal only after
    # retirement, under its own bounded publication deadline.
    try:
        with _alarm(time.monotonic() + 2):
            write_record(attempt, record, failure)
    except BaseException:
        if failure is None:
            raise
    if failure is not None:
        # isinstance may consult an exception's user-defined __class__
        # property. Classify its actual type without touching the instance.
        if original is not None and not issubclass(type(original), Exception):
            raise original
        raise DiagnosticError(failure["error"]) from original
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
