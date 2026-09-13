#!/usr/bin/env python3
"""Prepare a fresh phase-control overlay on an already prepared owner observer.

No build, execution, production edits, acceptance or fault-mode changes occur.
Root composes its separately reviewed accepted/send/notify/RET hooks afterward.
Verification-only noninlined role/service boundaries keep sequential service
temporaries out of the observer's caller frames; compiled stack use must still
be measured for each resulting module before runtime authorization.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil


def identity(path):
    data = path.read_bytes()
    return byte_identity(data)


def byte_identity(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def replace_once(value, old, new, edits, label):
    if value.count(old) != 1:
        raise ValueError(f"expected unique original hook: {label}")
    edits.append({"label": label, "original": old, "replacement": new})
    return value.replace(old, new)


def prepare(source, output):
    source, output = source.resolve(), output.resolve()
    package = Path(__file__).resolve().parent / "fixtures/stability-owner-phase"
    output.mkdir(parents=True, exist_ok=False)
    record = {"status": "PREPARING", "started_utc": datetime.now(timezone.utc).isoformat(),
              "source": str(source), "verification_only": True, "compiled": False,
              "executed": False, "gate_credit": False, "files": [],
              "command": "0xc100f501", "version": 1, "request_bytes": 256,
              "stack_boundaries": [], "compiled_stack_bound_verified": False}
    try:
        shutil.copyfile(__file__, output / "helper.py")
        record["helper"] = identity(output / "helper.py")
        observer = source / "stability_observer.rs"
        observer_bytes = observer.read_bytes()
        if b"STABILITY_OWNER_BEGIN" not in observer_bytes:
            raise ValueError("requires the already reviewed typed owner observer")
        record["unchanged_observer_module"] = byte_identity(observer_bytes)
        originals = output / "originals"
        originals.mkdir()
        inputs = output / "phase-inputs"
        inputs.mkdir()
        for path in sorted(package.glob("*.rs")):
            shutil.copyfile(path, inputs / path.name)
        shutil.copyfile(package / "stability_phase.rs", output / "stability_phase.rs")
        record["new_module"] = identity(output / "stability_phase.rs")
        names = [p.name.removesuffix(".append.rs") + ".rs" for p in sorted(package.glob("*.append.rs"))]
        names.append("ihk_smp_x86_64.rs")
        for name in names:
            path = source / name
            original_bytes = path.read_bytes()
            original = original_bytes.decode("utf-8")
            if "mod stability_phase;" in original or "verification_phase_ioctl" in original or "fn verification_accepted_phase" in original:
                raise ValueError(f"source already has phase wiring: {name}")
            (originals / name).write_bytes(original_bytes)
            before = byte_identity(original_bytes)
            changed = original
            edits = []
            appendix_path = inputs / (name.removesuffix(".rs") + ".append.rs")
            appendix = appendix_path.read_text() if appendix_path.exists() else ""
            if name == "ihk_smp_x86_64.rs":
                if 'mod stability_observer;' not in original:
                    raise ValueError("root module is missing the reviewed observer declaration")
                appendix = '\n// VERIFICATION OVERLAY ONLY. No exported or production ABI.\n#[allow(dead_code)]\n#[path = "stability_phase.rs"]\nmod stability_phase;\n'
                old = '    fn ioctl(_device: &ProviderOpenLease, cmd: u32, arg: usize) -> Result<isize> {\n'
                new = old + '        if cmd == stability_phase::COMMAND {\n            return smp_memory::verification_phase_ioctl(arg, false);\n        }\n'
                changed = replace_once(changed, old, new, edits, "native SMP phase ioctl")
                old = '    fn compat_ioctl(_device: &ProviderOpenLease, cmd: u32, arg: usize) -> Result<isize> {\n'
                new = old + '        if cmd == stability_phase::COMMAND {\n            return smp_memory::verification_phase_ioctl(arg as u32 as usize, true);\n        }\n'
                changed = replace_once(changed, old, new, edits, "explicit compat rejection")
            elif name == "smp_service.rs":
                if 'fn verification_observe(' not in original:
                    raise ValueError("Runtime is missing the reviewed full observer")
                # The first compiled overlay inlined all three run() roles
                # and the pump's services into one 3000-byte caller frame at
                # the accepted observer call. Isolate roles first, then each
                # fallible pump step; do not change their order or bodies.
                for method, returns in (
                    ("metadata", " -> Result<bool>"),
                    ("zeroing", " -> Result<bool>"),
                    ("pump", ""),
                    ("pump_master", " -> Result"),
                    ("pump_regular", " -> Result"),
                    ("publish_remote", " -> Result"),
                    ("publish_applications", " -> Result"),
                    ("publish_syscalls", " -> Result"),
                    ("publish_procfs", " -> Result"),
                ):
                    old = f"    fn {method}(&self){returns} {{\n"
                    new = "    #[inline(never)]\n" + old
                    changed = replace_once(changed, old, new, edits,
                                           f"verification stack boundary Runtime::{method}")
                    record["stack_boundaries"].append(f"Runtime::{method}")
                old = '        if let Err(error) = self.publish_procfs() {\n            self.fail(error);\n        }\n    }\n'
                new = '        if let Err(error) = self.publish_procfs() {\n            self.fail(error);\n        }\n        self.verification_accepted_phase();\n    }\n'
                changed = replace_once(changed, old, new, edits, "unlocked end-pump accepted snapshot")
            elif name == "smp_application.rs":
                old = "    pub(crate) fn advance(&self) -> Result {\n"
                new = "    #[inline(never)]\n" + old
                changed = replace_once(changed, old, new, edits,
                                       "verification stack boundary Remote::advance")
                record["stack_boundaries"].append("Remote::advance")
            changed += appendix
            restored = changed.removesuffix(appendix)
            for edit in reversed(edits):
                if restored.count(edit["replacement"]) != 1:
                    raise ValueError(f"inverse hook ambiguity: {edit['label']}")
                restored = restored.replace(edit["replacement"], edit["original"])
            if restored != original:
                raise ValueError(f"inverse restoration failed: {name}")
            (output / name).write_text(changed)
            delta = "".join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                fromfile="a/" + name, tofile="b/" + name))
            (output / (name + ".diff")).write_text(delta)
            if identity(path) != before:
                raise ValueError(f"input changed while preparing: {name}")
            record["files"].append({"name": name, "original": before, "overlay": identity(output / name),
                "diff": identity(output / (name + ".diff")), "edits": edits,
                "appendix": identity(appendix_path) if appendix_path.exists() else None,
                "inverse_restoration_byte_equal": True})
        if observer.read_bytes() != observer_bytes:
            raise ValueError("reviewed observer module changed during preparation")
        record["root_required_hooks"] = [
            "successful exact selected Completion::prepare -> stability_phase::accepted_selected()",
            "exact selected send, before counting actual fault attempt -> stability_phase::before_selected_send()?",
            "root-owned real send/notify/RET instrumentation and physical-ring controller",
            "versioned user client invokes SELECT_BLOCKED before input and explicit later phases",
        ]
        record["status"] = "PREPARED_NOT_COMPILED_NOT_EXECUTED"
    except BaseException as error:
        record.update(status="FAIL", error=str(error))
        raise
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.output)
