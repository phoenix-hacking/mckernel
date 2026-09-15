#!/usr/bin/env python3
"""Stage selected-retention-v1 on exact held-v1 composed Rust input, source only.

Preserves every original byte and applies three inverse-checked source deltas.
No compiler, tests, guest, source-input mutation, or execution authority.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat

MAX_FILES = 128
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MODES = {"postpublish-notify": 2, "recoverable-backpressure": 3}
SOURCE_MANIFEST_NAME = "source-manifests.json"
SOURCE_MANIFEST_IDENTITY = {
    "size": 19839,
    "sha256": "d9d439bff0a90bddcc3920f36b8fac81d6e1515fd83f035e18a34464cc8498d0",
}
FROZEN_SOURCE = {
    2: {
        "application_syscall.rs": "83c76e277f759e920a91f4fd3bb601268aee39082acbe3f4cd732ec3c58feb92",
        "smp_application_syscall.rs": "4f7611fca376aacddf80be2dacef0928f5e6c8506c692f0154680f93dfeaa5d4",
        "stability_phase.rs": "041b7e983132745e64aed003e745600f7e8573ed19a8ead57a4f4fecda888131",
    },
    3: {
        "application_syscall.rs": "83c76e277f759e920a91f4fd3bb601268aee39082acbe3f4cd732ec3c58feb92",
        "smp_application_syscall.rs": "b18b2356189a42b9083e09b477bba4b81011a9c3c42aafb9564daebb0f813ee2",
        "stability_phase.rs": "d81bb72e67ae0db6a69c6dfed6c9db96c33ec33ffc9aeef015970b431884d4ea",
    },
}
NAMES = ("response-prepare.rs", "return-prepare.rs", "cancel-guard.rs",
         "mailbox-retention.append.rs", "phase-retention.append.rs")
OLD_GATE_SHA = "dac2855ca19e587c33f7bd5a36c30c9090a6ea846f6dca90081abf0543228267"


def identity(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read_regular(path):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise ValueError("expected bounded regular file: " + str(path))
    descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino) or not stat.S_ISREG(opened.st_mode):
            raise ValueError("input identity changed before read: " + str(path))
        chunks, count = [], 0
        while count <= MAX_FILE_BYTES:
            chunk = os.read(descriptor, min(65536, MAX_FILE_BYTES + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = path.lstat()
    data = b"".join(chunks)
    fields = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if count > MAX_FILE_BYTES or fields(before) != fields(after) or fields(after) != fields(current):
        raise ValueError("input changed or exceeded bound while reading: " + str(path))
    return data


def source_names(source):
    names = []
    # Path.iterdir may call listdir internally and materialize an unbounded
    # directory before yielding. Consume scandir directly with an early cap.
    with os.scandir(source) as entries:
        for entry in entries:
            if len(names) >= MAX_FILES or not entry.name.endswith(".rs"):
                raise ValueError("source must be a flat bounded Rust-only composed tree")
            names.append(entry.name)
    if not names:
        raise ValueError("source must be a flat bounded Rust-only composed tree")
    return sorted(names)


def authoritative_source_manifest(mode, package=None):
    """Return a pinned 51-file manifest and verify every retained authority."""
    package = package or Path(__file__).resolve().parent / "fixtures" / "stability-selected-retention-v1"
    manifest_path = package / SOURCE_MANIFEST_NAME
    raw = read_regular(manifest_path)
    if identity(raw) != SOURCE_MANIFEST_IDENTITY:
        raise ValueError("authoritative source manifest identity drifted")
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("authoritative source manifest is not JSON: " + str(error)) from error
    if (document.get("schema_version") != 1 or document.get("member_count_per_mode") != 51 or
            document.get("execution_authorized") is not False or document.get("runtime_acceptance") is not False):
        raise ValueError("authoritative source manifest header mismatch")
    row = document.get("modes", {}).get(str(mode))
    expected_mode = "postpublish-notify" if mode == 2 else "recoverable-backpressure"
    if not isinstance(row, dict) or row.get("mode") != expected_mode:
        raise ValueError("authoritative source manifest mode mismatch")
    authorities = row.get("authority_records")
    if not isinstance(authorities, list) or not authorities:
        raise ValueError("authoritative source records missing")
    verified = []
    for authority in authorities:
        path = Path(authority.get("path", ""))
        data = read_regular(path)
        actual = identity(data)
        if actual != {"size": authority.get("size"), "sha256": authority.get("sha256")}:
            raise ValueError("authoritative source record identity drifted: " + str(path))
        record = json.loads(data)
        if record.get("mode") != authority.get("expected_mode") or record.get("status") != authority.get("expected_status"):
            raise ValueError("authoritative source record state mismatch: " + str(path))
        verified.append({"path": str(path), **actual})
    members = row.get("members")
    if not isinstance(members, list) or len(members) != 51:
        raise ValueError("authoritative source composition must contain exactly 51 flat Rust members")
    expected = {}
    for entry in members:
        if (not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or
                "/" in entry["name"] or not entry["name"].endswith(".rs") or entry["name"] in expected or
                type(entry.get("size")) is not int or type(entry.get("sha256")) is not str or
                len(entry["sha256"]) != 64):
            raise ValueError("invalid or duplicate authoritative source member")
        expected[entry["name"]] = {"size": entry["size"], "sha256": entry["sha256"]}
    tree = Path(row.get("tree", ""))
    names = source_names(tree)
    if names != sorted(expected):
        raise ValueError("authoritative source tree membership drifted")
    for name in names:
        if identity(read_regular(tree / name)) != expected[name]:
            raise ValueError("authoritative source tree hash drifted: " + name)
    frozen = FROZEN_SOURCE[mode]
    if any(expected.get(name, {}).get("sha256") != digest for name, digest in frozen.items()):
        raise ValueError("frozen held-v1 source is not the authoritative composition")
    return ({name: entry["sha256"] for name, entry in expected.items()}, {
        "manifest": {"path": str(manifest_path), **identity(raw)},
        "authority_records": verified,
        "tree": str(tree),
    })


def validate_source_contract(source, mode, manifest=None):
    """Reject membership or byte drift before any staging output is created."""
    expected = authoritative_source_manifest(mode)[0] if manifest is None else dict(manifest)
    names = source_names(source)
    if names != sorted(expected):
        missing = sorted(set(expected) - set(names))
        extra = sorted(set(names) - set(expected))
        raise ValueError("source ownership membership mismatch (missing=%s extra=%s)" % (missing, extra))
    originals = {}
    for name in names:
        data = read_regular(Path(source) / name)
        originals[name] = data
        if identity(data)["sha256"] != expected[name]:
            raise ValueError("authoritative source hash mismatch: " + name)
    return originals


def replace_once(data, old, new, label, edits):
    if not old or data.count(old) != 1:
        raise ValueError("expected one exact original hook: " + label)
    edits.append((old, new, label))
    return data.replace(old, new, 1)


def prepare(source, output, mode):
    if mode not in MODES:
        raise ValueError("only published modes 2 and 3 are supported")
    source, output = Path(source).absolute(), Path(output).absolute()
    if source != source.resolve() or output != output.resolve():
        raise ValueError("source and output require canonical nonsymlink paths")
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("source and output must be disjoint")
    package = Path(__file__).resolve().parent / "fixtures"
    output.mkdir(parents=True, exist_ok=False)
    record = {"schema_version": 1, "record_kind": "stability_selected_retention_stage",
              "status": "PREPARING", "mode": mode, "mode_number": MODES[mode],
              "response_retention_profile": "published-retention-v1",
              "original_held_source_bindings": FROZEN_SOURCE[MODES[mode]],
              "source": str(source), "output": str(output / "source"),
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "compiled": False, "executed": False, "execution_authorized": False,
              "application_acceptance": False, "production_gate_credit": False,
              "physical_full_ring_verified": False, "compiled_stack_bound_verified": False,
              "command": "0xc100f502", "version": 2, "request_bytes": 256,
              "files": [], "inputs": [], "source_inputs": []}
    try:
        for name in ("source", "originals", "inputs", "diffs"):
            (output / name).mkdir()
        helper = read_regular(Path(__file__))
        (output / "helper.py").write_bytes(helper)
        record["helper"] = identity(helper)
        inputs = {}
        for name in NAMES:
            path = package / "stability-selected-retention-v1" / name
            data = read_regular(path)
            inputs[path] = data
            (output / "inputs" / name).write_bytes(data)
            record["inputs"].append({"path": str(path), **identity(data)})
        gate_path = package / "stability-published-hold-v1/send-gate.rs"
        gate = read_regular(gate_path)
        inputs[gate_path] = gate
        (output / "inputs/original-send-gate.rs").write_bytes(gate)
        record["inputs"].append({"path": str(gate_path), **identity(gate)})
        if identity(gate)["sha256"] != OLD_GATE_SHA:
            raise ValueError("original held-v1 gate changed")
        formatted_gate = gate.replace(b"SendGate::Released => {},", b"SendGate::Released => {}")
        if formatted_gate == gate:
            raise ValueError("original held-v1 gate formatting anchor changed")
        templates = {path.name: data for path, data in inputs.items() if path != gate_path}
        if templates["mailbox-retention.append.rs"].count(gate) != 1:
            raise ValueError("moved gate must retain exactly the original counter block")
        mode_number = MODES[mode]
        manifest, authority = authoritative_source_manifest(mode_number)
        record["authoritative_source"] = dict(authority,
            members=[{"name": name, "sha256": digest} for name, digest in sorted(manifest.items())])
        names, originals, total = source_names(source), validate_source_contract(source, mode_number, manifest), 0
        for name in names:
            data = originals[name]
            (output / "originals" / name).write_bytes(data)
            record["source_inputs"].append({"name": name, **identity(data)})
            total += len(data)
            if total > MAX_TOTAL_BYTES:
                raise ValueError("combined source byte budget exceeded")
            if b"\r" in data:
                raise ValueError("source requires exact LF bytes: " + name)
            data.decode("utf-8")
            originals[name] = data
        required = {"stability_observer.rs", "smp_application.rs", "smp_service.rs", "smp_memory.rs",
                    "sysfs_memory.rs", "ihk_smp_x86_64.rs", "mcctrl_process.rs"} | set(FROZEN_SOURCE[MODES[mode]])
        if not required.issubset(originals):
            raise ValueError("missing complete original held-v1 composed source")
        # Every member, including the former three "frozen" inputs, was
        # authenticated above against the retained mode-specific manifest.
        # One actual native Completion::publish caller. Do not infer this from
        # any similarly named service/RPC publication method.
        original_mailbox = originals["smp_application_syscall.rs"]
        publish = b"        call.completion.as_mut().unwrap().publish(|packet| {\n"
        if original_mailbox.count(publish) != 1:
            raise ValueError("selected Completion publisher hook is not unique")
        for name, original in originals.items():
            changed, edits = original, []
            if name == "application_syscall.rs":
                start = b"    pub(crate) fn prepare(mut self, servicing_tid: i32, value: i64) -> Result<Completion<M>, i32> {\n"
                end = b"\n}\n\npub(crate) struct Completion<M: ResponseMemory> {"
                if original.count(start) != 1 or original.count(end) != 1:
                    raise ValueError("original prepare method boundaries drifted")
                first, last = original.index(start), original.index(end)
                if first >= last:
                    raise ValueError("reversed prepare method boundaries")
                # Template ends in LF; end starts at the enclosing impl's LF.
                changed = replace_once(changed, original[first:last], templates["response-prepare.rs"].rstrip(b"\n"), "preserving actual prepare result", edits)
            elif name == "smp_application_syscall.rs":
                old = b"""        let response = call.response.take().ok_or(-71)?;
        match response.prepare(worker.worker.tid(), value) {
            Ok(completion) => call.completion = Some(completion),
            Err(error) => {
                self.quarantined = true;
                return Err(error);
            }
        }
"""
                changed = replace_once(changed, old, templates["return-prepare.rs"], "selected prepare error restores Response", edits)
                cancel = b"    fn cancel_call(call: &mut Call<M>) -> Result {\n"
                changed = replace_once(changed, cancel, cancel + templates["cancel-guard.rs"], "selected cancellation retains original capability", edits)
                prepublish = b"        let stability_request = call.delivery.request().clone();\n"
                hook = b"        stability_retention_pre_publish(call.completion.as_ref().and_then(Completion::verification_owner))?;\n"
                changed = replace_once(changed, prepublish, hook + prepublish, "universal prepublish gate before eligibility and wake", edits)
                changed = replace_once(changed, formatted_gate, b"    // The selected phase gate already ran at the unique Mailbox prepublish entry.\n", "remove optional send gate without duplicate counts", edits)
                old_comment = b"""    // The initial selected key was bound to real OS-generation/ledger/worker
    // owners while this request was Delivered. The selection never resets.
    // A scalar-only barrier can defer publication until the unlocked pump has
    // emitted AcceptedReturn. It never resets the production completion clock.
"""
                changed = replace_once(changed, old_comment, b"    // Fault injection begins only after the universal selected retention gate.\n", "update relocated gate comment", edits)
                # Use an exact final suffix as the reversible append anchor.
                anchor = changed[-128:]
                changed = replace_once(changed, anchor, anchor + templates["mailbox-retention.append.rs"], "selected claim retention helpers", edits)
            elif name == "stability_phase.rs":
                changed = replace_once(changed, b"        RELEASED => SendGate::Released,\n", b"        RELEASED if RELEASE_COMMITS.load(Ordering::Acquire) == 1 => SendGate::Released,\n", "only committed release opens publication", edits)
                anchor = changed[-128:]
                changed = replace_once(changed, anchor, anchor + templates["phase-retention.append.rs"], "read-only committed release predicate", edits)
            restored = changed
            for old, new, label in reversed(edits):
                if restored.count(new) != 1:
                    raise ValueError("inverse hook ambiguity: " + label)
                restored = restored.replace(new, old, 1)
            if restored != original:
                raise ValueError("inverse byte restoration failed: " + name)
            (output / "source" / name).write_bytes(changed)
            delta = "".join(difflib.unified_diff(original.decode().splitlines(True), changed.decode().splitlines(True),
                                                fromfile="held-v1/" + name, tofile="selected-retention-v1/" + name)).encode()
            (output / "diffs" / (name + ".diff")).write_bytes(delta)
            record["files"].append({"name": name, "original": identity(original), "staged": identity(changed),
                                    "diff": identity(delta), "edits": [label for _, _, label in edits],
                                    "inverse_restoration_byte_equal": True})
        if source_names(source) != names:
            raise ValueError("source members changed during staging")
        for name, expected in originals.items():
            if read_regular(source / name) != expected:
                raise ValueError("source changed during staging: " + name)
        for path, expected in inputs.items():
            if read_regular(path) != expected:
                raise ValueError("fixture changed during staging: " + str(path))
        if read_regular(Path(__file__)) != helper:
            raise ValueError("helper changed during staging")
        record["status"] = "PREPARED_NOT_COMPILED_NOT_EXECUTED"
    except BaseException as error:
        record.update(status="FAIL", error=type(error).__name__ + ": " + str(error))
        raise
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    args = parser.parse_args()
    prepare(args.source, args.output, args.mode)
