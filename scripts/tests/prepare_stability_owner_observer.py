#!/usr/bin/env python3
"""Create a verification-only typed owner-observer overlay; never build or run.

--source is an explicitly selected, flat native-rust source directory. The
output records its exact identities. Applying this overlay to a pinned full
build stage, selecting phases and controlling faults belongs to the parent
verification lane. This helper does not edit that source or enable a gate.
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
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def replace_once(data, old, new, label, edits):
    if data.count(old) != 1:
        raise ValueError(f"expected one stable insertion anchor: {label}")
    edits.append({"label": label, "original": old, "replacement": new})
    return data.replace(old, new)


def prepare(args):
    source, output = args.source.resolve(), args.output.resolve()
    package = Path(__file__).resolve().parent / "fixtures/stability-owner-observer"
    output.mkdir(parents=True, exist_ok=False)
    record = {"status": "PREPARING", "started_utc": datetime.now(timezone.utc).isoformat(),
        "verification_only": True, "compiled": False, "executed": False,
        "production_gate_credit": False, "source": str(source), "files": [],
        "limits": {"applications": 8, "calls_per_mailbox": 8, "workers_per_mailbox": 16,
            "tags_per_ledger_class": 16, "pager_handles": 16},
        "snapshot_version": 1, "snapshot_scope": "independently sampled complete bounded domains"}
    try:
        shutil.copyfile(__file__, output / "helper.py")
        record["helper"] = identity(output / "helper.py")
        extension_dir = output / "observer-inputs"
        extension_dir.mkdir()
        extensions = sorted(package.glob("*.append.rs"))
        for extension in extensions:
            shutil.copyfile(extension, extension_dir / extension.name)
        shutil.copyfile(package / "stability_observer.rs", output / "stability_observer.rs")
        record["new_module"] = {"path": "stability_observer.rs", **identity(output / "stability_observer.rs")}
        originals = output / "originals"
        originals.mkdir()
        names = [path.name.removesuffix(".append.rs") + ".rs" for path in extensions]
        names.append("ihk_smp_x86_64.rs")
        for name in names:
            original_path = source / name
            original = original_path.read_text()
            if "STABILITY_OWNER_" in original or "mod stability_observer;" in original:
                raise ValueError(f"source is already overlaid: {name}")
            shutil.copyfile(original_path, originals / name)
            before = identity(originals / name)
            edits = []
            changed = original
            appendix_path = extension_dir / (name.removesuffix(".rs") + ".append.rs")
            appendix = appendix_path.read_text() if appendix_path.exists() else ""
            if name == "ihk_smp_x86_64.rs":
                # Scope the unused-code allowance to the new observer module;
                # the unchanged production modules retain their lint policy.
                appendix = '\n// VERIFICATION OVERLAY ONLY. Removed from production module builds.\n#[allow(dead_code)]\n#[path = "stability_observer.rs"]\nmod stability_observer;\n'
            elif name == "application_syscall.rs":
                old = "pub(crate) unsafe trait ResponseMemory {\n"
                new = old + "    // Verification metadata only; missing adapters are explicit None.\n    fn verification_owner(&self) -> Option<crate::stability_observer::Claim> { None }\n"
                changed = replace_once(changed, old, new, "ResponseMemory metadata capability", edits)
            elif name == "sysfs_memory.rs":
                old = "unsafe impl ResponseMemory for SyscallResponse {\n"
                new = old + "    fn verification_owner(&self) -> Option<crate::stability_observer::Claim> {\n        Some(self.verification_claim())\n    }\n"
                changed = replace_once(changed, old, new, "native exact claim metadata", edits)
                old = "    fn address(&mut self) -> *mut u8 {\n        self.address as *mut u8\n    }"
                new = "    fn address(&mut self) -> *mut u8 {\n        crate::stability_observer::address(self.verification_claim());\n        self.address as *mut u8\n    }"
                changed = replace_once(changed, old, new, "selected response address acquisition counter", edits)
                old = "        // The mailbox's in-kernel reservation or complete transfer critical\n"
                new = "        crate::stability_observer::payload(self.verification_claim(), bytes.len());\n" + old
                changed = replace_once(changed, old, new, "selected payload access counter", edits)
                old = "        // The guest can already reuse the response; only host bookkeeping is\n"
                new = "        crate::stability_observer::release(self.verification_claim());\n" + old
                changed = replace_once(changed, old, new, "selected release bookkeeping counter", edits)
            changed += appendix
            restored = changed.removesuffix(appendix) if appendix else changed
            for edit in reversed(edits):
                if restored.count(edit["replacement"]) != 1:
                    raise ValueError(f"inverse anchor mismatch: {edit['label']}")
                restored = restored.replace(edit["replacement"], edit["original"])
            if restored != original:
                raise ValueError(f"inverse restoration mismatch: {name}")
            (output / name).write_text(changed)
            diff = "".join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                fromfile="a/" + name, tofile="b/" + name))
            (output / (name + ".diff")).write_text(diff)
            if identity(original_path) != before:
                raise ValueError(f"source changed during overlay generation: {name}")
            record["files"].append({"name": name, "original": before,
                "overlay": identity(output / name), "diff": identity(output / (name + ".diff")),
                "appendix": identity(appendix_path) if appendix_path.exists() else None,
                "edits": edits, "inverse_restoration_byte_equal": True})
        record["phase_wiring"] = "NOT_WIRED: Runtime/Started verification_select_read16 and verification_observe require reviewed outside-lock calls"
        record["fault_wiring"] = "NONE: no queue mutation, status injection, notification change or guest response read"
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
    prepare(parser.parse_args())
