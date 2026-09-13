#!/usr/bin/env python3
"""Stage the private published-hold-v1 overlay onto an isolated composed source.

The input must already contain the frozen owner, phase-v1, send/notify and RET
overlays for mode 2 or 3. Only a fresh output/source tree is written. No compiler,
guest, test, production input mutation, runtime authority, or acceptance occurs.
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
FROZEN = {
    "stability-owner-phase/stability_phase.rs": "5ce35193f9d88d7b990b92cc90287437ffe9c2e6b3f409ddfa2190b1ebfb9e54",
    "stability-owner-phase/smp_application.append.rs": "5120d4ad683702ffc80453643b6106635c5f6148861da7d247686a37039c5834",
    "stability-owner-phase/smp_application_syscall.append.rs": "fc4fd377d10e5a9f6e63627fb0a062de9d0650367d7079e289e255c74cfb67ec",
    "stability-owner-phase/smp_service.append.rs": "27ccee5815ccdd09c128803483fa488061d50721ff35f51e67363164379e5579",
    "stability-owner-phase/smp_memory.append.rs": "3097600b3bf042cfd952162b2a0584faa1bc69c21c1f779f5010c5148a67989c",
    "stability-transport-fault/send.append.rs": "01f781f9258e3a6564c8512c40721dc2a11e0621a5262756c6f8e85675f0543d",
}
NEW_NAMES = ("stability_phase.rs", "smp_application.append.rs", "smp_application_syscall.append.rs",
             "smp_service.append.rs", "smp_memory.append.rs", "send-gate.rs")
OLD_GATE = b"""    if let Err(error) = crate::stability_phase::before_selected_send() {
        STABILITY_FAULT_BARRIERS.fetch_add(1, Ordering::AcqRel);
        return Err(error);
    }
"""


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


def replace_once(data, old, new, label, edits):
    if not old or data.count(old) != 1:
        raise ValueError("expected one exact original hook: " + label)
    edits.append((old, new, label))
    return data.replace(old, new, 1)


def prepare(source, output, mode):
    if mode not in MODES:
        raise ValueError("only published modes 2 and 3 are supported")
    source = Path(source).absolute()
    output = Path(output).absolute()
    # Reject aliasing, existing output, nested input/output, and symlink roots.
    if source != source.resolve() or output != output.resolve():
        raise ValueError("source and output must use canonical nonsymlink paths")
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("source and output must be disjoint trees")
    package = Path(__file__).resolve().parent / "fixtures"
    output.mkdir(parents=True, exist_ok=False)
    record = {"schema_version": 1, "record_kind": "stability_published_hold_stage",
              "status": "PREPARING", "mode": mode, "mode_number": MODES[mode],
              "source": str(source), "output": str(output / "source"),
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "compiled": False, "executed": False, "execution_authorized": False,
              "application_acceptance": False, "production_gate_credit": False,
              "physical_full_ring_verified": False, "compiled_stack_bound_verified": False,
              "command": "0xc100f502", "version": 2, "request_bytes": 256,
              "files": [], "inputs": [], "source_inputs": []}
    try:
        for directory in ("source", "originals", "inputs", "diffs"):
            (output / directory).mkdir()
        helper = read_regular(Path(__file__))
        (output / "helper.py").write_bytes(helper)
        record["helper"] = identity(helper)
        frozen = {}
        for relative, expected in FROZEN.items():
            data = read_regular(package / relative)
            if identity(data)["sha256"] != expected:
                raise ValueError("frozen original fixture changed: " + relative)
            frozen[relative] = data
        templates = {name: read_regular(package / "stability-published-hold-v1" / name) for name in NEW_NAMES}
        for label, data in list(frozen.items()) + [("stability-published-hold-v1/" + name, data) for name, data in templates.items()]:
            retained = output / "inputs" / label
            retained.parent.mkdir(parents=True, exist_ok=True)
            retained.write_bytes(data)
            record["inputs"].append({"path": label, **identity(data)})
        names = source_names(source)
        originals = {}
        total = 0
        for name in names:
            data = read_regular(source / name)
            # Retain a successfully bounded read before any semantic or total
            # budget check can fail. The one triggering member may add <=8 MiB
            # of failure evidence beyond the 64-MiB logical source budget.
            (output / "originals" / name).write_bytes(data)
            record["source_inputs"].append({"name": name, **identity(data)})
            total += len(data)
            if total > MAX_TOTAL_BYTES:
                raise ValueError("combined source byte budget exceeded")
            if b"\r" in data:
                raise ValueError("source requires exact LF bytes: " + name)
            data.decode("utf-8")
            originals[name] = data
        required = {"stability_observer.rs", "stability_phase.rs", "ihk_smp_x86_64.rs", "mcctrl_process.rs",
                    "smp_memory.rs", "smp_service.rs", "smp_application.rs", "smp_application_syscall.rs"}
        if not required.issubset(originals):
            raise ValueError("missing composed native owner/phase/transport/RET source")
        if originals["stability_phase.rs"] != frozen["stability-owner-phase/stability_phase.rs"]:
            raise ValueError("requires exact original phase module")
        send = frozen["stability-transport-fault/send.append.rs"].replace(b"@MODE@", str(MODES[mode]).encode("ascii"))
        if originals["smp_application_syscall.rs"].count(send) != 1:
            raise ValueError("requires complete unchanged exact-mode send appendix")
        if originals["smp_service.rs"].count(b"        self.verification_accepted_phase();\n") != 1:
            raise ValueError("requires one original end-pump observer hook")
        if b"STABILITY_RET_SELECTED" not in originals["mcctrl_process.rs"]:
            raise ValueError("requires separate original RET observation")
        for name, original in originals.items():
            changed, edits = original, []
            if name == "stability_phase.rs":
                new = templates[name]
                if new.count(b"@MODE@") != 1:
                    raise ValueError("unexpected new phase mode marker count")
                changed = replace_once(changed, original, new.replace(b"@MODE@", str(MODES[mode]).encode("ascii")), "private phase module", edits)
            appendix = name[:-3] + ".append.rs"
            if appendix in templates:
                changed = replace_once(changed, frozen["stability-owner-phase/" + appendix], templates[appendix], "original phase appendix " + name, edits)
            if name == "smp_application_syscall.rs":
                changed = replace_once(changed, OLD_GATE, templates["send-gate.rs"], "separate emitted/host hold counter", edits)
            restored = changed
            for old, new, label in reversed(edits):
                if restored.count(new) != 1:
                    raise ValueError("inverse hook ambiguity: " + label)
                restored = restored.replace(new, old, 1)
            if restored != original:
                raise ValueError("inverse byte restoration failed: " + name)
            (output / "source" / name).write_bytes(changed)
            delta = "".join(difflib.unified_diff(original.decode().splitlines(True), changed.decode().splitlines(True),
                                                fromfile="original/" + name, tofile="published-hold/" + name)).encode()
            (output / "diffs" / (name + ".diff")).write_bytes(delta)
            record["files"].append({"name": name, "original": identity(original), "staged": identity(changed),
                                    "diff": identity(delta), "edits": [label for _, _, label in edits],
                                    "inverse_restoration_byte_equal": True})
        if source_names(source) != names:
            raise ValueError("source directory members changed during staging")
        for name, data in originals.items():
            if read_regular(source / name) != data:
                raise ValueError("source changed during staging: " + name)
        for relative, data in frozen.items():
            if read_regular(package / relative) != data:
                raise ValueError("original fixture changed during staging: " + relative)
        for name, data in templates.items():
            if read_regular(package / "stability-published-hold-v1" / name) != data:
                raise ValueError("new fixture changed during staging: " + name)
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
