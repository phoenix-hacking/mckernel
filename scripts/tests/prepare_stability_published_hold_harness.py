#!/usr/bin/env python3
"""Prepare the exact native-interface harness source; never compile or execute.

Root separately reviews and compiles the retained harness.rs for each mode.
Every state case runs in a fresh process, with no reset hook in native source.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

SUBJECTS = {
    "stability_phase.rs": "7219f34ca70b4a4051947fa5221802ce5395aa1f2e475c0aab263676c4b416e2",
    "smp_application.append.rs": "3b6b1348687cd6ed8a092e184cfcf687d95b7b36ca14756d7a0ae10f1cb8b7b3",
    "smp_application_syscall.append.rs": "f9af4c106b69def12cd353c684c83c0dbfbdef7915cc27ff6fabc30e21d53fc5",
    "smp_memory.append.rs": "2d4be27a2e26df46f9e278d4071d901595bf8358ea6444c41a2da6eff27f5000",
    "smp_service.append.rs": "0a9f8988e2b97dd224b421cf7baaff8b001ddb01441ab2dedffe0b3a753875cc",
    "send-gate.rs": "dac2855ca19e587c33f7bd5a36c30c9090a6ea846f6dca90081abf0543228267",
}
OBSERVER = "fb0a795209d73262b0415e91b55a9c4e7f9ac357cf255460c16dc84233ad6a31"


def identity(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def bounded_read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("requires bounded regular source input: " + str(path))
    with path.open("rb") as stream:
        data = stream.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("source grew beyond bound")
    return data


def prepare(output, mode):
    if type(mode) is not int or mode not in (2, 3):
        raise ValueError("mode must be the plain integer2 or3")
    package = Path(__file__).resolve().parent / "fixtures/stability-published-hold-v1"
    observer_path = package.parent / "stability-owner-observer/stability_observer.rs"
    output = Path(output).absolute()
    if output != output.resolve() or package == output or package in output.parents or output in package.parents:
        raise ValueError("requires a fresh canonical output disjoint from source package")
    output.mkdir(parents=True, exist_ok=False)
    record = {"schema_version": 1, "record_kind": "published_hold_native_harness_preparation",
              "status": "PREPARING", "mode": mode,
              "started_utc": datetime.now(timezone.utc).isoformat(), "inputs": [], "outputs": [],
              "subject_methods_modified": False, "compiled": False, "executed": False,
              "application_acceptance": False, "kernel_ownership_acceptance": False,
              "physical_response_or_ring_acceptance": False, "native_stack_acceptance": False}
    originals = {}
    try:
        (output / "inputs").mkdir()
        for name in list(SUBJECTS) + ["native-harness.rs", "native-expectations.json", "harness.md"]:
            source = package / name
            data = bounded_read(source)
            originals[source] = data
            (output / "inputs" / name).write_bytes(data)
            record["inputs"].append({"path": str(source), **identity(data)})
            if name in SUBJECTS and identity(data)["sha256"] != SUBJECTS[name]:
                raise ValueError("reviewed native method source changed: " + name)
            if name == "stability_phase.rs":
                if data.count(b"@MODE@") != 1:
                    raise ValueError("requires one literal phase mode marker")
                staged = data.replace(b"@MODE@", str(mode).encode("ascii"))
                record["mode_substitution"] = {"source": identity(data), "staged": identity(staged),
                                                "only_edit": "@MODE@ -> " + str(mode)}
                (output / name).write_bytes(staged)
            elif name in SUBJECTS:
                (output / name).write_bytes(data)
            elif name == "native-harness.rs":
                (output / "harness.rs").write_bytes(data)
        observer = bounded_read(observer_path)
        originals[observer_path] = observer
        (output / "inputs/stability_observer.rs").write_bytes(observer)
        record["inputs"].append({"path": str(observer_path), **identity(observer)})
        if identity(observer)["sha256"] != OBSERVER:
            raise ValueError("reviewed original observer types changed")
        fragments = []
        for start, end in [
            (b"#[derive(Clone, Copy, Debug, PartialEq, Eq)]\npub(crate) struct Tag {", b"#[derive(Clone, Copy, Debug)]\npub(crate) struct Call {"),
            (b"#[derive(Clone, Copy, Debug, PartialEq, Eq)]\npub(crate) struct Selection {", b"// One selection per fresh verification module/guest."),
        ]:
            if observer.count(start) != 1 or observer.count(end) != 1:
                raise ValueError("observer type boundary is not unique")
            first, last = observer.index(start), observer.index(end)
            if first >= last:
                raise ValueError("observer type boundaries reversed")
            data = observer[first:last]
            fragments.append(data)
            record.setdefault("observer_type_fragments", []).append({"start_offset": first, "end_offset": last, **identity(data)})
        (output / "observer-types.rs").write_bytes(b"\n".join(fragments))
        helper = bounded_read(Path(__file__))
        originals[Path(__file__)] = helper
        (output / "helper.py").write_bytes(helper)
        record["helper"] = identity(helper)
        expectations = json.loads((output / "inputs/native-expectations.json").read_text())
        record["cases"] = expectations["cases"]
        record["root_required_execution"] = {"compiler": "pinned rustc --edition=2021 harness.rs -o harness",
            "case_argv": ["./harness", "CASE_NAME"], "fresh_process_per_case": True,
            "raw_exit_expected": 0, "per_case_timeout_seconds": 8,
            "per_stream_byte_budget": 262144, "root_owned_supervision_and_retention_required": True}
        for path, expected in originals.items():
            if bounded_read(path) != expected:
                raise ValueError("source changed during harness preparation: " + str(path))
        for path in sorted(output.glob("*.rs")):
            record["outputs"].append({"path": path.name, **identity(path.read_bytes())})
        record["status"] = "PREPARED_HARNESS_SOURCE_NOT_COMPILED_NOT_EXECUTED"
    except BaseException as error:
        record.update(status="FAIL", error=type(error).__name__ + ": " + str(error))
        raise
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", type=int, choices=(2, 3), required=True)
    args = parser.parse_args()
    prepare(args.output, args.mode)
