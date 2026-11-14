#!/usr/bin/env python3
"""Bounded Linux diagnostic, never McKernel application acceptance.

The exclusive failure sidecar is an append-only JSON-lines journal. Each event
is fsynced before attempting any subsequent evidence publication. It preserves
the first exception even if creating the evaluation file subsequently fails.
Inputs must live in a controlled filesystem: these pathname checks detect
changes around execution; they are not an adversarial filesystem sandbox.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import NamedTuple


_HERE = Path(__file__).resolve().parent


def _module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contracts = _module("linux_diagnostic_runtime_contracts", "runtime_contracts.py")
supervisor = _module("linux_diagnostic_supervisor", "supervisor.py")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, required):
    _require(isinstance(value, dict) and set(value) == set(required),
             "object keys differ from required schema: " + str(tuple(required)))


def _integer(value, low, high, label):
    _require(type(value) is int and low <= value <= high, label + " invalid integer")


def _canonical(value, label):
    _require(isinstance(value, str) and "\0" not in value and os.path.isabs(value),
             label + " must be absolute")
    path = Path(value)
    _require(str(path.resolve(strict=True)) == value, label + " must be canonical without symlinks")
    return path


def _metadata(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


class Snapshot(NamedTuple):
    path: str
    data: bytes
    identity: tuple

    def reference(self):
        return {"path": self.path, "size": len(self.data),
                "sha256": hashlib.sha256(self.data).hexdigest()}


def _snapshot(path, maximum, reference=None):
    _canonical(path, "artifact path")
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        _require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
                 "artifact must be a bounded regular file")
        data = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    _canonical(path, "artifact path")
    _require(_metadata(before) == _metadata(after) == _metadata(os.stat(path, follow_symlinks=False))
             and len(data) == before.st_size, "artifact changed during read")
    result = Snapshot(path, data, _metadata(before))
    if reference is not None:
        _require(result.reference() == reference, "artifact size/hash/path mismatch")
    return result


def _ref(value, maximum=None):
    _keys(value, ("path", "size", "sha256"))
    _integer(value["size"], 0, contracts.ARTIFACT_LIMIT_BYTES, "artifact size")
    digest = value["sha256"]
    _require(isinstance(digest, str) and len(digest) == 64
             and all(c in "0123456789abcdef" for c in digest), "invalid SHA256")
    return _snapshot(value["path"], contracts.ARTIFACT_LIMIT_BYTES if maximum is None else maximum, value)


def _wait(value):
    _require(isinstance(value, dict), "wait must be an object")
    if value.get("kind") == "exited":
        _keys(value, ("kind", "code"))
        _integer(value["code"], 0, 255, "exit code")
    elif value.get("kind") == "signaled":
        _keys(value, ("kind", "signal"))
        _integer(value["signal"], 1, 64, "signal")
    else:
        raise ValueError("unknown terminal wait kind")
    return value


def _attempt(value):
    _require(isinstance(value, str) and "\0" not in value and os.path.isabs(value),
             "attempt must be absolute")
    path = Path(value)
    _require(str(path) == value and path.name not in ("", ".", ".."), "attempt spelling must be canonical")
    parent = _canonical(str(path.parent), "attempt parent")
    _require(parent.is_dir() and not os.path.lexists(value), "attempt must have an existing parent and fresh child")
    return path


class LoadedRequest(NamedTuple):
    request: Snapshot
    inputs: tuple
    oracle: bytes
    parent_identity: tuple


def load_request(path):
    snapshot = _snapshot(os.fspath(path), contracts.JSON_LIMIT_BYTES)
    request = contracts.strict_json_bytes(snapshot.data)
    _keys(request, ("schema_version", "kind", "case_id", "source", "oracle", "payload",
                    "argv", "executable_path", "cwd", "env", "stdin", "timeout_seconds",
                    "cleanup_timeout_seconds", "stdout_limit_bytes", "stderr_limit_bytes",
                    "application_acceptance", "mckernel_application_executed", "attempt"))
    _integer(request["schema_version"], 1, 1, "request schema")
    _require(request["kind"] == "linux-diagnostic-request", "wrong request kind")
    _require(isinstance(request["case_id"], str) and request["case_id"] and "\0" not in request["case_id"], "invalid case_id")
    inputs = tuple(_ref(request[name], contracts.JSON_LIMIT_BYTES if name == "oracle" else None)
                   for name in ("source", "oracle", "payload"))
    argv = request["argv"]
    _require(isinstance(argv, list) and argv and all(isinstance(arg, str) and "\0" not in arg for arg in argv), "invalid literal argv")
    _canonical(request["executable_path"], "executable")
    _require(request["payload"]["path"] == request["executable_path"], "payload path must equal executable_path")
    _require(_canonical(request["cwd"], "cwd").is_dir(), "cwd must be a directory")
    env = request["env"]
    _require(isinstance(env, dict) and all(isinstance(k, str) and k and "=" not in k and "\0" not in k
             and isinstance(v, str) and "\0" not in v for k, v in env.items()), "invalid environment")
    if request["stdin"] is not None:
        inputs += (_ref(request["stdin"]),)
    for name in ("timeout_seconds", "cleanup_timeout_seconds"):
        value = request[name]
        _require(type(value) in (int, float) and 0 < value <= 3600 and math.isfinite(value), "invalid " + name)
    for name in ("stdout_limit_bytes", "stderr_limit_bytes"):
        _integer(request[name], 0, contracts.ARTIFACT_LIMIT_BYTES, name)
    for name in ("application_acceptance", "mckernel_application_executed"):
        _require(request[name] is False, "diagnostic flags must be false")
    oracle = contracts.strict_json_bytes(inputs[1].data)
    _keys(oracle, ("schema_version", "kind", "case_id", "wait_status", "stdout_hex", "stderr_hex"))
    _integer(oracle["schema_version"], 1, 1, "oracle schema")
    _require(oracle["kind"] == "linux-diagnostic-oracle" and oracle["case_id"] == request["case_id"], "oracle identity differs")
    _wait(oracle["wait_status"])
    for name in ("stdout", "stderr"):
        value = oracle[name + "_hex"]
        _require(isinstance(value, str) and len(value) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in value), "invalid oracle hex")
        _require(len(value) // 2 <= request[name + "_limit_bytes"], "oracle exceeds stream limit")
    attempt = _attempt(request["attempt"])
    parent = os.stat(attempt.parent, follow_symlinks=False)
    return LoadedRequest(snapshot, inputs, inputs[1].data, (parent.st_dev, parent.st_ino))


def _unchanged(loaded):
    for previous in (loaded.request,) + loaded.inputs:
        current = _snapshot(previous.path, max(len(previous.data), 1), previous.reference())
        _require(current.identity == previous.identity, "input identity changed: " + previous.path)


def _check_report(request, oracle, observed):
    _require(isinstance(observed, dict), "supervisor report must be an object")
    _integer(observed.get("schema_version"), 1, 1, "report schema")
    _require(observed.get("status") == "COMPLETED", "status is not COMPLETED")
    _require(observed.get("cleanup_complete") is True, "cleanup incomplete")
    _require(observed.get("application_acceptance") is False, "supervisor acceptance flag changed")
    for name in ("argv", "executable_path", "cwd", "env"):
        _require(observed.get(name) == request[name], "launch contract mismatch: " + name)
    for name in ("timeout_seconds", "cleanup_timeout_seconds"):
        value = observed.get(name)
        _require(type(value) in (int, float) and math.isfinite(value) and value == request[name], "deadline mismatch")
    _ref(observed.get("executable"))
    _require(observed["executable"] == request["payload"], "executable identity differs from payload")
    stdin = observed.get("stdin")
    if request["stdin"] is None:
        _keys(stdin, ("kind",))
        _require(stdin["kind"] == "devnull", "stdin differs from devnull")
    else:
        _keys(stdin, ("kind", "path", "size", "sha256"))
        reference = {key: stdin[key] for key in ("path", "size", "sha256")}
        _ref(reference)
        _require(stdin["kind"] == "file" and reference == request["stdin"], "stdin identity differs")
    raw = observed.get("raw_wait_status")
    _integer(raw, 0, 65535, "raw wait status")
    if os.WIFEXITED(raw):
        actual = {"kind": "exited", "code": os.WEXITSTATUS(raw)}
    elif os.WIFSIGNALED(raw):
        actual = {"kind": "signaled", "signal": os.WTERMSIG(raw)}
    else:
        raise ValueError("raw wait status is not terminal")
    _wait(actual)
    decoded = observed.get("wait_status")
    _require(isinstance(decoded, dict), "decoded wait must be an object")
    decoded = dict(decoded)
    if actual["kind"] == "signaled":
        _require(type(decoded.get("core_dumped")) is bool and decoded["core_dumped"] == bool(os.WCOREDUMP(raw)), "core-dump status mismatch")
        del decoded["core_dumped"]
    _wait(decoded)
    _require(actual == decoded, "raw/decoded wait contradiction")
    _require(actual == oracle["wait_status"], "wait differs from oracle")
    _keys(observed.get("streams"), ("stdout", "stderr"))
    for name in ("stdout", "stderr"):
        stream = observed["streams"][name]
        _keys(stream, ("artifact", "eof", "truncated", "bytes_observed", "bytes_retained", "discarded_observed_bytes", "limit_bytes"))
        _require(stream["eof"] is True and stream["truncated"] is False, name + " incomplete")
        limit = request[name + "_limit_bytes"]
        for key in ("bytes_observed", "bytes_retained", "discarded_observed_bytes", "limit_bytes"):
            _integer(stream[key], 0, limit, name + " " + key)
        _require(stream["limit_bytes"] == limit, name + " collection limit differs")
        artifact = _ref(stream["artifact"], limit)
        _require(artifact.path == str(Path(request["attempt"]) / (name + ".bin")), name + " artifact path differs")
        _require(stream["bytes_observed"] == stream["bytes_retained"] == len(artifact.data)
                 and stream["discarded_observed_bytes"] == 0, name + " accounting differs")
        _require(artifact.data == bytes.fromhex(oracle[name + "_hex"]), name + " bytes differ from oracle")


def _event(stream, value):
    stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def _publish(attempt, result):
    # mkdir is exclusive when setup failed before the supervisor created it.
    if not os.path.lexists(attempt):
        attempt.mkdir(mode=0o700)
    _require(_canonical(str(attempt), "attempt").is_dir(), "attempt is not a directory")
    with (attempt / "diagnostic-evaluation.json").open("x", encoding="utf-8") as stream:
        _event(stream, result)


def evaluate(loaded, request_path):
    _require(isinstance(loaded, LoadedRequest), "evaluate requires a validated request snapshot")
    _require(os.fspath(request_path) == loaded.request.path, "request path differs from snapshot")
    request = contracts.strict_json_bytes(loaded.request.data)
    oracle = contracts.strict_json_bytes(loaded.oracle)
    attempt = _attempt(request["attempt"])
    parent = os.stat(attempt.parent, follow_symlinks=False)
    _require((parent.st_dev, parent.st_ino) == loaded.parent_identity, "attempt parent identity changed")
    sidecar = attempt.parent / (attempt.name + ".diagnostic-failure.jsonl")
    fd = os.open(str(sidecar), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as journal:
        result = {"schema_version": 1, "kind": "linux-diagnostic-evaluation", "case_id": request["case_id"],
                  "request": loaded.request.reference(), "request_identity": list(loaded.request.identity),
                  "source": request["source"], "oracle": request["oracle"], "payload": request["payload"],
                  "failure_journal": str(sidecar), "status": "FAIL", "reasons": [], "observed": None,
                  "application_acceptance": False, "mckernel_application_executed": False}
        _event(journal, {"event": "reserved", "request": result["request"], "status": "SETUP_PENDING",
                         "application_acceptance": False, "mckernel_application_executed": False})
        directory_fd = os.open(str(attempt.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        try:
            _unchanged(loaded)
            result["observed"] = supervisor.run_supervised(request["argv"], cwd=request["cwd"], env=request["env"],
                attempt_dir=str(attempt), timeout_seconds=request["timeout_seconds"],
                cleanup_timeout_seconds=request["cleanup_timeout_seconds"],
                stdout_limit_bytes=request["stdout_limit_bytes"], stderr_limit_bytes=request["stderr_limit_bytes"],
                stdin_path=request["stdin"]["path"] if request["stdin"] is not None else None,
                executable_path=request["executable_path"])
            _unchanged(loaded)
            _check_report(request, oracle, result["observed"])
            result["status"] = "PASS"
        except Exception as error:
            result["reasons"].append(type(error).__name__ + ": " + str(error))
            _event(journal, {"event": "collection_failure", "status": "FAIL", "error": result["reasons"][0]})
        _event(journal, {"event": "evaluation", "status": result["status"], "reasons": list(result["reasons"])})
        try:
            _publish(attempt, result)
        except Exception as error:
            result["status"] = "FAIL"
            result["reasons"].append("publication failure: " + type(error).__name__ + ": " + str(error))
            _event(journal, {"event": "publication_failure", "status": "FAIL", "error": result["reasons"][-1]})
        return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(load_request(args.request), args.request)
    except Exception as error:
        print("diagnostic request rejected: {}".format(error), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
