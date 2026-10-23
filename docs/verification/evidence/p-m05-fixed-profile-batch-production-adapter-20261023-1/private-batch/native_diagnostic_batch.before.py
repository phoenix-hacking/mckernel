#!/usr/bin/env python3
"""Run a bounded, sequential batch of independently released diagnostics.

This sidecar grants no execution release or guest acceptance. A timed-out
root owner is left running and the batch stops without a retry or signal.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time


SHA = re.compile(r"[0-9a-f]{64}\Z")
NONCE = re.compile(r"[0-9a-f]{32}\Z")
OWNER = "/home/holden/mckernel/scripts/application-tests/native_diagnostic_container_owner.py"
PREFIX = ["/usr/bin/sudo", "-A", "/home/holden/anaconda3/bin/python3", "-B", OWNER]
FLAGS = {"--attempt-parent", "--nonce", "--owner-sha256", "--manifest", "--manifest-sha256"}
LIMIT = 4 * 1024 * 1024


class BatchError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise BatchError(message)


def _read(path, label):
    """Read one bounded regular file without following a final symlink."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_size <= LIMIT, label + " regular bounded file")
        raw = bytearray()
        while len(raw) <= LIMIT:
            block = os.read(fd, min(1024 * 1024, LIMIT + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        after = os.fstat(fd)
        identity = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        _need(len(raw) == before.st_size and all(getattr(before, key) == getattr(after, key)
                                                 for key in identity), label + " changed while reading")
        return bytes(raw)
    finally:
        os.close(fd)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw, label):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, label + " duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(_):
        raise BatchError(label + " nonfinite JSON")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BatchError(label + " malformed JSON") from exc


def _canonical(path, label):
    _need(type(path) is str and path.startswith("/") and "\0" not in path and
          str(Path(path).resolve(strict=True)) == path, label + " canonical path")
    return path


def _file_ref(value, label):
    _need(type(value) is dict and set(value) == {"path", "sha256"}, label + " reference")
    try:
        path = _canonical(value["path"], label)
        raw = _read(path, label)
    except (OSError, RuntimeError) as exc:
        raise BatchError(label + " unavailable") from exc
    _need(type(value["sha256"]) is str and SHA.fullmatch(value["sha256"]), label + " digest")
    _need(_digest(raw) == value["sha256"], label + " digest drift")
    return raw


def _command_args(command, label):
    _need(type(command) is list and len(command) == 15 and
          all(type(item) is str and item and "\0" not in item for item in command) and
          command[:5] == PREFIX, label + " owner command")
    names = command[5::2]
    _need(len(names) == len(FLAGS) and set(names) == FLAGS, label + " owner flags")
    return dict(zip(names, command[6::2]))


def validate_spec(spec):
    _need(type(spec) is dict and set(spec) == {"schema_version", "kind", "cases"}, "batch keys")
    _need(type(spec["schema_version"]) is int and spec["schema_version"] == 1 and
          spec["kind"] == "native-diagnostic-batch", "batch identity")
    cases = spec["cases"]
    _need(type(cases) is list and 1 <= len(cases) <= 32, "case count")
    seen_ids, seen_commands, seen_outputs = set(), set(), set()
    seen_releases, seen_nonces, seen_parents = set(), set(), set()
    checked = []
    owner_digest = _digest(_read(OWNER, "owner"))
    for index, case in enumerate(cases):
        _need(type(case) is dict and set(case) == {"case_id", "command", "timeout_seconds",
                                                    "manifest", "release", "output_name"},
              "case %d keys" % index)
        cid = case["case_id"]
        _need(type(cid) is str and cid and "\0" not in cid and cid not in seen_ids,
              "case %d id" % index)
        seen_ids.add(cid)
        label = "case " + cid
        command = case["command"]
        args = _command_args(command, label)
        key = json.dumps(command, ensure_ascii=False, separators=(",", ":"))
        _need(key not in seen_commands, label + " command reused")
        seen_commands.add(key)
        _need(args["--owner-sha256"] == owner_digest, label + " owner hash drift")
        _need(NONCE.fullmatch(args["--nonce"]) is not None and
              args["--nonce"] not in seen_nonces, label + " nonce reused")
        seen_nonces.add(args["--nonce"])
        parent = _canonical(args["--attempt-parent"], label + " attempt parent")
        _need(Path(parent).is_dir() and parent not in seen_parents,
              label + " attempt parent reused")
        seen_parents.add(parent)
        timeout = case["timeout_seconds"]
        _need(type(timeout) in (int, float) and math.isfinite(timeout) and
              0 < timeout <= 900, label + " timeout")
        _file_ref(case["manifest"], label + " manifest")
        _need(args["--manifest"] == case["manifest"]["path"] and
              args["--manifest-sha256"] == case["manifest"]["sha256"],
              label + " manifest argv")
        release_raw = _file_ref(case["release"], label + " release")
        release_path = case["release"]["path"]
        _need(release_path not in seen_releases, label + " release reused")
        seen_releases.add(release_path)
        release = _json(release_raw, label + " release")
        _need(type(release) is dict and release.get("status") == "PASS_EXECUTION" and
              release.get("case_id") == cid and release.get("command") == command and
              release.get("manifest_sha256") == args["--manifest-sha256"] and
              release.get("args_manifest_sha256") == args["--manifest-sha256"] and
              release.get("owner_sha256") == owner_digest and
              type(release.get("owner_uid")) is int and release["owner_uid"] == 0 and
              release.get("attempt_nonce") == args["--nonce"] and
              release.get("attempt_parent") == parent and
              release.get("invocation_sha256") == _digest(
                  json.dumps(command, separators=(",", ":")).encode("utf-8")),
              label + " release identity")
        output = case["output_name"]
        _need(type(output) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}",
                                                  output) is not None and
              output != "batch-result.json" and output not in seen_outputs,
              label + " output name")
        seen_outputs.add(output)
        checked.append((cid, command, float(timeout), case["manifest"]["path"],
                        release_path, output))
    return checked


def _publish(directory, name, value):
    """Fsync a complete temp file, link it exclusively, then fsync the directory."""
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".batch.", dir=str(directory))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, directory / name, follow_symlinks=False)
        _fsync_dir(directory)
    finally:
        os.unlink(temporary)


def _fsync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _proc_starttime(pid):
    try:
        raw = Path("/proc/%d/stat" % pid).read_text()
        fields = raw[raw.rfind(")") + 2:].split()
        return int(fields[19])
    except (OSError, ValueError, IndexError):
        return None


def run_batch(spec_path, output_dir, runner=subprocess.Popen, now=time.monotonic):
    """Run once in order; ``runner`` accepts Popen arguments for offline tests."""
    spec_path = str(Path(spec_path).resolve(strict=True))
    spec_raw = _read(spec_path, "batch spec")
    spec = _json(spec_raw, "batch spec")
    cases = validate_spec(spec)
    out = Path(output_dir)
    _need(out.is_absolute() and not out.exists() and not out.is_symlink(), "new output directory")
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    _fsync_dir(out.parent)
    results = []
    for cid, command, timeout, manifest, release, output_name in cases:
        started = now()
        record = {"case_id": cid, "manifest": manifest, "release": release,
                  "command": command, "started_monotonic": started,
                  "stdio": "discarded"}
        try:
            _need(_read(spec_path, "batch spec") == spec_raw, "batch spec drift")
            validate_spec(spec)
        except (BatchError, OSError) as exc:
            record.update({"returncode": None, "uncertain": False, "error": "PREFLIGHT_REFUSAL",
                           "reason": str(exc)})
        else:
            proc = None
            try:
                proc = runner(command, shell=False, stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              start_new_session=True, close_fds=True)
                try:
                    code = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    code = proc.poll()
                    if code is None:
                        record.update({"returncode": None, "uncertain": True,
                                       "error": "TIMED_OUT_OWNER_RETAINED",
                                       "launcher_pid": proc.pid,
                                       "launcher_starttime": _proc_starttime(proc.pid)})
                if "uncertain" not in record:
                    record.update({"returncode": code, "uncertain": False})
            except (OSError, subprocess.SubprocessError) as exc:
                record.update({"returncode": None, "uncertain": True,
                               "error": type(exc).__name__})
                if proc is not None:
                    record["launcher_pid"] = proc.pid
                    record["launcher_starttime"] = _proc_starttime(proc.pid)
            # The release, owner, and manifest are authoritative for the
            # invocation.  Re-check them after the owner returns as well as
            # before launch: a concurrent replacement must never turn a run
            # made against one identity into a durable PASS for another.
            try:
                _need(_read(spec_path, "batch spec") == spec_raw, "batch spec drift")
                validate_spec(spec)
            except (BatchError, OSError) as exc:
                # Never downgrade a timeout/launch uncertainty: the retained
                # owner identity is needed for safe cleanup even when a
                # second drift check also fails.
                record.update({"returncode": None,
                               "error": "POSTRUN_REFUSAL", "reason": str(exc)})
                if not record.get("uncertain", False):
                    record["uncertain"] = False
        record["elapsed_seconds"] = max(0.0, now() - started)
        _publish(out, output_name, record)
        results.append(record)
        if record["uncertain"] or record["returncode"] != 0:
            break
    summary = {"schema_version": 1, "kind": "native-diagnostic-batch-result",
               "stopped_on_failure": len(results) != len(cases) or
               results[-1]["uncertain"] or results[-1]["returncode"] != 0,
               "results": [item["case_id"] for item in results]}
    _publish(out, "batch-result.json", summary)
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    result = run_batch(args.spec, args.output_dir)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(1 if result["stopped_on_failure"] else 0)
