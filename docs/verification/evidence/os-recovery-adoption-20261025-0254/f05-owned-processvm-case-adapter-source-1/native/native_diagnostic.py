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
PROFILE_RETAINED = "native-diagnostic-4vcpu-8192mib"
PROFILE_SMALL = "native-diagnostic-2vcpu-6144mib"
PROFILE_DUAL = "native-diagnostic-4vcpu-6144mib"
# The launcher prefix is part of the reviewed wire contract.  The tail is
# deliberately bounded rather than frozen so the same manifest validator can
# describe startup and the four core-mode payloads.
PAYLOAD_ARGV_PREFIX = ("/bin/mcexec", "-t", "1", "0")
PAYLOAD_PATHS = ("app", "/apps/app")
PAYLOAD_ARGC_MAX = 32
PAYLOAD_ARG_BYTES_MAX = 256
PAYLOAD_ARGV_BYTES_MAX = 2048
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


def _validate_payload_argv(argv):
    """Validate the bounded mcexec payload argv without normalising it."""
    _need(type(argv) is list and argv, "payload argv must be a non-empty list")
    _need(len(argv) <= PAYLOAD_ARGC_MAX, "payload argv argc limit")
    _need(tuple(argv[:len(PAYLOAD_ARGV_PREFIX)]) == PAYLOAD_ARGV_PREFIX and
          len(argv) > len(PAYLOAD_ARGV_PREFIX) and
          argv[len(PAYLOAD_ARGV_PREFIX)] in PAYLOAD_PATHS,
          "payload argv prefix/path")
    encoded = 0
    for item in argv:
        _need(type(item) is str and "\0" not in item, "payload argv item")
        try:
            size = len(item.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise DiagnosticError("payload argv item UTF-8") from exc
        _need(size <= PAYLOAD_ARG_BYTES_MAX, "payload argv argument byte limit")
        encoded += size
    _need(encoded <= PAYLOAD_ARGV_BYTES_MAX, "payload argv total byte limit")
    return argv


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
    _need(isinstance(obj["profile"], dict) and set(obj["profile"]) <= {"name", "memory_mib", "vcpus", "numa_nodes", "append"}
          and {"memory_mib", "vcpus", "numa_nodes"} <= set(obj["profile"]), "profile keys")
    profile = obj["profile"]
    _need(all(type(profile[k]) is int for k in ("memory_mib", "vcpus", "numa_nodes")), "profile types")
    name = profile.get("name", PROFILE_RETAINED)
    _need(type(name) is str and name in (PROFILE_RETAINED, PROFILE_SMALL, PROFILE_DUAL), "profile name")
    expected = {PROFILE_RETAINED: (8192, 4, 2), PROFILE_SMALL: (6144, 2, 1),
                PROFILE_DUAL: (6144, 4, 2)}[name]
    _need((profile["memory_mib"], profile["vcpus"], profile["numa_nodes"]) == expected, "profile differs")
    append = profile.get("append", APPEND)
    _need(append == APPEND, "kernel append differs from retained profile")
    _keys(obj["payload"], ("cwd", "argv", "env", "oracle", "stdout_limit_bytes", "stderr_limit_bytes"))
    payload = obj["payload"]
    _need(payload["cwd"] == "/case/work", "payload cwd")
    _validate_payload_argv(payload["argv"])
    _need(payload["env"] == {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"}, "frozen environment")
    oracle = payload["oracle"]
    _need(set(oracle) in ({"stdout_hex", "stderr_hex", "exit_code"},
                          {"stdout_hex", "stderr_hex", "exit_code", "stderr_typed"}),
          "manifest keys differ")
    _need(type(oracle["stdout_hex"]) is str and re.fullmatch(r"(?:[0-9a-fA-F]{2})*", oracle["stdout_hex"]), "oracle stdout")
    _need(type(oracle["stderr_hex"]) is str and re.fullmatch(r"(?:[0-9a-fA-F]{2})*", oracle["stderr_hex"]), "oracle stderr")
    _need(type(oracle["exit_code"]) is int and not isinstance(oracle["exit_code"], bool) and 0 <= oracle["exit_code"] <= 255, "oracle exit")
    if "stderr_typed" in oracle:
        _validate_typed_stderr_oracle(oracle["stderr_typed"])
        _need(oracle["stderr_hex"] == "", "typed stderr cannot also freeze bytes")
    for stream_name in ("stdout", "stderr"):
        limit = payload[stream_name + "_limit_bytes"]
        _need(type(limit) is int and 0 <= limit <= MAX_JSON and len(bytes.fromhex(oracle[stream_name + "_hex"])) <= limit, "stream limit")
    return {"schema_version": 1, "kind": obj["kind"], "case_id": obj["case_id"], "artifacts": bound,
            "modules": modules, "staging": staging,
            "profile": {"name": name, "memory_mib": expected[0], "vcpus": expected[1],
                        "numa_nodes": expected[2], "append": append},
            "payload": dict(payload)}


_FUTEX_CASES = (
    ("wait_mismatch", -1, 11), ("wait_relative_zero", -1, 110),
    ("wait_relative_10ms", -1, 110), ("wait_bitset_expired", -1, 110),
    ("wait_bitset_future", -1, 110), ("wait_null_word", -1, 14),
    ("wait_unaligned_word", -1, 22), ("timeout_protected", -1, 14),
    ("timeout_cross_page", -1, 14), ("timeout_negative_seconds", -1, 22),
    ("timeout_negative_nanoseconds", -1, 22), ("timeout_large_nanoseconds", -1, 22),
    ("wait_bitset_zero", -1, 22), ("wake_empty", 0, 0),
    ("wake_unmapped_private", 0, 0), ("wait_relative_runnable", -1, 110),
)
_FUTEX_MAX_NS = 2_000_000_000
_FUTEX_MAX_I64 = (1 << 63) - 1
_FUTEX_MAX_PID = (1 << 31) - 1


def _validate_typed_stderr_oracle(oracle):
    """Validate the dynamic, line-oriented native-ultra-futex contract."""
    _keys(oracle, ("kind", "record_order", "line_count", "case_ids", "thread_count", "clone"))
    _need(oracle["kind"] == "native-ultra-futex-v1", "typed stderr kind")
    _need(oracle["record_order"] in ("current-source-v1", "historical-split-v1"),
          "typed stderr record order")
    _need(type(oracle["line_count"]) is int and oracle["line_count"] == 18,
          "typed stderr line count")
    _need(oracle["case_ids"] == [row[0] for row in _FUTEX_CASES], "typed stderr cases")
    _need(type(oracle["thread_count"]) is int and oracle["thread_count"] == 2,
          "typed stderr thread count")
    _need(oracle["clone"] is True, "typed stderr clone requirement")


def _check_typed_futex_stderr(data, oracle):
    """Check stable meanings while allowing timestamps, counts and TIDs to vary."""
    _validate_typed_stderr_oracle(oracle)
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise DiagnosticError("typed stderr is not ASCII") from exc
    lines = text.splitlines(keepends=True)
    _need(len(lines) == oracle["line_count"] and all(line.endswith("\n") for line in lines),
          "typed stderr framing")
    case_re = re.compile(r"^NATIVE_ULTRA_FUTEX_CASE id=([a-z0-9_]+) result=(-?[0-9]+) "
                         r"errno=([0-9]+) elapsed_ns=([0-9]+) before_ns=([0-9]+) "
                         r"after_ns=([0-9]+) deadline_ns=([0-9]+)\n$")
    def u64(value, label):
        parsed = int(value)
        _need(0 <= parsed <= _FUTEX_MAX_I64, label + " signed range")
        return parsed
    case_count = 16 if oracle["record_order"] == "current-source-v1" else 15
    for line, expected in zip(lines[:case_count], _FUTEX_CASES[:case_count]):
        match = case_re.fullmatch(line)
        _need(match is not None, "typed futex case framing")
        case, result, errno_value, elapsed, before, after, deadline = match.groups()
        _need((case, int(result), int(errno_value)) == expected, "typed futex case result")
        elapsed_i, before_i, after_i, deadline_i = (u64(elapsed, "typed futex elapsed"),
                                                    u64(before, "typed futex before"),
                                                    u64(after, "typed futex after"),
                                                    u64(deadline, "typed futex deadline"))
        minimum = 9_000_000 if case in ("wait_relative_10ms", "wait_relative_runnable") else 0
        _need(elapsed_i == after_i - before_i and minimum <= elapsed_i <= _FUTEX_MAX_NS,
              "typed futex case timing")
        if case == "wait_bitset_future":
            _need(deadline_i > 0 and after_i >= deadline_i - 1_000_000,
                  "typed futex future deadline")
        else:
            _need(deadline_i == 0, "typed futex unexpected deadline")
    clone_re = re.compile(r"^NATIVE_ULTRA_FUTEX_CLONE parent_tid=([1-9][0-9]*) "
                          r"child_tid=([1-9][0-9]*) entry_tid=([1-9][0-9]*) "
                          r"stored_tid=([1-9][0-9]*) cleared_tid=0 entered=1 wait_calls=([0-9]+) "
                          r"elapsed_ns=([0-9]+) flags=([0-9a-f]+) stack_bytes=262144\n$")
    clone_index = 17 if oracle["record_order"] == "current-source-v1" else 15
    thread_index = 16 if oracle["record_order"] == "current-source-v1" else 17
    match = clone_re.fullmatch(lines[clone_index])
    _need(match is not None, "typed futex clone framing")
    clone_parent, child, entry, stored, wait_calls, clone_elapsed, flags = match.groups()
    _need(0 <= int(wait_calls) <= 256 and flags == "1250f00",
          "typed futex clone fields")
    thread_re = re.compile(r"^NATIVE_ULTRA_FUTEX_THREADS joined=2 parent_tid=([1-9][0-9]*) "
                           r"tid0=([1-9][0-9]*) tid1=([1-9][0-9]*) count0=([1-9][0-9]*) "
                           r"count1=([1-9][0-9]*) token0=1 token1=2 stack_bytes=262144 "
                           r"elapsed_ns=([0-9]+)\n$")
    match = thread_re.fullmatch(lines[thread_index])
    _need(match is not None, "typed futex thread framing")
    parent, tid0, tid1, count0, count1, thread_elapsed = map(int, match.groups())
    _need(all(1 <= value <= _FUTEX_MAX_PID for value in (parent, tid0, tid1)) and
          len({parent, tid0, tid1}) == 3 and int(count0) > 0 and int(count1) > 0 and
          all(1 <= value < 20_000_000 for value in (int(count0), int(count1))) and
          thread_elapsed <= 6_000_000_000,
          "typed futex thread identities")
    _need(all(1 <= int(value) <= _FUTEX_MAX_PID for value in
              (clone_parent, child, entry, stored)) and
          int(clone_parent) == parent and int(child) == int(entry) == int(stored) and
          int(child) != int(clone_parent) and 0 <= int(clone_elapsed) <= _FUTEX_MAX_NS,
          "typed futex clone identities")
    if oracle["record_order"] == "historical-split-v1":
        # The historical fixture split the final CASE after CLONE.
        match = case_re.fullmatch(lines[16])
        _need(match is not None and match.group(1) == "wait_relative_runnable" and
              (int(match.group(2)), int(match.group(3))) == _FUTEX_CASES[15][1:],
              "typed futex final case")
        _, _, _, elapsed, before, after, deadline = match.groups()
        elapsed_i, before_i, after_i, deadline_i = (u64(elapsed, "typed futex final elapsed"),
                                                    u64(before, "typed futex final before"),
                                                    u64(after, "typed futex final after"),
                                                    u64(deadline, "typed futex final deadline"))
        _need(elapsed_i == after_i - before_i and 9_000_000 <= elapsed_i <= _FUTEX_MAX_NS and
              deadline_i == 0,
              "typed futex final case timing")


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


def _qmp_socket_path(attempt):
    """Linux sun_path reserves one of its 108 bytes for the trailing NUL."""
    path = str(Path(attempt) / "qmp.sock")
    _need(len(os.fsencode(path)) <= 107, "QMP socket pathname exceeds Linux AF_UNIX 107-byte limit")
    return path


def build_command(manifest, attempt):
    """Return the exact QEMU argv only after the derived-image join is READY."""
    attempt = Path(attempt)
    _need(attempt.is_dir() and (attempt.stat().st_mode & 0o777) == 0o700, "attempt not private")
    manifest = _validate_manifest(_thaw(_freeze(manifest)))
    a = manifest["artifacts"]
    qmp = _qmp_socket_path(attempt)
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
    qmp = _qmp_socket_path(attempt)
    if manifest["profile"]["name"] == PROFILE_SMALL:
        profile_args = ["-smp", "2,sockets=1,cores=2,threads=1", "-m", "6144",
                        "-object", "memory-backend-ram,size=6G,id=ram-node0",
                        "-numa", "node,nodeid=0,cpus=0-1,memdev=ram-node0"]
    elif manifest["profile"]["name"] == PROFILE_DUAL:
        profile_args = ["-smp", "4,sockets=2,cores=2,threads=1", "-m", "6144",
                        "-object", "memory-backend-ram,size=3G,id=ram-node0",
                        "-object", "memory-backend-ram,size=3G,id=ram-node1",
                        "-numa", "node,nodeid=0,cpus=0-1,memdev=ram-node0",
                        "-numa", "node,nodeid=1,cpus=2-3,memdev=ram-node1"]
    else:
        profile_args = ["-smp", "4,sockets=2,cores=2,threads=1", "-m", "8192",
                        "-object", "memory-backend-ram,size=4G,id=ram-node0",
                        "-object", "memory-backend-ram,size=4G,id=ram-node1",
                        "-numa", "node,nodeid=0,cpus=0-1,memdev=ram-node0",
                        "-numa", "node,nodeid=1,cpus=2-3,memdev=ram-node1"]
    return [QEMU, "-machine", "q35", "-accel", "tcg,thread=multi", "-cpu", "max,la57=off",
            *profile_args,
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
        typed = manifest["payload"]["oracle"].get("stderr_typed") if name == "stderr" else None
        if typed is not None:
            _check_typed_futex_stderr(data, typed)
        else:
            _need(data == bytes.fromhex(manifest["payload"]["oracle"][name + "_hex"]), "wrong payload bytes")
    schedules = re.findall(r"application SCHEDULE os=0 generation=1 pid=(\d+) cpu=0\b", serial)
    _need(len(schedules) == 1, "guest scheduling evidence")
    prefix = r"os=0 generation=1 pid=" + schedules[0]
    lifecycle_patterns = () if _begin_cleanup_enabled(manifest) else (
        r"application retirement " + prefix + r" token=\d+ errno=0\b",
        r"application_process=release " + prefix + r" cleanup_errno=0\b")
    for pattern in (*lifecycle_patterns,
                    *[r"application procfs " + op + " " + prefix + " tid=" + schedules[0] + r"\b"
                      for op in ("published", "deleted")]):
        _need(len(re.findall(pattern, serial)) == 1, "retirement/release evidence")
    _check_syscall_trace(serial, prefix, _begin_cleanup_enabled(manifest), _begin_process_case(manifest))
    return {"schema_version": 1, "kind": "native-diagnostic-result", "case_id": manifest["case_id"],
            "status": "PROTOCOL_PASS", "application_acceptance": False, "mckernel_application_executed": False,
            "guest_report": report, "observation": observation, "runtime_blocker": DIAGNOSTIC_LIMITATION}


def _check_syscall_trace(serial, prefix, begin_cleanup=False, child_domain=False):
    """Join every sampled delivery; exit_group deliberately has no RET.

    mcctrl_process.rs::return_syscall prints return_route only when the Linux
    worker slot differs from the saved guest CPU, before printing returned.
    mcexec.c::init_worker_threads allocates slots 0..n_threads inclusive: the
    frozen -t 1 invocation therefore permits slots 0 and 1, not host CPU IDs.
    The exit/exit_group branch (and Rust act_exit) retires without RET. This
    single-thread startup fixture requires one final exit_group (231).
    """
    if child_domain:
        serial, _ = _audit_begin_children(serial, prefix)
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
    if begin_cleanup:
        _check_begin_cleanup(serial, prefix, exit_position)
    else:
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


PAIR_CONTROL_QUEUE_BYTES=16384
"""Appended to the retained diagnostic module; original one-app path stays intact."""
_one_validate_manifest = _validate_manifest
_one_evaluate = evaluate
_one_build_command = build_command
PAIR_IMAGE_SHA = None # PENDING actual NEW205 image, never old03a/fixedFP fallback
PAIR_MODULE_SHAS = ('c396958bfdb0f22036b469ea2a64e0a6b188b9619ee4105c7879483bb3b9790d', 'af234fbcd09327a80e12396eebbfbcd30838f88a552fa13ba00a2728a761eeaa', '6571ac7eca13559d8bab65125d54facbbc65e84f815d4ff3fc77ec6aa1104972')

def pair_argv(i):
    return ["/bin/mcexec", "-t", "1", "-c", str(i), "0", "/apps/app"+str(i)]

def pair_env(i):
    return {"PATH":"/usr/bin:/bin", "COKERNEL_PATH":"/apps", "PAIR_CPU":str(i)}

def _validate_manifest(obj):
    if "pair" not in obj:
        return _one_validate_manifest(obj)
    round_case="pair_rounds" in obj
    if round_case:_need(type(obj["pair_rounds"]) is int and obj["pair_rounds"]==10,"fixed ten-round manifest")
    _need(set(obj)=={"schema_version","kind","case_id","artifacts","modules","profile","payload","staging","pair"}|({"pair_rounds"} if round_case else set()),"pair manifest keys")
    base=_one_validate_manifest({k:v for k,v in obj.items() if k not in ("pair","pair_rounds")})
    _need(base["profile"]["name"]==PROFILE_RETAINED,"pair retains4vCPU8192MiB envelope")
    import importlib.util
    module_spec=importlib.util.spec_from_file_location("exact_composite_module_binding",Path(__file__).resolve().parent/"composite_module_binding.py")
    module_binding=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module_binding)
    module_binding.validate_module_binding(base)
    p=obj["pair"]
    _keys(p,("version","os","generation","host_cpus","cpus","default_ikc_linux","apps","source_authority","inherited_overlay_manifest"))
    _need(type(p["version"]) is int and p["version"]==1 and type(p["os"]) is int and p["os"]==0 and type(p["generation"]) is int and p["generation"]==1,"pair OS identity")
    _need(p["host_cpus"]==[1,2] and p["cpus"]==[0,1] and type(p["default_ikc_linux"]) is int and p["default_ikc_linux"]==0,"pair CPU contract")
    authority=_ref(p["source_authority"],"NEW205 complete source/production authority")
    binding=json.loads(Path(authority["path"]).read_text(),object_pairs_hook=_pairs)
    import importlib.util
    authority_source=Path(__file__).resolve().parent/"repaired_image_authority.py"
    spec=importlib.util.spec_from_file_location("strict_repaired205_authority",authority_source)
    authority_consumer=importlib.util.module_from_spec(spec);spec.loader.exec_module(authority_consumer)
    authority_consumer.validate(binding,base["artifacts"]["mckernel_image"])
    inherited=_ref(p["inherited_overlay_manifest"],"inherited overlay")
    old=json.loads(Path(inherited["path"]).read_text(),object_pairs_hook=_pairs)["final_map"]
    final=json.loads(Path(base["staging"]["overlay_manifest"]["path"]).read_text(),object_pairs_hook=_pairs)["final_map"]
    _need(set(final)==set(old)|{"apps/app0","apps/app1"},"exact pair overlay membership")
    changed={n for n in old if old[n]!=final[n]}
    _need(changed <= {"init","apps/app","bin/native-boot","images/mckernel.img","modules/ihk.ko","modules/ihk-smp-x86_64.ko","modules/mcctrl.ko"},"only retained pair changes and exact composite module members")
    for n in old:
        _need({k:v for k,v in old[n].items() if k not in {"sha256","size"}}=={k:v for k,v in final[n].items() if k not in {"sha256","size"}},"retained metadata "+n)
    _need(type(p["apps"]) is list and len(p["apps"])==2,"exactly two apps")
    for i,a in enumerate(p["apps"]):
        _keys(a,("id","cpu","argv","cwd","env","payload","oracle","stdout_limit_bytes","stderr_limit_bytes","timeout_ms"))
        _need(type(a["id"]) is int and a["id"]==i and type(a["cpu"]) is int and a["cpu"]==i,"pair ordinal")
        _need(a["argv"]==pair_argv(i) and a["cwd"]=="/case/two-app/work"+str(i) and a["env"]==pair_env(i),"pair launch contract")
        payload=_ref(a["payload"],"pair payload")
        row=final["apps/app"+str(i)]
        _need(row["sha256"]==payload["sha256"] and row["size"]==payload["size"] and row["mode"]==stat.S_IFREG|0o755,"pair payload final member")
        _need(a["oracle"]=={"stdout_hex":base["payload"]["oracle"]["stdout_hex"],"stderr_hex":"","exit_code":0} if i==0 else
              a["oracle"]=={"stdout_hex":bytes.fromhex(a["oracle"]["stdout_hex"]).hex(),"stderr_hex":"","exit_code":0},"pair oracle shape")
        expected_shas=("e5aab46f5a720bacdbb2fb3cb83d682b02df7261336e79663c79fa78022b9bc4","52095dafd5235a8c1073248bbda3964f8a7b749722306ceaabf321d2fdcd4816")
        _need(hashlib.sha256(bytes.fromhex(a["oracle"]["stdout_hex"])).hexdigest()==expected_shas[i],"frozen pair output oracle")
        _need(type(a["timeout_ms"]) is int and a["timeout_ms"]==10000 and type(a["stdout_limit_bytes"]) is int and a["stdout_limit_bytes"]==1024 and type(a["stderr_limit_bytes"]) is int and a["stderr_limit_bytes"]==1024,"pair finite bounds")
    _need(p["apps"][0]["payload"]==base["artifacts"]["payload"],"primary app alias")
    return {**base,"pair":p,**({"pair_rounds":10} if round_case else {})}

def build_command(manifest,attempt):
    plan=_one_build_command(manifest,attempt)
    if "pair" not in manifest:return plan
    plan=_thaw(plan)
    plan["payload"]={"pair":manifest["pair"]["apps"]}
    plan["overlay"]["payloads"]=[a["payload"]["path"] for a in manifest["pair"]["apps"]]
    plan["overlay"]["boot_contract"]="native-boot-two-cpu-readback-v1"
    plan["overlay"]["guest_destinations"].update({"/apps/app"+str(i):a["payload"]["path"] for i,a in enumerate(manifest["pair"]["apps"])})
    plan["overlay"]["init_sequence"][-1]="two isolated app supervisors; join both before shared retirement"
    return _freeze(plan)

def _pair_trace(serial,pid,cpu,begin_cleanup=False):
    prefix=r"os=0 generation=1 pid="+str(pid)
    suffixes={"delivered":r"worker=(\d+) delivery=(\d+) cpu=(\d+) number=(\d+)",
              "returned":r"worker=(\d+) delivery=(\d+) cpu=(\d+) value=(-?\d+)",
              "return_route":r"worker=(\d+) delivery=(\d+) launcher_cpu=(-?\d+) guest_cpu=(\d+)"}
    records={k:{} for k in suffixes}
    for position,line in enumerate(serial.splitlines()):
        for name,suffix in suffixes.items():
            marker="application_syscall="+name+" "+"os=0 generation=1 pid="+str(pid)+" "
            if marker not in line:continue
            m=re.search(re.escape(marker)+suffix+r"\s*$",line)
            _need(m is not None,"malformed pair trace")
            row=tuple(map(int,m.groups()));key=row[:2]
            _need(all(0<v<2**64 for v in key) and key not in records[name],"duplicate/invalid pair delivery")
            records[name][key]=(row[2:],position)
    delivered,returned,routes=(records[k] for k in suffixes)
    exits={k for k,(row,_) in delivered.items() if row[1]==231}
    _need(delivered and returned and routes and len(exits)==1,"missing pair route/exit evidence")
    ordinary=set(delivered)-exits
    _need(set(returned)==ordinary and set(routes)<=ordinary and all(row[1]!=60 for row,_ in delivered.values()),"pair syscall correspondence")
    terminal=delivered[next(iter(exits))][1]
    _need(all(row[0]==cpu for row,_ in delivered.values()) and all(row[0]==cpu for row,_ in returned.values()),"pair actual CPU mismatch")
    workers={}
    for key in ordinary:
        begin,end=delivered[key][1],returned[key][1]
        _need(begin<end<terminal,"pair syscall order")
        slot=cpu
        if key in routes:
            (launcher,guest),where=routes[key]
            _need(launcher in (0,1) and launcher!=cpu and guest==cpu and begin<where<end,"pair route mismatch")
            slot=launcher
        _need(workers.setdefault(key[0],slot)==slot,"pair inconsistent worker route")
    if begin_cleanup:
        _check_begin_cleanup(serial,prefix,terminal)
        return
    # The retained broker retries EAGAIN with a fresh retirement Exchange
    # after the next monotonic-second boundary. The fixed successful launcher
    # has a10s supervisor budget: initial+ten boundary retries+success is a
    # conservative12-response cap. Every response still follows terminal exit.
    attempts=[];releases=[]
    for position,line in enumerate(serial.splitlines()):
        if "application retirement " in line and re.search(prefix+r"\b",line):
            match=re.search(r"application retirement "+prefix+r" token=(\d+) errno=(-?\d+)\s*$",line)
            _need(match is not None,"malformed pair retirement")
            token,error=map(int,match.groups())
            _need(0<token<2**64 and position>terminal,"pair premature retirement")
            attempts.append((position,token,error))
        if "application_process=release " in line and re.search(prefix+r"\b",line):
            match=re.search(r"application_process=release "+prefix+r" cleanup_errno=(-?\d+)\s*$",line)
            _need(match is not None and int(match.group(1))==0,"pair release failure")
            releases.append(position)
    _need(1<=len(attempts)<=12 and len({row[1] for row in attempts})==len(attempts),"pair retirement attempts")
    _need(all(row[2]==-11 for row in attempts[:-1]) and attempts[-1][2]==0,"pair retirement retry result")
    _need(len(releases)==1 and releases[0]>attempts[-1][0],"pair premature release")

def _pair_body(manifest,observation):
    serial=observation["serial"]
    _need(not any(line.startswith("ND_PAYLOAD ") for line in serial.splitlines()),"foreign one-app report")
    lines=[line[len("ND_PAIR "):] for line in serial.splitlines() if line.startswith("ND_PAIR ")]
    _need(len(lines)==1 and len(lines[0])<=MAX_JSON,"missing/duplicate pair report")
    r=json.loads(lines[0],object_pairs_hook=_pairs)
    _keys(r,("os","generation","host_cpus","cpus","procfs_empty","apps"))
    _need(type(r["os"]) is int and r["os"]==0 and type(r["generation"]) is int and r["generation"]==1 and r["host_cpus"]==[1,2] and r["cpus"]==[0,1] and r["procfs_empty"] is True,"pair CPU/retirement report")
    _need(type(r["apps"]) is list and len(r["apps"])==2,"pair reports")
    pids=[]
    for i,(a,expected) in enumerate(zip(r["apps"],manifest["pair"]["apps"])):
        _keys(a,("id","pid","cpu","cwd","argv","env","raw_wait_status","clean","fault","timeout","started_ns","reaped_ns","finished_ns","streams"))
        _need(type(a["id"]) is int and a["id"]==i and type(a["cpu"]) is int and a["cpu"]==i and type(a["pid"]) is int and a["pid"]>0 and a["pid"] not in pids,"pair PID/CPU identity")
        pids.append(a["pid"])
        for k in ("argv","cwd","env"):_need(a[k]==expected[k],"pair launch "+k)
        _need(all(type(a[k]) is int for k in ("raw_wait_status","clean","fault","timeout")) and (a["raw_wait_status"],a["clean"],a["fault"],a["timeout"])==(0,1,0,0),"pair app status")
        _need(all(type(a[k]) is int and a[k]>0 for k in ("started_ns","reaped_ns","finished_ns")) and a["started_ns"]<=a["reaped_ns"]<=a["finished_ns"],"pair times")
        _keys(a["streams"],("stdout","stderr"))
        for stream in ("stdout","stderr"):
            s=a["streams"][stream]
            _keys(s,("hex","eof","truncated","observed","retained","discarded","limit","eof_ns"))
            _need(type(s["hex"]) is str and re.fullmatch(r"(?:[0-9a-f]{2})*",s["hex"]),"pair stream hex")
            data=bytes.fromhex(s["hex"])
            _need(all(type(s[k]) is int and s[k]>=0 for k in ("observed","retained","discarded","limit","eof_ns")),"pair stream type")
            _need(s["eof"] is True and s["truncated"] is False and s["observed"]==s["retained"]==len(data)<=1024 and s["discarded"]==0 and s["limit"]==1024,"pair stream accounting")
            _need(a["started_ns"]<=s["eof_ns"]<=a["finished_ns"] and data==bytes.fromhex(expected["oracle"][stream+"_hex"]),"pair stream oracle")
        prefix=r"os=0 generation=1 pid="+str(a["pid"])
        _need(len(re.findall(r"application SCHEDULE "+prefix+r" cpu="+str(i)+r"\b",serial))==1,"pair schedule")
        lifecycle_patterns=() if _begin_cleanup_enabled(manifest) else (r"application retirement "+prefix+r" token=(\d+) errno=0\b",r"application_process=release "+prefix+r" cleanup_errno=0\b")
        for pattern in (*lifecycle_patterns,*[r"application procfs "+op+" "+prefix+r" tid="+str(a["pid"])+r"\b" for op in ("published","deleted")]):
            _need(len(re.findall(pattern,serial))==1,"pair retirement/procfs")
        _pair_trace(serial,a["pid"],i,_begin_cleanup_enabled(manifest))
    schedules=re.findall(r"application SCHEDULE os=(\d+) generation=(\d+) pid=(\d+) cpu=(\d+)\b",serial)
    _need(set(schedules)=={("0","1",str(pids[i]),str(i)) for i in range(2)} and len(schedules)==2,"foreign pair schedule")
    for line in serial.splitlines():
        for name in ("delivered","returned","return_route"):
            marker="application_syscall="+name+" "
            if marker not in line:continue
            found=re.search(re.escape(marker)+r"os=(\d+) generation=(\d+) pid=(\d+) ",line)
            _need(found is not None and found.groups()[:2]==("0","1") and int(found.group(3)) in pids,"malformed/foreign pair syscall")
    _need(max(a["started_ns"] for a in r["apps"])<min(a["reaped_ns"] for a in r["apps"]),"no pair overlap")
    _need("NATIVE_PAIR_CPU os=0 generation=1 assigned_host=1,2 logical=0,1 default_ikc_linux=0" in serial,"missing actual boot CPU readback")
    tokens=re.findall(r"application retirement os=0 generation=1 pid=(?:"+"|".join(map(str,pids))+r") token=(\d+) errno=0\b",serial)
    _need(len(tokens)==2 and len(set(tokens))==2 and all(int(t)>0 for t in tokens),"pair distinct retirement tokens")
    attempt_tokens=re.findall(r"application retirement os=0 generation=1 pid=(?:"+"|".join(map(str,pids))+r") token=(\d+) errno=-?\d+\s*$",serial,re.MULTILINE)
    _need(len(attempt_tokens)==len(set(map(int,attempt_tokens))) and all(0<int(t)<2**64 for t in attempt_tokens),"pair reused retirement attempt token")
    channels=[]
    for logical,physical in enumerate((1,2)):
        pattern=r"control accepted os=0 generation=1 port=501 guest_cpu="+str(logical)+r" linux_cpu="+str(physical)+r" cookie=(\d+) receive=([0-9a-f]+) send=([0-9a-f]+) bytes="+str(PAIR_CONTROL_QUEUE_BYTES)+r" reference=(\d+) remote_cookie=([0-9a-f]+)"
        matches=re.findall(pattern,serial)
        _need(len(matches)==1 and int(matches[0][0])>0 and all(int(x,16)>0 for x in (matches[0][1],matches[0][2],matches[0][4])),"missing twoCPU IKC channel readback")
        channels.append(matches[0])
    _need(channels[0][0]!=channels[1][0],"duplicate pair IKC cookie")
    queues=[int(row[k],16) for row in channels for k in (1,2)]
    _need(all(a+PAIR_CONTROL_QUEUE_BYTES<=b or b+PAIR_CONTROL_QUEUE_BYTES<=a for i,a in enumerate(queues) for b in queues[i+1:]),"overlapping pair IKC queues")
    _need(len(re.findall(r"control accepted os=0 generation=1 port=501 ",serial))==2,"foreign/duplicate pair IKC channel")
    elapsed=max(a["finished_ns"] for a in r["apps"])-min(a["started_ns"] for a in r["apps"])
    return {"schema_version":1,"kind":"native-diagnostic-result","case_id":manifest["case_id"],"status":"PROTOCOL_PASS","application_acceptance":False,"mckernel_application_executed":False,"guest_report":r,"observation":observation,"runtime_blocker":DIAGNOSTIC_LIMITATION,"pair_metrics":{"completed_apps":2,"wall_ns":elapsed,"apps_per_wall_minute":120_000_000_000/elapsed}}

def evaluate(manifest,observation):
    if "pair" not in manifest:return _one_evaluate(manifest,observation)
    # _pair_host_evaluate is generated from the literal retained host-observer
    # prefix, ending before single-payload parsing. No QMP/teardown gate changes.
    return _pair_host_evaluate(manifest,observation)


def _pair_host_evaluate(manifest, observation):
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
    return _pair_launch_expansion_body(manifest,observation) if manifest.get("pair_rounds")==10 else _pair_body(manifest,observation)

def _pair_launch_expansion_body(manifest,observation):
    """Fixed ten rounds; retain the original one-pair checker for each view."""
    _need(type(manifest.get('pair_rounds')) is int and manifest['pair_rounds']==10,'fixed ten-round case')
    serial=observation['serial'];lines=serial.splitlines()
    _need(not any(line.startswith(('ND_PAIR_ROUND_','ND_PAIR_ROUNDS_')) and not line.startswith(('ND_PAIR_ROUND_START ','ND_PAIR_ROUND_END ','ND_PAIR_ROUND_FAIL ','ND_PAIR_ROUNDS_COMPLETE ')) for line in lines),'unknown ten-round wire marker')
    _need(not any(line.startswith('ND_PAYLOAD ') for line in lines),'foreign one-app report')
    def records(prefix):
        return [(i,json.loads(line[len(prefix):],object_pairs_hook=_pairs)) for i,line in enumerate(lines) if line.startswith(prefix)]
    starts=records('ND_PAIR_ROUND_START ');ends=records('ND_PAIR_ROUND_END ');pairs=records('ND_PAIR ');complete=records('ND_PAIR_ROUNDS_COMPLETE ')
    _need(len(starts)==len(ends)==len(pairs)==10 and len(complete)==1,'exact ten-round evidence')
    _need(not any(line.startswith('ND_PAIR_ROUND_FAIL') for line in lines),'failed pair round')
    _keys(complete[0][1],('rounds','os','generation','procfs_empty'))
    _need(complete[0][1]=={'rounds':10,'os':0,'generation':1,'procfs_empty':True} and all(type(complete[0][1][k]) is int for k in ('rounds','os','generation')),'ten-round completion identity')
    pids=[]
    for _,report in pairs:
        _need(type(report.get('apps')) is list and len(report['apps'])==2,'ten-round apps')
        for app in report['apps']:
            pid=app.get('pid');_need(type(pid) is int and pid>0 and pid not in pids,'ten-round unique PID');pids.append(pid)
    schedules=re.findall(r'application SCHEDULE os=(\d+) generation=(\d+) pid=(\d+) cpu=(\d+)\b',serial)
    expected={('0','1',str(pid),str(i%2)) for i,pid in enumerate(pids)}
    _need(len(schedules)==20 and set(schedules)==expected,'ten-round global schedules')
    for line in lines:
        for name in ('delivered','returned','return_route'):
            marker='application_syscall='+name+' '
            if marker in line:
                match=re.search(re.escape(marker)+r'os=(\d+) generation=(\d+) pid=(\d+) ',line)
                _need(match is not None and match.groups()[:2]==('0','1') and int(match.group(3)) in pids,'ten-round foreign syscall')
    tokenrows=re.findall(r'application retirement os=0 generation=1 pid=(\d+) token=(\d+) errno=-?\d+\s*$',serial,re.MULTILINE)
    _need(tokenrows and all(int(pid) in pids and 0<int(token)<2**64 for pid,token in tokenrows),'ten-round token domain')
    _need(len(tokenrows)==len({int(token) for _,token in tokenrows}),'ten-round fresh retirement tokens')
    boot='NATIVE_PAIR_CPU os=0 generation=1 assigned_host=1,2 logical=0,1 default_ikc_linux=0'
    _need(sum(boot in line for line in lines)==1,'one actual OS boot assignment')
    validated=[];previous_end=None
    for round_index in range(10):
        start_at,start=starts[round_index];end_at,end=ends[round_index];report_at,report=pairs[round_index]
        for boundary in (start,end):
            _keys(boundary,('round','time_ns','procfs_empty'))
            _need(type(boundary['round']) is int and boundary['round']==round_index and type(boundary['time_ns']) is int and boundary['time_ns']>0 and boundary['procfs_empty'] is True,'ten-round boundary identity')
        _need(start_at<report_at<end_at<complete[0][0] and start['time_ns']<end['time_ns'],'ten-round serial/timestamp order')
        if round_index:
            _need(ends[round_index-1][0]<start_at and previous_end<=start['time_ns'],'sequential round handoff')
        current=pids[round_index*2:round_index*2+2];other=set(pids)-set(current);view=[]
        for line in lines:
            if line.startswith(('ND_PAIR ','ND_PAIR_ROUND_','ND_PAIR_ROUNDS_')):continue
            # Exclude only the fully identified other round. Unknown or malformed
            # schedule/syscall rows were refused globally above, not filtered.
            if any(marker in line for marker in ('application SCHEDULE ','application_syscall=','application retirement ','application_process=release ','application_process=cleanup_requested ','application cleanup ACK ','application procfs ')):
                found=re.search(r'os=0 generation=1 pid=(\d+)\b',line)
                if found is not None and int(found.group(1)) in other:continue
            view.append(line)
        view.append('ND_PAIR '+json.dumps(report,separators=(',',':')))
        observed=dict(observation,serial='\n'.join(view)+'\n');checked=_pair_body(manifest,observed)
        _need(all(start['time_ns']<=app['started_ns']<=app['finished_ns']<=end['time_ns'] for app in report['apps']),'round result inside handoff bounds')
        validated.append({'round':round_index,'start':start,'end':end,'guest_report':checked['guest_report'],'pair_metrics':checked['pair_metrics'],'trace_projection_excludes_only_known_other_round_PIDs':sorted(other)})
        previous_end=end['time_ns']
    elapsed=max(app['finished_ns'] for _,r in pairs for app in r['apps'])-min(app['started_ns'] for _,r in pairs for app in r['apps'])
    return {'schema_version':1,'kind':'native-diagnostic-result','case_id':manifest['case_id'],'status':'PROTOCOL_PASS','application_acceptance':False,'mckernel_application_executed':False,'guest_report':{'os':0,'generation':1,'rounds':validated,'procfs_empty':True},'observation':observation,'runtime_blocker':DIAGNOSTIC_LIMITATION,'pair_metrics':{'completed_rounds':10,'completed_apps':20,'wall_ns':elapsed,'apps_per_wall_minute':1_200_000_000_000/elapsed}}



# Explicit source-bound BEGIN_CLEANUP schema; absent field preserves legacy.
BEGIN_CLEANUP_PROFILE_ID = "begin-cleanup-real-ack-parent-clone-v2"
BEGIN_CLEANUP_SOURCE_REFS = {'consumer': {'path': '/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/wait-error-observation-1/mcctrl_process.rs', 'size': 54854, 'sha256': '8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8', 'mode': 33152}, 'provider': {'path': '/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-lifecycle-epipe-repair-1/smp_application.rs', 'sha256': 'f5c56d83a13f10a712a4555849f52078c2d410254080150d34408011daf527a5', 'size': 72744, 'mode': 33152}}

def _begin_cleanup_enabled(manifest):
    return "cleanup_profile" in manifest

def _validate_cleanup_profile(profile, modules):
    _keys(profile, ("schema_version", "id", "consumer", "provider", "modules", "child_trace_cases"))
    _need(type(profile["schema_version"]) is int and profile["schema_version"] == 1 and
          profile["id"] == BEGIN_CLEANUP_PROFILE_ID, "BEGIN cleanup schema")
    _need(profile["child_trace_cases"] == list(BEGIN_PROCESS_CASES), "BEGIN child trace case scope")
    for name in ("consumer", "provider"):
        _need(profile[name] == BEGIN_CLEANUP_SOURCE_REFS[name], "BEGIN source identity")
        _ref(profile[name], "BEGIN " + name)
    _need(type(modules) is list and len(modules)==3 and profile["modules"] == modules, "BEGIN module tuple differs")
    # The ordinary manifest validator checks each complete module reference,
    # including actual bytes. Null/future descriptors cannot become authority.
    return dict(profile)

def _check_begin_cleanup(serial, prefix, terminal):
    """Intent is not ACK. Match owner identity, not cross-namespace tokens.

    ACK may precede intent logging; close may set abandoned=1. Retirement
    queries are issued only after successful cleanup ACK. The target terminal
    must precede its own actual retirement, independently of any child.
    """
    owner = re.fullmatch(r"os=(\d+) generation=(\d+) pid=(\d+)", prefix)
    _need(owner is not None, "BEGIN owner identity")
    pid = owner.group(3)
    intents=[]; acknowledgements=[]; attempts=[]
    patterns = (
        ("application_process=cleanup_requested ", r"intent_errno=(-?\d+)", intents),
        ("application cleanup ACK ", r"token=(\d+) errno=(-?\d+) abandoned=([01])", acknowledgements),
        ("application retirement ", r"token=(\d+) errno=(-?\d+)", attempts),
    )
    for position,line in enumerate(serial.splitlines()):
        for marker,suffix,rows in patterns:
            if marker not in line or not re.search(r"pid="+pid+r"\b", line):
                continue
            match=re.search(re.escape(marker)+prefix+" "+suffix+r"\s*$",line)
            _need(match is not None, "malformed/wrong-generation BEGIN lifecycle")
            rows.append((position, *map(int,match.groups())))
    _need(len(intents)==1 and intents[0][1]==0, "missing/failed BEGIN intent")
    _need(len(acknowledgements)==1, "missing/duplicate real cleanup ACK")
    ack=acknowledgements[0]
    _need(0<ack[1]<2**64 and ack[2]==0, "real cleanup ACK failure/token")
    _need(1<=len(attempts)<=12 and len({a[1] for a in attempts})==len(attempts), "BEGIN retirement attempts")
    _need(all(0<a[1]<2**64 and a[0]>terminal and a[0]>ack[0] for a in attempts), "BEGIN premature retirement/token")
    _need(all(a[2]==-11 for a in attempts[:-1]) and attempts[-1][2]==0, "BEGIN retirement result")
    return {"entry_token":ack[1],"query_tokens":[a[1] for a in attempts]}

_legacy_cleanup_validate_manifest = _validate_manifest
def _validate_manifest(obj):
    if "cleanup_profile" not in obj:
        return _legacy_cleanup_validate_manifest(obj)
    base=dict(obj);profile=base.pop("cleanup_profile")
    validated=_legacy_cleanup_validate_manifest(base)
    validated["cleanup_profile"]=_validate_cleanup_profile(profile,validated["modules"])
    return validated


BEGIN_PROCESS_CASES = ('P-M06-01-process-exec-wait-235B', 'P-M01-02-child-SIGTERM-and-exec-recovery-227B')

def _begin_process_case(manifest):
    return _begin_cleanup_enabled(manifest) and manifest["case_id"] in BEGIN_PROCESS_CASES

def _audit_begin_children(serial, prefix):
    """Return a parent projection only after auditing every observed child row.

    Child authority is a positive RET to a matched parent clone(56), plus real
    same-generation procfs publication. A child can run before the parent RET
    log. A SIGTERM-cancelled child need not emit exit_group; every sampled
    ordinary delivery still needs its actual return and valid optional route.
    """
    owner=re.fullmatch(r"os=(\d+) generation=(\d+) pid=(\d+)",prefix)
    _need(owner is not None,"process trace parent identity")
    os_id,generation,parent=map(int,owner.groups())
    suffixes={"delivered":r"worker=(\d+) delivery=(\d+) cpu=(\d+) number=(\d+)",
              "returned":r"worker=(\d+) delivery=(\d+) cpu=(\d+) value=(-?\d+)",
              "return_route":r"worker=(\d+) delivery=(\d+) launcher_cpu=(-?\d+) guest_cpu=(\d+)"}
    groups={};row_pids={}
    for position,line in enumerate(serial.splitlines()):
        for name,suffix in suffixes.items():
            marker="application_syscall="+name+" "
            if marker not in line:continue
            m=re.search(re.escape(marker)+r"os=(\d+) generation=(\d+) pid=(\d+) "+suffix+r"\s*$",line)
            _need(m is not None,"malformed process syscall row")
            os_seen,gen_seen,pid,worker,delivery,a,b=map(int,m.groups())
            _need((os_seen,gen_seen)==(os_id,generation) and pid>0 and 0<worker<2**64 and 0<delivery<2**64,"foreign process syscall identity")
            records=groups.setdefault(pid,{k:{} for k in suffixes});key=(worker,delivery)
            _need(key not in records[name],"duplicate process syscall row")
            records[name][key]=((a,b),position);row_pids[position]=pid
    _need(parent in groups,"missing process parent trace")
    pd,pr=groups[parent]["delivered"],groups[parent]["returned"]
    children={}
    for key,((cpu,number),position) in pd.items():
        if number!=56 or key not in pr:continue
        (retcpu,value),retpos=pr[key]
        _need(retcpu==cpu==0 and position<retpos,"parent clone correspondence")
        if value<=0:continue
        _need(value!=parent and value not in children,"duplicate/parent clone child")
        children[value]=position
    _need(set(groups)<={parent,*children},"unlinked child syscall PID")
    for child,clone_position in children.items():
        # A child may be cancelled before its first sampled syscall; its
        # provider publication must still identify the clone return exactly.
        publication=[]
        for position,line in enumerate(serial.splitlines()):
            if "application procfs published " not in line or not re.search(r"pid="+str(child)+r"\b",line):continue
            m=re.search(r"application procfs published os="+str(os_id)+r" generation="+str(generation)+r" pid="+str(child)+r" tid="+str(child)+r"\s*$",line)
            _need(m is not None,"child procfs identity")
            publication.append(position)
        _need(len(publication)==1 and publication[0]>clone_position,"missing/duplicate child publication")
        if child not in groups:continue
        delivered,returned,routes=(groups[child][k] for k in suffixes)
        _need(delivered and set(routes)<=set(returned)<=set(delivered),"child syscall correspondence")
        terminals={k for k,(row,_) in delivered.items() if row[1] in (60,231)}
        _need(len(terminals)<=1 and set(returned)==set(delivered)-terminals,"child ordinary RET coverage")
        terminal=delivered[next(iter(terminals))][1] if terminals else None
        workers={}
        for key,((cpu,number),begin) in delivered.items():
            _need(cpu==0 and begin>publication[0],"child CPU/publication order")
            if key in terminals:continue
            (retcpu,_),end=returned[key]
            _need(retcpu==0 and begin<end and (terminal is None or end<terminal),"child syscall/terminal order")
            slot=0
            if key in routes:
                (launcher,guest),where=routes[key]
                _need(launcher==1 and guest==0 and begin<where<end,"child route identity/order")
                slot=launcher
            _need(workers.setdefault(key[0],slot)==slot,"child worker route changed")
    parent_view=[line for position,line in enumerate(serial.splitlines()) if position not in row_pids or row_pids[position]==parent]
    return "\n".join(parent_view), sorted(children)

# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Exact F05 successor appended AFTER the complete f368 evaluator/wrapper chain.
# Historical BEGIN_PROCESS_CASES and both audit/cleanup implementations stay intact.
F05_CASE = "M14-05-05-owned-processvm-204B"
F05_PROFILE = "begin-cleanup-real-ack-owned-processvm-204B-v1"
F05_SOURCE_SHA = "4aef0b5f30bc8090bdbe102332e39895b328b3ebe2735c3d011d5c035c602e68"
F05_BINARY_SHA = "be508daa7549a50312306bb1064d4df9fe738dc9d7ba6dd32d58e8a1d97258a2"
F05_ORACLE_SHA = "de8c41a3a53a3cf823c9c6cfe242f363cb823dfa173be854f6d89188a20e7aae"
F05_HOST_SHA = "ca6f2ee37dde1da02ffb1d001a9c6457fdf4fbefe20017e45e34a9f12796e604"
F05_STDOUT = (
    b"OWNED_F05 v1 children=1 clone_child_settid=1 parent_tid_unchanged=1\n"
    b"traceme=0 sigstop=19 peek=0 poke=0 readback=0 cross_4k_word=1\n"
    b"child_verified=1 private_unchanged=1 child_exit=0 reaped=1\n"
    b"OWNED_F05 PASS\n"
)
F05_ORACLE = {"stdout_hex": F05_STDOUT.hex(), "stderr_hex": "", "exit_code": 0}
F05_MODULE_SHAS = (
    "daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c",
    "887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12",
    "57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8",
)
_f05_previous_cleanup_profile = _validate_cleanup_profile
_f05_previous_validate_manifest = _validate_manifest
_f05_previous_process_case = _begin_process_case
_f05_previous_evaluate = evaluate


def _f05_bound_ref(ref, size, sha, label):
    _need(ref.get("size") == size and ref.get("sha256") == sha, label + " frozen identity")
    return _ref(ref, label)


def _validate_cleanup_profile(profile, modules):
    if profile.get("id") != F05_PROFILE:
        return _f05_previous_cleanup_profile(profile, modules)
    _keys(profile, ("schema_version", "id", "consumer", "provider", "modules",
                    "child_trace_cases", "case_binding"))
    _need(type(profile["schema_version"]) is int and profile["schema_version"] == 1,
          "F05 cleanup schema")
    _need(profile["child_trace_cases"] == [F05_CASE], "F05 exact child case scope")
    for name in ("consumer", "provider"):
        _need(profile[name] == BEGIN_CLEANUP_SOURCE_REFS[name], "F05 BEGIN source identity")
        _ref(profile[name], "F05 BEGIN " + name)
    _need(type(modules) is list and len(modules) == 3 and profile["modules"] == modules,
          "F05 cleanup module references")
    _need(tuple(row["sha256"] for row in modules) == F05_MODULE_SHAS, "F05 module tuple")
    binding = profile["case_binding"]
    _keys(binding, ("source", "oracle", "host_qualification", "payload_timeout_ms"))
    _need(type(binding["payload_timeout_ms"]) is int and binding["payload_timeout_ms"] == 10000,
          "F05 collector payload timeout")
    _f05_bound_ref(binding["source"], 10987, F05_SOURCE_SHA, "F05 Rust source")
    _f05_bound_ref(binding["oracle"], 1474, F05_ORACLE_SHA, "F05 original oracle")
    _f05_bound_ref(binding["host_qualification"], 7418, F05_HOST_SHA, "F05 HOST qualification")
    return dict(profile)


def _f05_contract(manifest):
    _need(manifest["case_id"] == F05_CASE and "pair" not in manifest,
          "F05 exact single-parent case ID")
    profile = manifest.get("cleanup_profile", {})
    _need(profile.get("id") == F05_PROFILE, "F05 explicit cleanup profile required")
    _validate_cleanup_profile(profile, manifest["modules"])
    payload = manifest["payload"]
    _need(payload == {
        "argv": ["/bin/mcexec", "-t", "1", "0", "/apps/app"],
        "cwd": "/case/work", "env": {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"},
        "oracle": F05_ORACLE, "stdout_limit_bytes": 1024, "stderr_limit_bytes": 1024,
    }, "F05 frozen launch/oracle/stream contract")
    _f05_bound_ref(manifest["artifacts"]["payload"], 5624488, F05_BINARY_SHA, "F05 payload")
    collector = manifest["staging"]["collector"]
    _need(collector["size"] == 1021320 and collector["sha256"] ==
          "c020a8e0ab43e222caf901d92bfecb2a8d8cf20ea0b539910a17a578f1fd12fc",
          "F05 retained 1024-byte/10s collector")
    binding = profile["case_binding"]
    oracle = json.loads(Path(binding["oracle"]["path"]).read_text(), object_pairs_hook=_pairs)
    _need(oracle["source"]["sha256"] == F05_SOURCE_SHA and oracle["source"]["size"] == 10987 and
          {key: oracle[key] for key in F05_ORACLE} == F05_ORACLE and
          oracle["expected_stdout"]["size"] == len(F05_STDOUT) == 204 and
          oracle["expected_stdout"]["sha256"] == hashlib.sha256(F05_STDOUT).hexdigest(),
          "F05 original source/oracle join")
    host = json.loads(Path(binding["host_qualification"]["path"]).read_text(), object_pairs_hook=_pairs)
    _need(host["status"] == "PASS_F05_OWNED_LINUX_REFERENCE_ONLY" and
          host["source"]["sha256"] == F05_SOURCE_SHA and host["source"]["bytes"] == 10987 and
          host["executable"]["sha256"] == F05_BINARY_SHA and host["executable"]["bytes"] == 5624488 and
          host["oracle"]["sha256"] == F05_ORACLE_SHA, "F05 HOST source/binary/oracle join")
    results = host["results"]
    _need(type(results) is list and len(results) == 3, "F05 HOST qualification stages")
    for index, row in enumerate(results):
        _need(row["index"] == index and type(row["returncode"]) is int and row["returncode"] == 0 and
              row["direct_child_joined"] is True and row["group_absent"] is True and
              row["remaining_group_members"] == row["unexpected_group_members"] == [] and
              row["timed_out"] is False and row["closed_streams"] is True and
              row["error"] is None and row["retirement_error"] is None,
              "F05 HOST positive process/stream joins")
    for name, expected in (("stdout", F05_STDOUT), ("stderr", b"")):
        capture = results[2]["captures"][name]
        _need(capture["sha256"] == hashlib.sha256(expected).hexdigest() and
              capture["size"] == len(expected), "F05 HOST exact " + name)
        _ref({"path": capture["path"], "sha256": capture["sha256"], "size": capture["size"],
              "mode": stat.S_IFREG | int(capture["mode"], 8)}, "F05 HOST " + name)


def _f05_case_profile_guard(manifest):
    new_case = manifest.get("case_id") == F05_CASE
    new_profile = manifest.get("cleanup_profile", {}).get("id") == F05_PROFILE
    frozen_binary = manifest.get("artifacts", {}).get("payload", {}).get("sha256") == F05_BINARY_SHA
    frozen_output = manifest.get("payload", {}).get("oracle", {}).get("stdout_hex") == F05_STDOUT.hex()
    _need(new_case == new_profile and (not (frozen_binary or frozen_output) or new_case),
          "F05 case/profile identity mismatch or historical relabeling")
    return new_case


def _validate_manifest(obj):
    # Exact new-ID binding is mandatory; old identities retain their literal chain.
    new_case = _f05_case_profile_guard(obj)
    validated = _f05_previous_validate_manifest(obj)
    if new_case:
        _f05_contract(validated)
    return validated


def _begin_process_case(manifest):
    if manifest.get("case_id") == F05_CASE:
        return manifest.get("cleanup_profile", {}).get("id") == F05_PROFILE
    return _f05_previous_process_case(manifest)


def _f05_trace(serial):
    # Keep the retained exactly-one parent SCHEDULE rule, with no child filtering.
    schedules = []
    for line in serial.splitlines():
        if "application SCHEDULE " in line:
            match = re.search(r"application SCHEDULE os=(\d+) generation=(\d+) pid=(\d+) cpu=(\d+)\s*$", line)
            _need(match is not None, "F05 malformed schedule")
            schedules.append(tuple(map(int, match.groups())))
    _need(len(schedules) == 1 and schedules[0][:2] == (0, 1) and schedules[0][2] > 0 and
          schedules[0][3] == 0, "F05 exactly one positive parent schedule")
    parent = schedules[0][2]
    prefix = "os=0 generation=1 pid=" + str(parent)
    _, children = _audit_begin_children(serial, prefix)  # Unchanged full audit.
    _need(len(children) == 1, "F05 exactly one linked positive distinct child")
    child = children[0]
    lines = serial.splitlines()
    publication = {}; deletion = {}
    for position, line in enumerate(lines):
        for operation, rows in (("published", publication), ("deleted", deletion)):
            if "application procfs " + operation + " " not in line:
                continue
            match = re.search(r"application procfs " + operation +
                              r" os=(\d+) generation=(\d+) pid=(\d+) tid=(\d+)\s*$", line)
            _need(match is not None, "F05 malformed procfs lifecycle")
            os_id, generation, pid, tid = map(int, match.groups())
            _need((os_id, generation) == (0, 1) and pid in (parent, child) and tid == pid and
                  pid not in rows, "F05 foreign/duplicate procfs lifecycle")
            rows[pid] = position
    _need(set(publication) == set(deletion) == {parent, child}, "F05 complete owned procfs lifecycle")
    delivered = {}; returned = {}
    for position, line in enumerate(lines):
        match = re.search(r"application_syscall=(delivered|returned) os=0 generation=1 pid=(\d+) "
                          r"worker=(\d+) delivery=(\d+) cpu=(\d+) (?:number|value)=(-?\d+)\s*$", line)
        if match:
            kind, pid, worker, delivery, cpu, value = match.groups()
            row = (int(pid), int(worker), int(delivery))
            (delivered if kind == "delivered" else returned)[row] = (int(value), position)
    terminal = [(row, position) for row, (number, position) in delivered.items()
                if row[0] == child and number in (60, 231)]
    _need(len(terminal) == 1 and delivered[terminal[0][0]][0] == 60,
          "F05 exactly one child raw exit60")
    child_terminal = terminal[0][1]
    _need(any(row[0] == child and number not in (60, 231) and row in returned
              for row, (number, _) in delivered.items()), "F05 actual ordinary child RET evidence")
    parent_terminal = [position for row, (number, position) in delivered.items()
                       if row[0] == parent and number == 231]
    _need(len(parent_terminal) == 1 and publication[child] < child_terminal < deletion[child] <
          parent_terminal[0], "F05 child lifetime/parent terminal order")
    # The actual RET must join a parent wait4 delivery and name this linked child.
    # A stop wait4 can also return child; only a RET after terminal60 is a reap.
    reaps = [position for row, (value, position) in returned.items()
             if row[0] == parent and value == child and row in delivered and delivered[row][0] == 61 and
             delivered[row][1] < position and child_terminal < position < parent_terminal[0]]
    _need(len(reaps) == 1, "F05 exact successful parent wait4/reap after child terminal")
    # Retain the parent real-ACK/terminal/retirement contract literally.
    _check_begin_cleanup(serial, prefix, parent_terminal[0])


def evaluate(manifest, observation):
    new_case = _f05_case_profile_guard(manifest)
    if new_case:
        _f05_contract(manifest)
        _f05_trace(observation["serial"])
    # Invoke the final retained evaluate wrapper, not an AST-extracted old name.
    return _f05_previous_evaluate(manifest, observation)
