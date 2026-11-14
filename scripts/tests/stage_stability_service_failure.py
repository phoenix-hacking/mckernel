#!/usr/bin/env python3
"""Stage source-bound H04 candidate tests without compiling or running them.

The retained transport-failure capture supplies its hash-verified generated
C-peer vectors. Fresh exact candidate methods replace all affected extracts.
Only a new --output directory is written. Production files are never patched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def identity(path):
    data = path.read_bytes()
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify(path, row):
    actual = identity(path)
    if any(actual[key] != row[key] for key in actual):
        raise ValueError(f"identity mismatch: {path}")


def relative_record_path(row, marker):
    parts = row["path"].split(f"/{marker}/", 1)
    if len(parts) != 2:
        raise ValueError(f"unexpected retained input path: {row['path']}")
    relative = Path(parts[1])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe retained relative path")
    return relative


def apply_exact_patch(source, patch):
    """Apply ordinary text hunks at their exact original offsets; never fuzz."""
    lines = patch.read_text().splitlines(keepends=True)
    index = 0
    touched = []
    while index < len(lines):
        if not lines[index].startswith("--- a/"):
            raise ValueError("expected unified diff file header")
        relative = Path(lines[index][6:].strip())
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe candidate path")
        if lines[index + 1] != f"+++ b/{relative}\n":
            raise ValueError("renames are outside this candidate")
        original = (source / relative).read_text().splitlines(keepends=True)
        result, cursor = [], 0
        index += 2
        while index < len(lines) and lines[index].startswith("@@ "):
            match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n", lines[index])
            if not match:
                raise ValueError("unsupported hunk header")
            start = int(match[1]) - 1
            if start < cursor:
                raise ValueError("overlapping hunks")
            result.extend(original[cursor:start])
            cursor = start
            consumed = produced = 0
            index += 1
            while index < len(lines) and lines[index][:1] in (" ", "+", "-") and not lines[index].startswith("--- a/"):
                kind, body = lines[index][0], lines[index][1:]
                if kind in " -":
                    if cursor >= len(original) or original[cursor] != body:
                        raise ValueError(f"candidate context mismatch: {relative}:{cursor + 1}")
                    cursor += 1
                    consumed += 1
                if kind in " +":
                    result.append(body)
                    produced += 1
                index += 1
            if consumed != int(match[2] or 1) or produced != int(match[4] or 1):
                raise ValueError("candidate hunk count mismatch")
        result.extend(original[cursor:])
        (source / relative).write_text("".join(result))
        touched.append(str(relative))
    expected = ["host-kernel/native-rust/smp_application.rs", "host-kernel/native-rust/smp_service.rs"]
    if touched != expected:
        raise ValueError(f"unexpected candidate files: {touched}")


def extract(source, relative, name, record):
    path = source / relative
    data = path.read_text()
    pattern = rf"^    (?:pub\(crate\) )?fn {name}\("
    matches = list(re.finditer(pattern, data, re.M))
    if len(matches) != 1:
        raise ValueError(f"expected one method {relative}:{name}")
    start = matches[0].start()
    end = data.index("{", start) + 1
    depth = 1
    # These reviewed methods have balanced braces in comments/string literals.
    # Preserve their exact bytes; do not rewrite production bodies in fixtures.
    while depth:
        if end >= len(data):
            raise ValueError(f"unbalanced method {name}")
        depth += (data[end] == "{") - (data[end] == "}")
        end += 1
    body = data[start:end]
    record["extracted_methods"].append({"source": str(relative), "name": name,
        "start_byte": len(data[:start].encode()), "end_byte": len(data[:end].encode()),
        "sha256": hashlib.sha256(body.encode()).hexdigest()})
    return body + "\n"


def stage(args):
    repo, capture, output = args.repo.resolve(), args.reference_capture.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = {"status": "STAGING", "compiled": False, "executed": False,
        "actual_guest_transport_fault_verified": False, "production_gate_credit": False,
        "extracted_methods": [], "reference_capture": str(capture)}
    try:
        retained = json.loads((capture / "record.json").read_text())
        if retained["status"] != "PASS":
            raise ValueError("reference capture must be PASS")
        shutil.copyfile(capture / "record.json", output / "reference-record.json")
        source = output / "source"
        changed = {"host-kernel/native-rust/smp_application.rs", "host-kernel/native-rust/smp_service.rs"}
        current_copies = set(changed)
        compiled = {str(relative_record_path(row, "source")): row for row in retained["compiler_inputs"]}
        record["reference_rebindings"] = []
        # Generated vectors remain tied to exact producer bodies. Only the
        # explicitly reviewed producer files can differ outside those bodies;
        # the transport fixture must equal its actual retained compiler input.
        for row in retained["inputs"]:
            relative = relative_record_path(row, "original-inputs")
            verify(capture / "original-inputs" / relative, row)
            name = str(relative)
            if name in changed or identity(repo / relative) == {key: row[key] for key in ("size", "sha256")}:
                continue
            if name == "scripts/tests/fixtures/native-application-transport-failure.rs":
                verify(repo / relative, compiled[name])
                record["reference_rebindings"].append({"path": name,
                    "basis": "exact retained compiler input after formatting", **identity(repo / relative)})
            elif name in ("kernel/syscall.c", "kernel/rust/syscall_policy.rs"):
                old = (capture / "original-inputs" / relative).read_bytes()
                current = (repo / relative).read_bytes()
                bodies = [body for body in retained["extracted_bodies"] if body["source"] == name]
                if len(bodies) != 7:
                    raise ValueError(f"expected seven retained producer methods: {name}")
                for body in bodies:
                    exact = old[body["start_byte"]:body["end_byte"]]
                    if hashlib.sha256(exact).hexdigest() != body["sha256"] or current.count(exact) != 1:
                        raise ValueError(f"producer method drift: {name}:{body['name']}")
                    start = current.index(exact)
                    record["reference_rebindings"].append({"path": name, "name": body["name"],
                        "basis": "exact retained producer body", "start_byte": start,
                        "end_byte": start + len(exact), "sha256": body["sha256"]})
                if name.endswith(".rs"):
                    pattern = rb"^const EINVAL:[^\n]+;"
                    before, after = re.search(pattern, old, re.M), re.search(pattern, current, re.M)
                    if before is None or after is None or before[0] != after[0]:
                        raise ValueError("Rust producer EINVAL constant drift")
                    record["reference_rebindings"].append({"path": name, "name": "EINVAL",
                        "basis": "exact retained producer constant", "sha256": hashlib.sha256(after[0]).hexdigest()})
            else:
                raise ValueError(f"unreviewed reference input drift: {relative}")
            current_copies.add(name)
        for row in retained["compiler_inputs"]:
            relative = relative_record_path(row, "source")
            original = capture / "source" / relative
            verify(original, row)
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
        record["current_originals"] = []
        for relative in sorted(current_copies):
            original = output / "original-inputs" / relative
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / relative, original)
            shutil.copyfile(original, source / relative)
            record["current_originals"].append({"path": relative, **identity(original)})
        fixture = source / "scripts/tests/fixtures"
        patch = repo / "scripts/tests/fixtures/stability-service-failure-candidate.patch"
        shutil.copyfile(patch, output / "candidate.patch")
        record["candidate"] = identity(output / "candidate.patch")
        apply_exact_patch(source, output / "candidate.patch")
        shutil.copyfile(repo / "scripts/tests/fixtures/stability-service-failure.rs",
            fixture / "stability-service-failure.rs")
        app = Path("host-kernel/native-rust/smp_application.rs")
        service = Path("host-kernel/native-rust/smp_service.rs")
        old_methods = ["transport_health", "quarantine_transport", "fail_transport",
            "finish_publication", "expire_publications", "publish_syscall", "return_syscall"]
        (fixture / "native-application-transport-failure-methods.rs").write_text(
            "impl Remote {\n" + "".join(extract(source, app, name, record) for name in old_methods) + "}\n")
        (fixture / "native-application-committed-return-method.rs").write_text(
            "impl Remote {\n" + extract(source, app, "return_syscall", record) + "}\n")
        methods = ["reserve", "transport_health", "quarantine_transport", "fail_transport",
            "fail_service", "finish_publication", "publish_syscall", "return_syscall"]
        (fixture / "stability-service-failure-remote-methods.rs").write_text(
            "impl Remote {\n" + "".join(extract(source, app, name, record) for name in methods) + "}\n")
        (fixture / "stability-service-failure-runtime-methods.rs").write_text(
            "impl Runtime {\n" + "".join(extract(source, service, name, record) for name in ("fail", "pump")) + "}\n")
        main = fixture / "native-application-syscall.rs"
        main.write_text(main.read_text() + '\n#[allow(dead_code)]\n#[path = "stability-service-failure.rs"]\nmod service_failure;\n')
        # These are reviewable future commands, not commands executed by staging.
        record["proposed_commands"] = [
            ["rustc", "--edition", "2021", "-D", "warnings", "--test", str(main), "-o", str(output / "syscall-tests")],
            [str(output / "syscall-tests"), "--nocapture"],
        ]
        record["compiler_inputs"] = [{"path": str(path.relative_to(output)), **identity(path)}
            for path in sorted(source.rglob("*")) if path.is_file()]
        record["status"] = "STAGED_NOT_RUN"
    except BaseException as error:
        record.update(status="FAIL", error=str(error))
        raise
    finally:
        (output / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--reference-capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    stage(parser.parse_args())
