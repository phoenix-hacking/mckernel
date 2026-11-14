#!/usr/bin/env python3
"""Add reviewed verification send/notify/RET hooks to a staged observer tree.

Source-only: --source must be a complete isolated stage containing the owner
and phase modules. This helper never compiles, loads, or edits its input tree.
The caller must bind the preceding phase/owner overlays to a production build.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil

MODES = {"prepublish-hard": 1, "postpublish-notify": 2,
         "recoverable-backpressure": 3, "permanent-backpressure": 4}


def identity(path):
    data = path.read_bytes()
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def replace_once(text, old, new, label, edits):
    if text.count(old) != 1:
        raise ValueError("expected one exact hook: " + label)
    edits.append({"label": label, "original": old, "replacement": new})
    return text.replace(old, new)


def prepare(args):
    source, output = args.source.resolve(), args.output.resolve()
    package = Path(__file__).resolve().parent / "fixtures"
    output.mkdir(parents=True, exist_ok=False)
    record = {"schema_version": 1, "status": "PREPARING", "mode": args.mode,
              "started_utc": datetime.now(timezone.utc).isoformat(), "files": [],
              "verification_only": True, "compiled": False, "executed": False,
              "physical_full_ring_verified": False, "production_gate_credit": False}
    try:
        shutil.copyfile(__file__, output / "helper.py")
        record["helper"] = identity(output / "helper.py")
        (output / "inputs").mkdir()
        for path in (package / "stability-transport-fault/send.append.rs",
                     package / "stability-ret-observer.rs"):
            shutil.copyfile(path, output / "inputs" / path.name)
        record["required_modules"] = []
        for name in ("stability_observer.rs", "stability_phase.rs"):
            record["required_modules"].append({"path": str(source / name), **identity(source / name)})
        appendix = (output / "inputs/send.append.rs").read_text()
        if appendix.count("@MODE@") != 2:
            raise ValueError("unexpected mode template markers")
        appendix = appendix.replace("@MODE@", str(MODES[args.mode]))
        for name in ("smp_application_syscall.rs", "smp_service.rs", "mcctrl_process.rs"):
            original_bytes = (source / name).read_bytes()
            original = original_bytes.decode("utf-8")
            if "\r" in original:
                raise ValueError("source requires exact LF bytes: " + name)
            if "STABILITY_FAULT_" in original or "STABILITY_RET_SELECTED" in original:
                raise ValueError("transport source already instrumented: " + name)
            (output / (name + ".original")).write_bytes(original_bytes)
            changed, edits, extension = original, [], ""
            if name == "smp_application_syscall.rs":
                start = changed.index("    pub(crate) fn return_value(\n")
                end = changed.index("    pub(crate) fn returned(", start)
                method = changed[start:end]
                old = "        Ok(())\n    }\n"
                new = ("        stability_fault_accepted(call.delivery.request(), call.delivery.serial().wire(),\n"
                       "            !call.cancelled && !call.kernel && !call.service,\n"
                       "            call.completion.as_ref().and_then(Completion::verification_owner));\n" + old)
                local = []
                replaced = replace_once(method, old, new, "accepted actual normal return", local)
                changed = replace_once(changed, method, replaced, "normal return method only", edits)
                old = "        call.completion.as_mut().unwrap().publish(send)?;"
                new = """        let stability_request = call.delivery.request().clone();
        let stability_serial = call.delivery.serial().wire();
        let stability_eligible = !call.cancelled && !call.kernel && !call.service;
        let stability_owner = call.completion.as_ref().and_then(Completion::verification_owner);
        call.completion.as_mut().unwrap().publish(|packet| {
            stability_fault_send(&stability_request, stability_serial, stability_eligible, stability_owner, packet, send)
        })?;"""
                changed = replace_once(changed, old, new, "actual completion send callback", edits)
                extension = "\n" + appendix
            elif name == "smp_service.rs":
                old = "|| smp_ikc::notify(cpu),"
                new = ("|| super::super::smp_application_syscall::stability_fault_notify(self.owner.slot(), self.owner.generation(), application.wire(), guest_cpu, "
                       "|| smp_ikc::notify(cpu).map_err(|error| error.to_errno())).map_err(errno),")
                changed = replace_once(changed, old, new, "actual separate notification callback", edits)
            else:
                old = "            worker.delivery.store(serial, Ordering::Release);\n"
                new = old + """            if image::word(&bytes, 40).map_err(errno)? == 0
                && image::word(&bytes, 48).map_err(errno)? == 0
                && image::word(&bytes, 64).map_err(errno)? == 16
            {
                stability_ret_select(stability_ret_key(self, &worker, serial));
            }
"""
                changed = replace_once(changed, old, new, "actual copied read16 worker delivery", edits)
                old = "        let result = self.invoke(super::application_abi::RETURN_SYSCALL, &mut bytes);\n"
                new = """        let stability_key = stability_ret_key(self, &worker, serial);
        stability_ret_enter(stability_key, i64::from_le_bytes(bytes[24..32].try_into().unwrap()), cpu);
""" + old + """        stability_ret_leave(stability_key,
            result.as_ref().map_or_else(|error| error.to_errno(), |_| 0),
            u64::from_le_bytes(bytes[48..56].try_into().unwrap()));
"""
                changed = replace_once(changed, old, new, "actual backend RET enter and leave", edits)
                extension = "\n" + (output / "inputs/stability-ret-observer.rs").read_text()
            changed += extension
            restored = changed.removesuffix(extension) if extension else changed
            for edit in reversed(edits):
                if restored.count(edit["replacement"]) != 1:
                    raise ValueError("inverse hook mismatch: " + edit["label"])
                restored = restored.replace(edit["replacement"], edit["original"])
            if restored.encode("utf-8") != original_bytes:
                raise ValueError("inverse byte comparison failed: " + name)
            (output / name).write_text(changed)
            diff = "".join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                               fromfile="a/" + name, tofile="b/" + name))
            (output / (name + ".diff")).write_text(diff)
            if identity(source / name) != identity(output / (name + ".original")):
                raise ValueError("source changed during staging: " + name)
            record["files"].append({"name": name, "original": identity(output / (name + ".original")),
                                    "overlay": identity(output / name), "edits": edits,
                                    "inverse_restoration_byte_equal": True})
        record["inputs"] = [{"name": p.name, **identity(p)} for p in sorted((output / "inputs").iterdir())]
        record["status"] = "PREPARED_NOT_COMPILED_NOT_EXECUTED"
    except BaseException as error:
        record.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    prepare(parser.parse_args())
