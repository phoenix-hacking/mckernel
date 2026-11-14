#!/usr/bin/env python3
"""Retain and validate runtime metadata; application execution is not implemented."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("application_preflight_contracts", _HERE / "runtime_contracts.py")
contracts = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(contracts)

MAX_REFERENCES = 256
MAX_RETAINED_BYTES = 95 * 1024**2
_BACKEND_REASON = "execution backend, paired guest evidence and runtime release are not implemented"


def require(condition, message):
    if not condition:
        raise contracts.ContractError(message)


def canonical(path):
    value = os.fspath(path)
    require(isinstance(value, str) and 0 < len(value) <= 4096 and "\0" not in value,
            "invalid input pathname")
    require(os.path.isabs(value) and str(Path(value).resolve(strict=True)) == value,
            "input pathname must be absolute, canonical and nonsymlink")
    return value


def fresh_attempt(path):
    value = os.fspath(path)
    require(isinstance(value, str) and "\0" not in value and os.path.isabs(value),
            "attempt must be an absolute pathname")
    target = Path(value)
    require(str(target) == value and target.name not in ("", ".", ".."), "noncanonical attempt pathname")
    canonical(str(target.parent))
    target.mkdir(mode=0o700)  # Exclusive: no parents/exist_ok and no overwrite.
    return target


def publish(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    require(len(data) <= contracts.JSON_LIMIT_BYTES, "preflight report JSON limit exceeded")
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest())


class InputCapture:
    """Retain schema-declared references, never execute or interpret opaque proof."""

    def __init__(self, attempt):
        self.directory = attempt / "inputs"
        self.directory.mkdir(mode=0o700)
        self.rows = []
        self.by_path = {}
        self.documents = {}
        self.reserved_bytes = 0
        self.reference_uses = 0

    def take(self, path, expected=None, maximum=contracts.ARTIFACT_LIMIT_BYTES):
        require(self.reference_uses < MAX_REFERENCES, "input reference count limit exceeded")
        self.reference_uses += 1
        path = canonical(path)
        if expected is not None:
            require(type(expected) is dict and set(expected) == {"path", "size", "sha256"},
                    "invalid artifact reference fields")
            require(type(expected["size"]) is int and 0 <= expected["size"] <= maximum,
                    "artifact declared size exceeds bound")
            require(type(expected["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", expected["sha256"]),
                    "invalid artifact SHA256")
            require(expected["path"] == path, "artifact pathname differs")
        if path in self.by_path:
            row = self.by_path[path]
            require(row["capture_status"] == "COMPLETE", "prior capture of input failed")
            require(row["original"]["size"] <= maximum, "manifest JSON byte limit exceeded")
            require(expected is None or row["original"] == expected, "conflicting identities for one input path")
            return row
        require(len(self.rows) < MAX_REFERENCES, "input reference count limit exceeded")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            before = os.fstat(source.fileno())
            require(stat.S_ISREG(before.st_mode), "input must be a regular file")
            require(0 <= before.st_size <= maximum, "input file size limit exceeded")
            require(expected is None or before.st_size == expected["size"], "input declared size differs")
            require(self.reserved_bytes + before.st_size <= MAX_RETAINED_BYTES, "aggregate input byte limit exceeded")
            self.reserved_bytes += before.st_size
            destination = self.directory / ("{:03d}.bin".format(len(self.rows)))
            row = dict(original_path=path, declared_size=before.st_size,
                       retained_path=str(destination), capture_status="PARTIAL")
            self.rows.append(row)
            self.by_path[path] = row
            try:
                digest = hashlib.sha256()
                with destination.open("xb") as output:
                    remaining = before.st_size
                    while remaining:
                        data = source.read(min(65536, remaining))
                        require(bool(data), "input shortened during capture")
                        output.write(data)
                        digest.update(data)
                        remaining -= len(data)
                    extra = source.read(1)
                    row["growth_byte_observed_but_not_retained"] = bool(extra)
                    require(not extra, "input grew during capture")
                    output.flush()
                    os.fsync(output.fileno())
                after = os.fstat(source.fileno())
                require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                        "input changed during capture")
                require(canonical(path) == path, "input pathname changed during capture")
                original = dict(path=path, size=before.st_size, sha256=digest.hexdigest())
                require(expected is None or original == expected, "input SHA256 differs from frozen identity")
                row["original"] = original
            finally:
                # Re-read actual retained bytes, including a failed partial copy.
                # A storage failure here propagates; it cannot claim full capture.
                if destination.exists():
                    observed = hashlib.sha256()
                    size = 0
                    with destination.open("rb") as retained:
                        for data in iter(lambda: retained.read(65536), b""):
                            size += len(data)
                            observed.update(data)
                    row["retained"] = dict(path=str(destination), size=size, sha256=observed.hexdigest())
            require(row["retained"]["size"] == row["original"]["size"] and
                    row["retained"]["sha256"] == row["original"]["sha256"], "retained input differs")
            row["capture_status"] = "COMPLETE"
            return row

    def artifact(self, reference, document=False):
        require(type(reference) is dict and "path" in reference, "artifact reference required")
        row = self.take(reference["path"], reference,
                        contracts.JSON_LIMIT_BYTES if document else contracts.ARTIFACT_LIMIT_BYTES)
        if not document:
            return row
        if reference["path"] not in self.documents:
            self.documents[reference["path"]] = contracts.load_json(row["retained"]["path"])
        return self.documents[reference["path"]]

    def graph(self, bundle):
        inputs = self.artifact(bundle["selected_inputs"], document=True)
        caps = self.artifact(bundle["capabilities"], document=True)
        packet = self.artifact(bundle["execution_packet"], document=True)
        for name in ("dirty_diff", "compiler_bindings"):
            self.artifact(inputs["source"][name])
        for name in ("linux_kernel", "mckernel_image", "launcher", "compiler"):
            self.artifact(inputs["artifacts"][name])
        for reference in inputs["artifacts"]["native_modules"]:
            self.artifact(reference)
        for payload in inputs["payloads"].values():
            for name in ("source", "executable"):
                self.artifact(payload[name])
            for name in ("interpreter", "stdin"):
                if payload[name] is not None:
                    self.artifact(payload[name])
            for reference in payload["dsos"]:
                self.artifact(reference)
        for capability in caps["capabilities"].values():
            for reference in capability["evidence"]:
                proof = self.artifact(reference, document=True)
                for artifact in proof["artifacts"]:
                    self.artifact(artifact)
        for case in packet["cases"]:
            self.artifact(case["source"])
            self.artifact(case["oracle"], document=True)

    def recheck(self):
        for row in self.rows:
            require(row["capture_status"] == "COMPLETE", "incomplete input capture")
            contracts.verify_artifact(row["original"])
            contracts.verify_artifact(row["retained"])


def preflight(inputs_path, *, case_id, attempt_dir, profile, mode):
    """Return a retained FAIL/BLOCKED report. No backend can be enabled here.

    An invalid/existing attempt pathname raises before writing anything there.
    Subsequent validation failures retain available inputs and a failure report.
    Metadata PASS is never an execution permit or application acceptance.
    """
    attempt = fresh_attempt(attempt_dir)
    capture = InputCapture(attempt)
    report = dict(schema_version=1, kind="application-run-preflight", status="FAIL",
                  execution_status="NOT_RUN", application_acceptance=False,
                  transport_acceptance=False, production_gate_credit=False,
                  backend_implemented=False, case_id=case_id, profile=profile, mode=mode,
                  reasons=[], metadata=None, schema_reference_capture_complete=False,
                  capture_limits=dict(references=MAX_REFERENCES, aggregate_bytes=MAX_RETAINED_BYTES))
    try:
        publish(attempt / "request.json", dict(inputs=os.fspath(inputs_path), case=case_id,
                                               attempt=str(attempt), profile=profile, mode=mode))
        require(profile == "baseline-root-1cpu", "unsupported profile")
        require(mode == "differential-guest", "unsupported mode")
        require(type(case_id) is str and 0 < len(case_id) <= 128, "invalid case selector")
        for path in (Path(__file__).resolve(), _HERE / "runtime_contracts.py", _HERE / "cases.json"):
            capture.take(str(path))
        first = capture.take(os.fspath(inputs_path), maximum=contracts.JSON_LIMIT_BYTES)
        bundle = contracts.load_json(first["retained"]["path"])
        require(type(bundle) is dict, "runtime bundle must be an object")
        capture.graph(bundle)
        # Evaluate the retained root, not a temporarily replaced original.
        # Nested references keep their original paths and frozen byte hashes.
        loaded = contracts.load_runtime_bundle(first["retained"]["path"])
        report["metadata"] = contracts.validate_case(loaded, case_id)
        capture.recheck()
        report["schema_reference_capture_complete"] = True
        report["status"] = "FAIL" if report["metadata"]["status"] == "FAIL" else "BLOCKED"
        report["reasons"] = list(report["metadata"]["reasons"]) + [_BACKEND_REASON]
    except (contracts.ContractError, OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, RecursionError) as error:
        report["reasons"] = [type(error).__name__ + ": " + str(error)]
    finally:
        report["retention_index"] = publish(attempt / "retention-index.json", dict(
            schema_version=1, scope="schema-declared runtime references and preflight source; opaque proof is not recursively interpreted",
            schema_reference_capture_complete=report["schema_reference_capture_complete"],
            reference_uses=capture.reference_uses, entries=capture.rows))
        publish(attempt / "report.json", report)
        for directory in (capture.directory, attempt, attempt.parent):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--profile", required=True, choices=["baseline-root-1cpu"])
    parser.add_argument("--mode", required=True, choices=["differential-guest"])
    args = parser.parse_args(argv)
    try:
        report = preflight(args.inputs, case_id=args.case, attempt_dir=args.attempt,
                           profile=args.profile, mode=args.mode)
    except (contracts.ContractError, OSError, ValueError, RuntimeError) as error:
        print("preflight could not retain an attempt: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 1 if report["status"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
