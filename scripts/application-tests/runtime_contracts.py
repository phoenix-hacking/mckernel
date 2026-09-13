"""Strict, read-only contracts for reviewed application execution artifacts.

This module does not launch a process, release a packet, manufacture capability
evidence, or accept McKernel provenance. PASS always names its narrower scope.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat


JSON_LIMIT_BYTES = 4 * 1024 * 1024
ARTIFACT_LIMIT_BYTES = 95 * 1024 * 1024 - 1
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_HEX = re.compile(r"(?:[0-9a-fA-F]{2})*\Z")
_CATALOG = Path(__file__).with_name("cases.json")
_INFRA = {
    "container_cpus": [2, 3, 4, 5], "container_memory_bytes": 12 * 1024 ** 3,
    "container_swap_bytes": 0, "container_tasks": 512,
    "linux_memory_bytes": 8 * 1024 ** 3, "linux_vcpus": 4,
    "mckernel_cpus": 1, "mckernel_memory_bytes": 128 * 1024 ** 2,
}


class ContractError(ValueError):
    """Malformed, stale, or internally inconsistent runtime metadata."""


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def _keys(value, required, optional=()):
    _require(isinstance(value, dict), "expected JSON object")
    _require(set(required) <= value.keys(), "missing fields: " + str(sorted(set(required) - value.keys())))
    _require(value.keys() <= set(required) | set(optional),
             "unknown fields: " + str(sorted(value.keys() - set(required) - set(optional))))


def _integer(value, low, high, name):
    _require(type(value) is int and low <= value <= high, name + " is outside its integer bound")


def _sha(value):
    _require(isinstance(value, str) and _SHA.fullmatch(value) is not None, "invalid SHA-256")


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def _float(value):
    result = float(value)
    _require(math.isfinite(result), "nonfinite JSON number")
    return result


def _constant(value):
    raise ContractError("nonfinite JSON constant: " + value)


def _int(value):
    _require(len(value) <= 21, "JSON integer exceeds 64-bit contract")
    result = int(value)
    _require(-(2 ** 63) <= result < 2 ** 64, "JSON integer exceeds 64-bit contract")
    return result


def strict_json_bytes(data):
    _require(isinstance(data, bytes) and len(data) <= JSON_LIMIT_BYTES, "JSON byte bound exceeded")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_float=_float, parse_int=_int, parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ContractError("invalid JSON: " + str(error)) from error


def load_json(path):
    try:
        path = os.fspath(path)
        _absolute(path, "JSON path")
        _require(str(Path(path).resolve(strict=True)) == path, "JSON path must be canonical without symlinks")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            _require(stat.S_ISREG(before.st_mode), "JSON must be a regular file")
            _require(before.st_size <= JSON_LIMIT_BYTES, "JSON byte bound exceeded")
            data = stream.read(JSON_LIMIT_BYTES + 1)
            after = os.fstat(stream.fileno())
            _require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                     (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "JSON changed while reading")
            return strict_json_bytes(data)
    except (OSError, RuntimeError) as error:
        raise ContractError("cannot read JSON: " + str(error)) from error


def verify_artifact(reference):
    """Stream a regular immutable artifact, rejecting stale size/hash or links."""
    _keys(reference, ("path", "size", "sha256"))
    _sha(reference["sha256"])
    _integer(reference["size"], 0, ARTIFACT_LIMIT_BYTES, "artifact size")
    path = reference["path"]
    _require(isinstance(path, str) and "\0" not in path and os.path.isabs(path),
             "artifact path must be absolute")
    try:
        _require(str(Path(path).resolve(strict=True)) == path, "artifact path must be canonical without symlinks")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            _require(stat.S_ISREG(before.st_mode), "artifact must be a regular file")
            _require(before.st_size == reference["size"], "artifact size mismatch: " + path)
            digest = hashlib.sha256()
            remaining = reference["size"]
            while remaining:
                block = stream.read(min(65536, remaining))
                _require(bool(block), "artifact shortened while hashing: " + path)
                digest.update(block)
                remaining -= len(block)
            _require(not stream.read(1), "artifact grew while hashing: " + path)
            after = os.fstat(stream.fileno())
            _require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                     (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "artifact changed while hashing")
            _require(digest.hexdigest() == reference["sha256"], "artifact SHA-256 mismatch: " + path)
    except (OSError, RuntimeError) as error:
        raise ContractError("cannot verify artifact: " + str(error)) from error
    return dict(reference)


def _artifact_json(reference):
    verify_artifact(reference)
    _require(reference["size"] <= JSON_LIMIT_BYTES, "manifest JSON bound exceeded")
    return strict_json_bytes(_verified_bytes(reference, JSON_LIMIT_BYTES))


def _verified_bytes(reference, maximum):
    """Reopen with a strict read bound; a replaced FIFO must never block."""
    try:
        fd = os.open(reference["path"], os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "artifact changed file type")
            data = stream.read(min(maximum, reference["size"]) + 1)
        _require(len(data) == reference["size"] and hashlib.sha256(data).hexdigest() == reference["sha256"],
                 "artifact changed after verification")
        return data
    except OSError as error:
        raise ContractError("cannot reopen artifact: " + str(error)) from error


def _header(value, kind, required, optional=()):
    _keys(value, ("schema_version", "kind") + tuple(required), optional)
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1, "unknown schema version")
    _require(value["kind"] == kind, "unexpected manifest kind")


def _argv(argv):
    _require(isinstance(argv, list) and bool(argv) and all(
        isinstance(arg, str) and "\0" not in arg for arg in argv), "argv must be literal strings without NUL")


def _absolute(path, name):
    _require(isinstance(path, str) and "\0" not in path and os.path.isabs(path), name + " must be absolute")


def _environment(value):
    _require(isinstance(value, dict) and all(
        isinstance(key, str) and key and "=" not in key and "\0" not in key
        and isinstance(item, str) and "\0" not in item for key, item in value.items()), "invalid explicit environment")


def _same_bytes(left, right):
    return (left["size"], left["sha256"]) == (right["size"], right["sha256"])


def load_runtime_bundle(path):
    """Validate frozen identities and structure; unresolved capabilities remain blocked.

    Raises ContractError on malformed metadata or stale evidence. Use
    validate_case() to inspect a selected case's capability/review eligibility.
    """
    bundle = load_json(path)
    _header(bundle, "runtime-bundle", ("selected_inputs", "capabilities", "execution_packet"))
    inputs = _artifact_json(bundle["selected_inputs"])
    caps = _artifact_json(bundle["capabilities"])
    packet = _artifact_json(bundle["execution_packet"])
    selected_hash = bundle["selected_inputs"]["sha256"]
    _header(inputs, "selected-inputs", ("source", "artifacts", "profile", "payloads"))
    _keys(inputs["source"], ("commit", "dirty_diff", "compiler_bindings"))
    _require(isinstance(inputs["source"]["commit"], str) and
             re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", inputs["source"]["commit"]) is not None,
             "invalid source commit identity")
    verify_artifact(inputs["source"]["dirty_diff"])
    verify_artifact(inputs["source"]["compiler_bindings"])
    artifacts = inputs["artifacts"]
    _keys(artifacts, ("linux_kernel", "mckernel_image", "native_modules", "launcher", "compiler"))
    for name in ("linux_kernel", "mckernel_image", "launcher", "compiler"):
        verify_artifact(artifacts[name])
    modules = artifacts["native_modules"]
    _require(isinstance(modules, list) and len(modules) == 3, "exactly three native modules required")
    for module in modules:
        verify_artifact(module)
    _require({Path(module["path"]).name for module in modules} ==
             {"ihk.ko", "ihk-smp-x86_64.ko", "mcctrl.ko"}, "native module inventory differs")
    profile = inputs["profile"]
    _keys(profile, tuple(_INFRA) + ("profile_id", "network", "uid", "gid", "groups", "umask", "qemu_argv"))
    _require(profile["profile_id"] == "baseline-root-1cpu", "unsupported execution profile")
    for name, expected in _INFRA.items():
        _require(type(profile[name]) is type(expected) and profile[name] == expected, "profile limit differs: " + name)
        if isinstance(expected, list):
            _require(all(type(item) is int for item in profile[name]), "CPU IDs must be integers")
    _require(profile["network"] == "none", "network must remain disabled")
    _require(type(profile["uid"]) is int and type(profile["gid"]) is int and
             profile["uid"] == 0 and profile["gid"] == 0 and profile["groups"] == [0]
             and type(profile["groups"][0]) is int, "root identity profile differs")
    _require(isinstance(profile["umask"], str) and re.fullmatch(r"0[0-7]{3}", profile["umask"]) is not None,
             "umask must be four octal digits")
    _argv(profile["qemu_argv"])
    _absolute(profile["qemu_argv"][0], "QEMU executable")
    _require(isinstance(inputs["payloads"], dict) and bool(inputs["payloads"]), "missing payload inventory")
    for payload in inputs["payloads"].values():
        _keys(payload, ("source", "executable", "executable_path", "argv", "env", "cwd", "interpreter", "dsos", "stdin"))
        verify_artifact(payload["source"])
        verify_artifact(payload["executable"])
        _absolute(payload["executable_path"], "payload executable_path")
        _absolute(payload["cwd"], "payload cwd")
        _argv(payload["argv"])
        _environment(payload["env"])
        _require(isinstance(payload["dsos"], list), "DSO inventory must be a list")
        for dependency in payload["dsos"]:
            verify_artifact(dependency)
        for name in ("interpreter", "stdin"):
            if payload[name] is not None:
                verify_artifact(payload[name])
    _header(caps, "runtime-capabilities", ("selected_inputs_sha256", "capabilities"))
    _require(caps["selected_inputs_sha256"] == selected_hash, "capability/input binding differs")
    _require(isinstance(caps["capabilities"], dict), "capability map required")
    catalog_bytes = _CATALOG.read_bytes()
    catalog = strict_json_bytes(catalog_bytes)
    known_cases = {case["id"]: case for case in catalog["cases"]}
    for name, capability in caps["capabilities"].items():
        _require(name in catalog["capabilities"], "unknown capability: " + name)
        _keys(capability, ("state", "contract", "evidence"), ("reason",))
        _require(capability["state"] in ("verified", "blocked", "unsupported"), "unknown capability state")
        _require(isinstance(capability["contract"], str) and bool(capability["contract"]), "missing capability contract")
        _require(isinstance(capability["evidence"], list), "capability evidence must be a list")
        if capability["state"] == "verified":
            _require(bool(capability["evidence"]), "verified capability requires actual bound evidence")
        else:
            _require(isinstance(capability.get("reason"), str) and bool(capability["reason"]), "blocked capability requires a reason")
        for reference in capability["evidence"]:
            evidence = _artifact_json(reference)
            _header(evidence, "capability-evidence", ("status", "review_status", "selected_inputs_sha256", "capability", "artifacts"))
            _require(evidence["status"] in ("PASS", "FAIL", "BLOCKED", "NOT_RUN"), "unknown evidence status")
            _require(evidence["selected_inputs_sha256"] == selected_hash and evidence["capability"] == name,
                     "capability evidence binding differs")
            _require(evidence["review_status"] == "REVIEWED", "capability evidence is not reviewed")
            _require(isinstance(evidence["artifacts"], list) and bool(evidence["artifacts"]), "capability proof artifacts required")
            for proof in evidence["artifacts"]:
                verify_artifact(proof)
            if capability["state"] == "verified":
                _require(evidence["status"] == "PASS", "verified capability has nonpassing evidence")
    _header(packet, "execution-packet", ("packet_id", "version", "catalog_sha256", "selected_inputs_sha256",
                                         "capabilities_sha256", "mode", "execution_enabled", "review_status", "cases"))
    _require(isinstance(packet["packet_id"], str) and re.fullmatch(r"[a-z0-9][a-z0-9.-]*", packet["packet_id"]) is not None,
             "invalid packet ID")
    _integer(packet["version"], 1, 2 ** 31 - 1, "packet version")
    _require(packet["catalog_sha256"] == hashlib.sha256(catalog_bytes).hexdigest(), "stale catalog hash")
    _require(packet["selected_inputs_sha256"] == selected_hash and
             packet["capabilities_sha256"] == bundle["capabilities"]["sha256"], "packet/input/capability binding differs")
    _require(packet["mode"] == "differential-guest", "unsupported packet execution mode")
    _require(type(packet["execution_enabled"]) is bool, "execution_enabled must be boolean")
    _require(packet["review_status"] in ("REVIEWED", "PENDING"), "unknown review state")
    _require(isinstance(packet["cases"], list) and 1 <= len(packet["cases"]) <= 3, "packet must select one to three cases")
    selected = {}
    oracles = {}
    for case in packet["cases"]:
        _keys(case, ("case_id", "source", "oracle", "review_status", "assertions_reviewed", "parameters_reviewed", "limits"))
        case_id = case["case_id"]
        _require(isinstance(case_id, str) and case_id in known_cases and case_id not in selected, "unknown or duplicate selected case")
        _require(case_id in inputs["payloads"], "selected payload is missing")
        _require(case["review_status"] in ("REVIEWED", "PENDING"), "unknown source review state")
        _require(type(case["assertions_reviewed"]) is bool and type(case["parameters_reviewed"]) is bool,
                 "source assertion/parameter review must be explicit")
        verify_artifact(case["source"])
        _require(_same_bytes(case["source"], inputs["payloads"][case_id]["source"]), "reviewed/compiled source identity differs")
        expected_limits = known_cases[case_id]["limits"]
        _keys(case["limits"], expected_limits)
        for name, expected in expected_limits.items():
            actual = case["limits"][name]
            if isinstance(expected, list):
                _require(actual == expected and all(type(item) is int for item in actual), "CPU set differs")
            else:
                _integer(actual, 0, expected, "case limit " + name)
                if expected > 0:
                    _require(actual > 0, "positive case limit required: " + name)
            if name in _INFRA:
                _require(actual == profile[name], "case/profile limits differ: " + name)
        oracle = _artifact_json(case["oracle"])
        _header(oracle, "independent-oracle", ("case_id", "version", "source_sha256", "review_status", "wait_status", "stdout", "stderr", "predicates"))
        _require(oracle["case_id"] == case_id and oracle["source_sha256"] == case["source"]["sha256"], "oracle source/case binding differs")
        _integer(oracle["version"], 1, 2 ** 31 - 1, "oracle version")
        _require(oracle["review_status"] in ("REVIEWED", "PENDING"), "unknown oracle review state")
        _require(isinstance(oracle["predicates"], list), "oracle predicates must be a list")
        selected[case_id] = case
        oracles[case_id] = oracle
    _require(inputs["payloads"].keys() == selected.keys(), "payload inventory must exactly match selected cases")
    return {"bundle": bundle, "inputs": inputs, "capabilities": caps, "packet": packet,
            "cases": selected, "oracles": oracles, "catalog": known_cases,
            "global_execution_gates": catalog["global_execution_gates"]}


def _decision(status, scope, reasons):
    return {"status": status, "scope": scope, "reasons": reasons, "application_acceptance": False}


def _oracle_support(oracle, case):
    reasons = []
    if oracle["predicates"]:
        reasons.append("additional oracle predicates are not implemented")
    wait = oracle["wait_status"]
    _require(isinstance(wait, dict) and isinstance(wait.get("kind"), str), "invalid wait oracle")
    if wait["kind"] == "exited":
        _keys(wait, ("kind", "code"))
        _integer(wait["code"], 0, 255, "exit code")
    elif wait["kind"] == "signaled":
        _keys(wait, ("kind", "signal"))
        _integer(wait["signal"], 1, 64, "signal")
    else:
        reasons.append("unsupported wait-status predicate")
    for name in ("stdout", "stderr"):
        rule = oracle[name]
        _require(isinstance(rule, dict) and isinstance(rule.get("kind"), str), "invalid stream oracle")
        if rule["kind"] == "exact-bytes":
            _keys(rule, ("kind", "hex"))
            _require(isinstance(rule["hex"], str) and _HEX.fullmatch(rule["hex"]) is not None, "invalid exact byte hex")
            _require(len(rule["hex"]) // 2 <= case["limits"][name + "_limit_bytes"], "oracle exceeds stream bound")
        elif rule["kind"] == "json-equals":
            _keys(rule, ("kind", "value"))
        else:
            reasons.append("unsupported " + name + " predicate: " + rule["kind"])
    return reasons


def validate_case(bundle, case_id):
    """Report metadata eligibility only; unsupported/missing capabilities block."""
    if not isinstance(case_id, str) or case_id not in bundle["cases"]:
        return _decision("BLOCKED", "runtime-contract-metadata", ["case is not in the reviewed active packet"])
    case = bundle["cases"][case_id]
    oracle = bundle["oracles"][case_id]
    reasons = []
    if not bundle["packet"]["execution_enabled"]:
        reasons.append("packet execution remains disabled")
    if any(state != "REVIEWED" for state in (bundle["packet"]["review_status"], case["review_status"], oracle["review_status"])):
        reasons.append("packet/source/oracle review is incomplete")
    if not case["assertions_reviewed"] or not case["parameters_reviewed"]:
        reasons.append("source assertions or complete parameter coverage are not reviewed")
    required = set(bundle["global_execution_gates"]) | set(bundle["catalog"][case_id]["requires"])
    dependencies = bundle["catalog"][case_id]["depends_on"]
    if dependencies:
        reasons.append("case dependency acceptance is not implemented: " + ", ".join(dependencies))
    for capability in sorted(required):
        record = bundle["capabilities"]["capabilities"].get(capability)
        if record is None or record["state"] != "verified":
            reasons.append("capability is missing, blocked, or unsupported: " + capability)
    try:
        verify_artifact(case["source"])
        verify_artifact(case["oracle"])
        verify_artifact(bundle["inputs"]["payloads"][case_id]["executable"])
        reasons.extend(_oracle_support(oracle, case))
    except ContractError as error:
        return _decision("FAIL", "runtime-contract-metadata", [str(error)])
    return _decision("BLOCKED" if reasons else "PASS", "runtime-contract-metadata", reasons)


def evaluate_case(bundle, case_id, collection_report, *, evidence=None):
    """Evaluate the supported independent oracle; never infer OS acceptance.

    evidence is reserved for a later reviewed provenance/resource evaluator.
    Its presence cannot turn printed markers or successful collection into
    McKernel verification. Unknown extra predicates always remain BLOCKED.
    """
    del evidence
    eligibility = validate_case(bundle, case_id)
    if eligibility["status"] != "PASS":
        return eligibility
    oracle = bundle["oracles"][case_id]
    case = bundle["cases"][case_id]
    payload = bundle["inputs"]["payloads"][case_id]
    report = collection_report
    try:
        _require(isinstance(report, dict), "collection report must be an object")
        _require(type(report.get("schema_version")) is int and report["schema_version"] == 1,
                 "unknown collection schema version")
        _require(report.get("status") == "COMPLETED", "process collection did not complete normally")
        _require(report.get("cleanup_complete") is True, "owned process cleanup is incomplete")
        for name in ("argv", "executable_path", "cwd", "env"):
            _require(report.get(name) == payload[name], "collection launch contract differs: " + name)
        for name in ("uid", "gid"):
            _integer(report.get(name), 0, 2 ** 32 - 1, "collection " + name)
        _require(isinstance(report.get("groups"), list) and all(type(group) is int for group in report["groups"]),
                 "collection groups must be integer IDs")
        for name in ("uid", "gid", "groups", "umask"):
            _require(report.get(name) == bundle["inputs"]["profile"][name], "collection identity differs: " + name)
        for report_name, limit_name in (("timeout_seconds", "payload_timeout_seconds"),
                                        ("cleanup_timeout_seconds", "cleanup_timeout_seconds")):
            value = report.get(report_name)
            _require(type(value) in (float, int) and math.isfinite(value) and
                     0 < value <= case["limits"][limit_name], "collection deadline exceeds packet bound")
        times = {}
        for name in ("payload_monotonic_started", "payload_monotonic_deadline", "payload_completion_observed_monotonic"):
            value = report.get(name)
            _require(type(value) in (float, int) and math.isfinite(value) and value >= 0,
                     "missing or invalid completion observation time: " + name)
            times[name] = value
        _require(times["payload_monotonic_deadline"] == times["payload_monotonic_started"] + report["timeout_seconds"],
                 "collector deadline does not match its declared payload timeout")
        _require(times["payload_monotonic_started"] <= times["payload_completion_observed_monotonic"] <=
                 times["payload_monotonic_deadline"], "completion was not observed within its deadline")
        stdin = report.get("stdin")
        _require(isinstance(stdin, dict), "collection stdin identity is missing")
        if payload["stdin"] is None:
            _keys(stdin, ("kind",))
            _require(stdin.get("kind") == "devnull", "stdin differs from reviewed /dev/null setup")
        else:
            _keys(stdin, ("kind", "path", "size", "sha256"))
            _absolute(stdin["path"], "collected stdin path")
            _integer(stdin["size"], 0, ARTIFACT_LIMIT_BYTES, "collected stdin size")
            _sha(stdin["sha256"])
            _require(stdin.get("kind") == "file" and _same_bytes(stdin, payload["stdin"]), "stdin identity differs")
        executable = report.get("executable")
        _keys(executable, ("path", "size", "sha256"))
        _absolute(executable["path"], "collected executable path")
        _integer(executable["size"], 0, ARTIFACT_LIMIT_BYTES, "collected executable size")
        _sha(executable["sha256"])
        _require(_same_bytes(executable, payload["executable"]), "collected executable identity differs")
        raw = report.get("raw_wait_status")
        _integer(raw, 0, 65535, "raw wait status")
        if os.WIFEXITED(raw):
            actual_wait = {"kind": "exited", "code": os.WEXITSTATUS(raw)}
        elif os.WIFSIGNALED(raw):
            actual_wait = {"kind": "signaled", "signal": os.WTERMSIG(raw)}
        else:
            raise ContractError("raw wait status is not a terminal exit or signal")
        decoded = report.get("wait_status")
        _keys(decoded, actual_wait, ("core_dumped",))
        for name in ("code", "signal"):
            if name in actual_wait:
                _require(type(decoded[name]) is int, "decoded wait value must be an integer")
        if "core_dumped" in decoded:
            _require(type(decoded["core_dumped"]) is bool and decoded["core_dumped"] == bool(os.WCOREDUMP(raw)),
                     "decoded core-dump flag differs from raw wait status")
        _require(all(decoded[key] == value for key, value in actual_wait.items()),
                 "decoded and raw wait status disagree")
        _require(actual_wait == oracle["wait_status"], "raw wait status differs from independent oracle")
        _keys(report.get("streams"), ("stdout", "stderr"))
        for name in ("stdout", "stderr"):
            stream = report["streams"][name]
            _keys(stream, ("artifact", "truncated", "eof", "bytes_observed", "bytes_retained",
                           "discarded_observed_bytes", "limit_bytes"))
            _require(stream.get("truncated") is False and stream.get("eof") is True, "stream is truncated or incomplete: " + name)
            artifact = verify_artifact(stream.get("artifact"))
            _require(artifact["size"] <= case["limits"][name + "_limit_bytes"], "collected stream exceeds packet bound")
            _integer(stream.get("limit_bytes"), 0, case["limits"][name + "_limit_bytes"], "stream collection limit")
            _require(artifact["size"] <= stream["limit_bytes"], "stream exceeds its collector limit")
            _require(type(stream.get("bytes_observed")) is int and type(stream.get("bytes_retained")) is int and
                     stream["bytes_observed"] == stream["bytes_retained"] == artifact["size"] and
                     type(stream["discarded_observed_bytes"]) is int and
                     stream["discarded_observed_bytes"] == 0, "stream byte accounting differs")
            observed = _verified_bytes(artifact, case["limits"][name + "_limit_bytes"])
            rule = oracle[name]
            if rule["kind"] == "exact-bytes":
                _require(observed == bytes.fromhex(rule["hex"]), name + " differs from exact independent bytes")
            else:
                actual = strict_json_bytes(observed)
                _require(json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False) ==
                         json.dumps(rule["value"], sort_keys=True, separators=(",", ":"), allow_nan=False),
                         name + " differs from independent JSON value/types")
    except (ContractError, KeyError, TypeError, OSError, ValueError) as error:
        return _decision("FAIL", "independent-oracle", [str(error)])
    return _decision("PASS", "independent-oracle", ["McKernel provenance and full runtime acceptance remain separately required"])
