#!/usr/bin/env python3
"""Manifest-bound, direct-QEMU diagnostic adapter.

This module deliberately has no guest/backend side effects at import time.  The
three stages (prepare, command, evaluate) are separate so review tests can use
fake process and QMP observations.  A diagnostic result is never application
acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import shutil
import subprocess
import time

QEMU = "/usr/libexec/qemu-kvm"
MAX_JSON = 4 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
ARTIFACTS = ("bzImage", "initramfs", "root_base", "mckernel_image", "mcexec", "payload")
MODULE_NAMES = ("ihk.ko", "ihk-smp-x86_64.ko", "mcctrl.ko")
BAD_MARKERS = re.compile(r"(?:panic|oops|\bBUG\b|\berror\b)", re.I)


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
    append = profile.get("append", "console=ttyS0")
    _need(isinstance(append, str) and "\0" not in append, "kernel append")
    _need(isinstance(obj["payload"], dict) and set(obj["payload"]) <= {"cwd", "argv", "env", "oracle"}
          and {"cwd", "argv", "env"} <= set(obj["payload"]), "payload keys")
    payload = obj["payload"]
    _need(payload["cwd"] == "/case/work" and payload["argv"] == ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"], "payload contract")
    _need(isinstance(payload["env"], dict) and all(type(k) is str and "=" not in k and "\0" not in k and type(v) is str and "\0" not in v for k, v in payload["env"].items()) and payload["env"].get("PATH") == "/usr/bin:/bin", "frozen PATH")
    oracle = payload.get("oracle", {"stdout_hex": "", "stderr_hex": "", "exit_code": 0})
    _keys(oracle, ("stdout_hex", "stderr_hex", "exit_code"))
    _need(type(oracle["stdout_hex"]) is str and re.fullmatch(r"(?:[0-9a-fA-F]{2})*", oracle["stdout_hex"]), "oracle stdout")
    _need(type(oracle["stderr_hex"]) is str and re.fullmatch(r"(?:[0-9a-fA-F]{2})*", oracle["stderr_hex"]), "oracle stderr")
    _need(type(oracle["exit_code"]) is int and not isinstance(oracle["exit_code"], bool) and 0 <= oracle["exit_code"] <= 255, "oracle exit")
    return {"schema_version": 1, "kind": obj["kind"], "case_id": obj["case_id"], "artifacts": bound,
            "modules": modules, "profile": {"memory_mib": 8192, "vcpus": 4, "numa_nodes": 2, "append": append},
            "payload": {"cwd": payload["cwd"], "argv": list(payload["argv"]), "env": dict(payload["env"]), "oracle": oracle} }


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        _need(key not in out, "duplicate JSON key")
        out[key] = value
    return out


def prepare_attempt(manifest, parent, name):
    """Create a fresh 0700 attempt and reserve its QMP socket pathname."""
    parent = Path(parent)
    _need(parent.is_absolute() and parent.is_dir() and not parent.is_symlink(), "attempt parent")
    _need(isinstance(name, str) and name and "/" not in name and name not in (".", ".."), "attempt name")
    attempt = parent / name
    _need(not os.path.lexists(attempt), "existing attempt")
    try:
        os.mkdir(attempt, 0o700)
    except FileExistsError as exc:
        raise DiagnosticError("existing attempt") from exc
    socket = attempt / "qmp.sock"
    _need(not os.path.lexists(socket), "stale socket")
    for filename in ("stdout.bin", "stderr.bin", "serial.log", "debugcon.log"):
        (attempt / filename).touch(mode=0o600, exist_ok=False)
    # The retained root image is never attached writable.  Work only on a
    # private copy; initramfs is likewise copied before overlay preparation.
    for source_name, target_name in (("root_base", "root.img"), ("initramfs", "initramfs.img")):
        shutil.copyfile(manifest["artifacts"][source_name]["path"], attempt / target_name)
        os.chmod(attempt / target_name, 0o600)
    (attempt / "overlay").mkdir(mode=0o700)
    return attempt


def build_command(manifest, attempt):
    """Return the reviewed direct-QEMU argv and initramfs/module overlay plan."""
    attempt = Path(attempt)
    _need(attempt.is_dir() and (attempt.stat().st_mode & 0o777) == 0o700, "attempt not private")
    a = manifest["artifacts"]
    qmp = str(attempt / "qmp.sock")
    _need(not os.path.lexists(qmp), "stale QMP socket")
    argv = [QEMU, "-m", "8192", "-smp", "4", "-numa", "node,nodeid=0", "-numa", "node,nodeid=1",
            "-nic", "none", "-nodefaults", "-display", "none",
            "-qmp", "unix:" + qmp + ",server=on,wait=off", "-serial", "file:" + str(attempt / "serial.log"),
            "-debugcon", "file:" + str(attempt / "debugcon.log"), "-kernel", a["bzImage"]["path"],
            "-initrd", str(attempt / "initramfs.img"), "-drive", "file=" + str(attempt / "root.img") + ",if=virtio,format=raw",
            "-append", manifest["profile"]["append"]]
    overlay = {"modules": [m["path"] for m in manifest["modules"]], "mckernel_image": a["mckernel_image"]["path"],
               "mcexec": a["mcexec"]["path"], "payload": a["payload"]["path"], "load_modules": list(MODULE_NAMES),
               "boot_contract": "native-boot-v1", "guest_destinations": {"/boot/mckernel.img": a["mckernel_image"]["path"],
               "/bin/mcexec": a["mcexec"]["path"], "/case/work/app": a["payload"]["path"]}}
    return {"argv": argv, "overlay": overlay, "payload": manifest["payload"], "qmp_socket": qmp}


def evaluate(manifest, observation):
    """Evaluate a fully captured fake/real observation; reject uncertainty."""
    _keys(observation, ("stdout", "stderr", "exit_code", "serial", "debugcon", "qmp", "teardown", "timed_out", "truncated"))
    _need(type(observation["timed_out"]) is bool and type(observation["truncated"]) is bool and
          observation["timed_out"] is False and observation["truncated"] is False, "timeout/truncation")
    _need(type(observation["exit_code"]) is int and 0 <= observation["exit_code"] <= 255, "exit code")
    _need(type(observation["stdout"]) is bytes and type(observation["stderr"]) is bytes and
          observation["exit_code"] == manifest["payload"]["oracle"]["exit_code"] and
          observation["stdout"] == bytes.fromhex(manifest["payload"]["oracle"]["stdout_hex"]) and
          observation["stderr"] == bytes.fromhex(manifest["payload"]["oracle"]["stderr_hex"]), "wrong exit/output")
    _need(type(observation["serial"]) is str and type(observation["debugcon"]) is str and
          not BAD_MARKERS.search(observation["serial"] + "\n" + observation["debugcon"]), "kernel panic/oops marker")
    _need(isinstance(observation["qmp"], dict) and observation["qmp"].get("status") in ("running", "shutdown"), "QMP status")
    _need(observation["teardown"] is True, "teardown uncertain")
    return {"schema_version": 1, "kind": "native-diagnostic-result", "case_id": manifest["case_id"],
            "status": "PASS", "application_acceptance": False, "stdout": observation["stdout"].hex(),
            "stderr": observation["stderr"].hex(), "exit_code": observation["exit_code"], "serial": observation["serial"],
            "debugcon": observation["debugcon"], "qmp": observation["qmp"]}


def run_diagnostic(manifest, attempt, process_factory=None, qmp_factory=None, timeout=300):
    """Run only through explicitly supplied factories; absent factories block.

    This prevents accidental host/QEMU execution while allowing the reviewed
    lifecycle to be exercised with a fake subprocess and QMP implementation.
    Factories receive the reviewed argv/socket and return objects implementing
    ``negotiate``, ``resume``, ``query_status``, ``terminate`` and ``close``.
    """
    _need(type(timeout) in (int, float) and not isinstance(timeout, bool) and timeout > 0, "deadline")
    _need(process_factory is not None and qmp_factory is not None, "runtime backend not supplied")
    command = build_command(manifest, attempt)
    process = process_factory(command["argv"], cwd=str(attempt), env=manifest["payload"]["env"])
    qmp = None
    observation = {"stdout": b"", "stderr": b"", "exit_code": 255, "serial": "", "debugcon": "",
                   "qmp": {}, "teardown": False, "timed_out": False, "truncated": False}
    started = time.monotonic()
    try:
        qmp = qmp_factory(command["qmp_socket"])
        qmp.negotiate(); qmp.resume(); qmp.query_status()
        try:
            stdout, stderr = process.communicate(timeout=max(0.01, timeout - (time.monotonic() - started)))
            observation.update(stdout=stdout, stderr=stderr, exit_code=process.returncode)
        except subprocess.TimeoutExpired:
            observation["timed_out"] = True
            raise DiagnosticError("payload/QEMU deadline")
        observation["qmp"] = qmp.query_status()
        observation["serial"] = (Path(attempt) / "serial.log").read_text(errors="replace")
        observation["debugcon"] = (Path(attempt) / "debugcon.log").read_text(errors="replace")
    finally:
        try:
            if qmp is not None:
                qmp.terminate()
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)
            observation["teardown"] = process.poll() is not None
        except Exception as exc:
            observation["teardown"] = False
            raise DiagnosticError("teardown uncertain") from exc
        finally:
            if qmp is not None:
                qmp.close()
    return evaluate(manifest, observation)


def write_record(attempt, record, failure=None):
    """Publish one fsynced first-failure journal and an atomic final record."""
    attempt = Path(attempt)
    target = attempt / "result.json"
    _need(not os.path.lexists(target), "final record already published")
    if failure is not None:
        journal = attempt / "first-failure.jsonl"
        if not journal.exists():
            with journal.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(failure, sort_keys=True, allow_nan=False) + "\n")
                stream.flush(); os.fsync(stream.fileno())
    fd, tmp = tempfile.mkstemp(prefix=".result.", dir=attempt)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True, allow_nan=False); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, target)
        dfd = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY); os.fsync(dfd); os.close(dfd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
