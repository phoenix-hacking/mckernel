#!/usr/bin/env python3
"""Generate a source-bound index of separate McKernel verification scopes.

This index copies authoritative statuses; it never promotes a gate, combines
historical scores, or converts infrastructure/source presence into runtime PASS.
Outputs are immutable snapshots: use a fresh filename after any input changes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import tarfile


TRACKERS = ("overview.txt", "overview2.txt", "migration.txt", "full-port.txt",
            "rust-source-retirement.txt", "final-push.txt", "VALIDATION_PROGRESS.MD")
LANGUAGE = "docs/verification/mckernel-rust-assembly-completion.md"
DRAFT_AUDIT = "docs/verification/application-draft-audit-20260913.json"
BOOTSTRAP = "docs/verification/stability-bootstrap-20260913.json"
BASELINES = (
    "docs/verification/native-application-readiness-20260909.json",
    "docs/verification/ultra-final-checkpoint-20260909.json",
)
COMPONENTS = (
    ("draft-reconciliation", "scripts/application-tests/audit_drafts.py", "scripts/tests/test_application_draft_audit.py"),
    ("supervision", "scripts/application-tests/supervisor.py", "scripts/tests/test_application_supervisor.py"),
    ("execution", "scripts/application-tests/run.py", "scripts/tests/test_application_runtime.py"),
    ("runtime-contracts", "scripts/application-tests/runtime_contracts.py", "scripts/tests/test_application_runtime_contracts.py"),
    ("reviewed-compilation", "scripts/application-tests/compile_reviewed.py", "scripts/tests/test_application_compile_reviewed.py"),
)
MAX_COMPILE_CAPTURE_BYTES = 95 * 1024 * 1024 - 1


class StateError(ValueError):
    """An authoritative source or immutable snapshot differs from its contract."""


def require(condition, message):
    if not condition:
        raise StateError(message)


def module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "cannot load " + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def dimensions(implementation="not-inferred", review="not-inferred", build="not-inferred",
               runtime="not-inferred", acceptance="not-verified"):
    return dict(implementation=implementation, review=review, build=build,
                runtime=runtime, acceptance=acceptance)


def excerpt(text, pattern):
    for line, value in enumerate(text.splitlines(), 1):
        if re.search(pattern, value):
            return {"line": line, "text": value}
    raise StateError("missing authoritative text: " + pattern)


def table_rows(text, heading, pattern):
    start = text.index(heading)
    base_line = text[:start].count("\n") + 1
    result = []
    for offset, line in enumerate(text[start:].splitlines()):
        match = re.match(pattern, line)
        if match:
            result.append({"line": base_line + offset, "fields": list(match.groups())})
        elif result:
            break
    require(result, "missing tracker table: " + heading)
    return result


def parse_language(text):
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r"\| (MK-LANG-\d{3}) \| (.*?) \| (.*?) \|", line)
        if not match:
            continue
        ident, condition, recorded = match.groups()
        status = recorded.split(":", 1)[0]
        require(status in {"TODO", "IN_PROGRESS", "BLOCKED", "PASS"}, "unknown language gate status")
        rows.append({"id": ident, "acceptance_condition": condition, "recorded_state": recorded,
                     "status": status, "source_line": number,
                     "dimensions": dimensions(acceptance=status)})
    require({r["id"] for r in rows} == {f"MK-LANG-{i:03d}" for i in range(1, 8)}
            and len(rows) == 7, "language gate coverage differs")
    return rows


def infrastructure_record(identity, record):
    return {
        "source": identity, "recorded_status": record.get("status", "no-status-field"),
        "recorded_fields": {k: v for k, v in record.items() if isinstance(v, (str, int, float, bool)) or v is None},
        "scope": "linked-record-only; consult original acceptance contract",
        "promotes_production_language_or_application_gate": False,
    }


def content_identity(data, path):
    return {"path": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def same_content(left, right):
    return left["size"] == right["size"] and left["sha256"] == right["sha256"]


def artifact_identity(row):
    require(isinstance(row, dict) and set(row) == {"path", "size", "sha256"}, "invalid artifact identity")
    require(isinstance(row["path"], str) and "\0" not in row["path"], "invalid artifact path")
    require(type(row["size"]) is int and 0 <= row["size"] <= MAX_COMPILE_CAPTURE_BYTES, "artifact size outside index bound")
    require(isinstance(row["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), "invalid artifact hash")
    return row


def repository_reference(row):
    """Only the declared /workspace mount maps container inputs to this repo."""
    artifact_identity(row)
    path = row["path"]
    if path.startswith("/workspace/"):
        path = path[len("/workspace/"):]
    pure = PurePosixPath(path)
    require(not pure.is_absolute() and str(pure) == path and ".." not in pure.parts and path != ".",
            "unmapped repository input: " + path)
    return dict(row, path=path)


def load_retentions(reader, paths):
    require(len(paths) == len(set(paths)), "duplicate retention manifest")
    result = []
    for path in paths:
        document = reader.json(path)
        require(document.get("status") == "PASS" and document.get("production_gate_credit") is False,
                "retention is not a verified nonproduction archive")
        require(document.get("new_catalog_acceptance") is False, "retention cannot award catalog acceptance")
        require(isinstance(document.get("captures"), list), "retention capture inventory missing")
        for capture in document["captures"]:
            reader.verify(artifact_identity(capture["archive"]))
        result.append({"source": reader.inputs[path], "document": document})
    return result


def compile_capture(reader, record_path, record, retentions):
    """Verify every retained regular member without extracting or running it."""
    matches = []
    for retention in retentions:
        for capture in retention["document"]["captures"]:
            if isinstance(capture.get("record"), dict) and same_content(capture["record"], reader.inputs[record_path]):
                matches.append((retention, capture))
    require(len(matches) == 1, "compile record needs exactly one matching retained capture")
    retention, capture = matches[0]
    require(capture.get("full_capture") is True and capture.get("excludes") == [] and capture.get("status") == "PASS",
            "compile capture is incomplete or not passing")
    source = capture["source"]
    require(isinstance(source, str) and PurePosixPath(source).parent == PurePosixPath("/work")
            and str(PurePosixPath(source)) == source, "compile capture must be a canonical direct /work child")
    artifact_identity(capture["record"])
    require(capture["record"]["path"] == source + "/record.json", "capture record path differs")
    require(isinstance(record.get("outputs"), list), "compile output inventory missing")
    expected = {}
    for row in [capture["record"], *record["outputs"]]:
        artifact_identity(row)
        path = PurePosixPath(row["path"])
        require(str(path) == row["path"] and ".." not in path.parts and row["path"].startswith(source + "/"),
                "compile output escapes capture")
        name = str(path.relative_to("/work"))
        require(name not in expected, "duplicate retained compile output")
        expected[name] = row
    # This consumer reads one small compile capture, not arbitrary guest archives.
    require(sum(row["size"] for row in expected.values()) <= MAX_COMPILE_CAPTURE_BYTES,
            "compile capture exceeds bounded index reader")
    directories = {str(parent) for name in expected for parent in PurePosixPath(name).parents
                   if str(parent) != "."}
    require(record.get("command_environment") == {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
                                                  "TZ": "UTC", "TMPDIR": source + "/tmp"},
            "compile environment differs from reviewed helper")
    # The reviewed helper creates this empty preparation directory explicitly;
    # it has no regular output whose parents would otherwise account for it.
    directories.add(PurePosixPath(source).name + "/tmp")
    require(type(capture.get("exact_tree_members")) is int
            and capture["exact_tree_members"] == len(expected) + len(directories), "compile capture member inventory differs")
    members, seen, count = {}, set(), 0
    archive = reader.verify(capture["archive"])
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(archive)) as compressed:
            expanded = compressed.read(MAX_COMPILE_CAPTURE_BYTES + 1)
        require(len(expanded) <= MAX_COMPILE_CAPTURE_BYTES, "expanded compile archive exceeds reader bound")
        with tarfile.open(fileobj=io.BytesIO(expanded), mode="r|") as stream:
            for member in stream:
                count += 1
                require(count <= capture["exact_tree_members"], "compile archive has extra members")
                name = member.name
                pure = PurePosixPath(name)
                require(pure.parts and str(pure) == name and not pure.is_absolute() and ".." not in pure.parts
                        and pure.parts[0] == PurePosixPath(source).name, "unsafe compile archive member")
                require(name not in seen, "duplicate archive member")
                seen.add(name)
                if member.isdir():
                    require(member.size == 0 and name in directories, "unlisted or nonempty archive directory")
                    continue
                require(member.isfile() and name in expected, "unlisted or linked compile archive member")
                require(member.size == expected[name]["size"], "retained member size differs")
                handle = stream.extractfile(member)
                require(handle is not None, "missing archive member bytes")
                data = handle.read(member.size + 1)
                require(same_content(content_identity(data, name), expected[name]), "retained member hash differs: " + name)
                members[expected[name]["path"]] = data
    except (tarfile.TarError, EOFError) as error:
        raise StateError("invalid compile capture: " + str(error)) from error
    require(set(members) == {row["path"] for row in expected.values()}, "compile capture omits outputs")
    require(count == capture["exact_tree_members"],
            "compile capture member count differs")
    require(members[capture["record"]["path"]] == reader.read(record_path), "archived compile record differs")
    return members, {"manifest": retention["source"], "archive": capture["archive"],
                     "record": capture["record"], "verified_regular_files": len(members), "verified_tree_members": count}


def elf_interpreter(data):
    require(len(data) >= 64 and data[:7] == b"\x7fELF\x02\x01\x01", "expected little-endian ELF64")
    require(struct.unpack_from("<HH", data, 16) == (2, 62), "expected x86_64 ET_EXEC")
    offset = struct.unpack_from("<Q", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 54)
    require(size == 56 and count > 0 and offset + size * count <= len(data), "invalid ELF program table")
    interpreters, dynamic = [], False
    for index in range(count):
        kind, _, start, _, _, length, _, _ = struct.unpack_from("<IIQQQQQQ", data, offset + index * size)
        if kind == 2:
            dynamic = True
        if kind == 3:
            require(1 < length <= 4096 and start + length <= len(data), "invalid ELF interpreter segment")
            raw = data[start:start + length]
            require(raw.endswith(b"\0") and b"\0" not in raw[:-1] and raw.startswith(b"/"), "invalid interpreter path")
            interpreters.append(raw[:-1].decode("ascii"))
    require(dynamic and len(interpreters) == 1, "expected dynamic ELF with one interpreter")
    return interpreters[0]


def reviewed_compilations(reader, paths, retentions, infrastructure):
    require(len(paths) == len(set(paths)), "duplicate explicit compile record")
    revisions = {}
    helper_reviews = [document for _, document in infrastructure
                      if document.get("record_kind") == "independent-compile-helper-source-review"]
    for path in paths:
        record = reader.json(path)
        require(type(record.get("schema_version")) is int and record["schema_version"] == 1
                and record.get("status") == "PASS" and record.get("phase") == "complete", "compile record did not complete")
        for field in ("linux_reference_executed", "mckernel_application_executed", "application_acceptance", "production_gate_credit"):
            require(record.get(field) is False, "compile record cannot promote runtime or acceptance: " + field)
        packet_ref = repository_reference(record["packet"])
        review_ref = repository_reference(record["independent_review"])
        packet = reader.json(packet_ref["path"])
        review = reader.json(review_ref["path"])
        reader.verify(packet_ref)
        reader.verify(review_ref)
        require(type(review.get("schema_version")) is int and review["schema_version"] == 1
                and review.get("record_kind") == "independent-source-and-oracle-review"
                and review.get("status") == "SOURCE_REVIEW_ACCEPTABLE_FOR_PINNED_COMPILATION",
                "independent review status/schema/kind does not authorize compilation")
        require(review.get("compile_authorized") is True and review.get("runtime_authorized") is False
                and review.get("execution_enabled") is False, "independent review is not compile-only")
        for field in ("application_acceptance", "production_gate_credit"):
            require(field not in review or review[field] is False,
                    "independent review cannot award acceptance: " + field)
        require(review["reviewed_packet"] == packet_ref, "independent review binds a different packet")
        require(packet.get("execution_enabled") is False and packet.get("mode") == "fixture-review-and-compile",
                "reviewed packet is not compile-only")
        require(type(packet.get("active_cases_max")) is int and packet["active_cases_max"] == 3
                and isinstance(packet.get("cases"), list) and 1 <= len(packet["cases"]) <= 3, "invalid compile packet case bound")
        selected = packet["cases"]
        ids = [case["case_id"] for case in selected]
        require(len(ids) == len(set(ids)) and ids == packet["case_ids"]
                and ids == [case["case_id"] for case in record["cases"]], "compile case membership differs")
        require(review["reviewed_sources"] == [case["source"] for case in selected]
                and review["reviewed_oracles"] == [case["oracle"] for case in selected], "review source/oracle membership differs")
        catalog = reader.json(packet["catalog"]["path"])
        reader.verify(packet["catalog"])
        reader.verify(packet["original_packet"])
        originals = {case["id"]: case for case in catalog["cases"]}
        matched_reviews = [item for item in helper_reviews if same_content(item["reviewed_helper"], record["helper"])
                           and item.get("compile_authorized") is True and item.get("runtime_authorized") is False
                           and item.get("execution_enabled") is False and item.get("reviewed_packet") == packet_ref
                           and item.get("independent_packet_review") == review_ref]
        require(len(matched_reviews) == 1, "compile helper requires an exact independently reviewed binding via --record")
        helper_review = matched_reviews[0]
        require(type(helper_review.get("schema_version")) is int and helper_review["schema_version"] == 1
                and helper_review.get("status") == "STATIC_REVIEW_ACCEPTABLE_FOR_PINNED_COMPILATION",
                "compile helper review status/schema does not authorize compilation")
        for field in ("application_acceptance", "production_gate_credit"):
            require(helper_review.get(field) is False, "compile helper review cannot award acceptance: " + field)
        helper_review_path = next(p for p, document in infrastructure if document is helper_review)
        members, capture = compile_capture(reader, path, record, retentions)

        def retained(row):
            artifact_identity(row)
            require(row["path"] in members and same_content(content_identity(members[row["path"]], row["path"]), row),
                    "compiled artifact not retained exactly")
            return members[row["path"]]

        retained(record["helper"])
        commands = {}
        capture_root = str(PurePosixPath(capture["record"]["path"]).parent)
        for command in record["commands"]:
            require(command["label"] not in commands and type(command.get("exit_code")) is int
                    and command["exit_code"] == 0, "duplicate or failed compiler command")
            require(type(command.get("timeout_seconds")) is int and 0 < command["timeout_seconds"] <= 120,
                    "compiler command exceeds preparation bound")
            require(command.get("cwd") == capture_root and capture_root + "/" + command["label"] + ".log" in members,
                    "compiler command log/cwd is not retained")
            commands[command["label"]] = command
        require(record.get("compiler_tools") and record.get("compiler_dependencies"), "compiler input identities missing")
        for row in record["compiler_tools"] + record["compiler_dependencies"]:
            artifact_identity(row)
        dependencies = {}
        for row in record["compiler_dependencies"]:
            require(row["path"] not in dependencies or same_content(row, dependencies[row["path"]]),
                    "conflicting compiler dependency identities")
            dependencies[row["path"]] = row
        for case, compiled in zip(selected, record["cases"]):
            cid = case["case_id"]
            require(cid in originals and cid not in revisions, "unknown or multiply credited compiled case")
            require(compiled.get("compile_status") == "PASS" and compiled.get("runtime_status") == "NOT_RUN"
                    and compiled.get("acceptance_status") == "NOT_RUN", "case is not compile-only")
            reader.verify(case["source"])
            reader.verify(case["oracle"])
            require(same_content(case["source"], compiled["source"]) and same_content(case["oracle"], compiled["oracle"]),
                    "compiled source/oracle differs from independent review")
            retained(compiled["source"])
            retained(compiled["oracle"])
            executable = retained(compiled["executable"])
            require(elf_interpreter(executable) == compiled["interpreter"], "recorded interpreter differs from retained ELF")
            contract = originals[cid]["payload_contract"]
            require(contract["build_profile"] == "ordinary-dynamic-etexec-c11"
                    and contract["feature_test_macros"] == ["_GNU_SOURCE"], "unsupported reviewed compile profile")
            folder = str(PurePosixPath(compiled["executable"]["path"]).parent)
            expected_compile = ["cc", "-std=c11", "-O2", "-g", "-Wall", "-Wextra", "-Werror", "-fno-pie", "-pthread",
                                "-D_GNU_SOURCE", "-MD", "-MF", folder + "/compiler.d", "-c", compiled["source"]["path"], "-o", folder + "/payload.o"]
            expected_link = ["cc", "-no-pie", "-pthread", "-Wl,-z,noexecstack", "-Wl,-Map," + folder + "/link.map",
                             folder + "/payload.o", "-o", compiled["executable"]["path"]]
            for suffix, argv in (("compile", expected_compile), ("link", expected_link),
                                 ("elf", ["readelf", "-h", "-l", "-d", compiled["executable"]["path"]]),
                                 ("disassembly", ["objdump", "-d", compiled["executable"]["path"]]),
                                 ("libraries", ["ldd", compiled["executable"]["path"]])):
                require(commands.get(cid + "-" + suffix, {}).get("argv") == argv, "missing or changed compile/ELF command: " + cid + "-" + suffix)
            for suffix in ("/payload.o", "/compiler.d", "/link.map"):
                require(folder + suffix in members and members[folder + suffix], "missing retained compiler evidence")
            compiler_names = set(members[folder + "/compiler.d"].decode("utf-8").replace("\\\n", " ").split()[1:])
            compiler_names.update(re.findall(r"^LOAD (/.+)$", members[folder + "/link.map"].decode("utf-8"), re.M))
            require(compiler_names and compiler_names <= dependencies.keys(), "compiler dependency inventory is incomplete")
            for name in compiler_names & members.keys():
                retained(dependencies[name])
            elf_log = members[capture_root + "/" + cid + "-elf.log"].decode("utf-8")
            require("ELF64" in elf_log and "EXEC (Executable file)" in elf_log
                    and "Advanced Micro Devices X86-64" in elf_log and "INTERP" in elf_log,
                    "retained ELF inspection differs")
            require(members[capture_root + "/" + cid + "-disassembly.log"], "disassembly capture is empty")
            library_log = members[capture_root + "/" + cid + "-libraries.log"].decode("utf-8")
            require("not found" not in library_log, "runtime library inspection reported a missing library")
            traced_libraries = set(re.findall(r"(/[^\s()]+)\s+\(0x[0-9a-f]+\)", library_log))
            require(isinstance(compiled["runtime_libraries"], list) and compiled["runtime_libraries"], "runtime closure missing")
            library_names = []
            for library in compiled["runtime_libraries"]:
                artifact_identity(library["original"])
                require(same_content(library["original"], library["captured"]), "copied DSO differs")
                retained(library["captured"])
                library_names.append(library["original"]["path"])
            require(len(library_names) == len(set(library_names)) and compiled["interpreter"] in library_names,
                    "runtime closure duplicates or omits interpreter")
            require(set(library_names) == traced_libraries, "runtime closure differs from retained loader trace")
            revisions[cid] = {"packet_id": packet["packet_id"], "packet_version": packet["version"],
                              "packet": packet_ref, "independent_review": review_ref,
                              "compile_helper_review": reader.inputs[helper_review_path],
                              "compile_record": reader.inputs[path], "retention": capture,
                              "source": case["source"], "oracle": case["oracle"], "executable": compiled["executable"],
                              "interpreter": compiled["interpreter"], "runtime_libraries": compiled["runtime_libraries"],
                              "dimensions": dimensions("SOURCE_INSPECTED_OPERATION_IMPLEMENTED", "INDEPENDENTLY_REVIEWED",
                                                       "COMPILED", "NOT_RUN", "NOT_VERIFIED"),
                              "runtime_authorized": False, "application_acceptance": False}
    return revisions


def baseline_relation(reader, path):
    record = reader.json(path)
    require(record.get("status") == "PASS" and record.get("production_gate_credit") is False
            and record.get("new_catalog_runtime_acceptance") is False and record.get("new_catalog_cases_accepted") == 0,
            "baseline cannot promote catalog or production acceptance")
    rows = []
    for old in record["native_compiler_bindings"] + record["guest_production_bindings"]:
        reader.read(old["path"])
        current = reader.inputs[old["path"]]
        rows.append({"path": old["path"], "historical": {k: old[k] for k in ("path", "size", "sha256")},
                     "current": current, "relation": "MATCH" if same_content(old, current) else "CHANGED"})
    for artifact in record["artifacts"]:
        reader.verify(artifact["published"])
    return {"source": reader.inputs[path], "scope": "historical-exact-artifact-baseline",
            "original_suites_passed": record["original_suites_passed"], "selected_pair": record["selected_pair"],
            "source_relations": rows, "changed_source_paths": sorted({row["path"] for row in rows if row["relation"] == "CHANGED"}),
            "current_source_acceptance": False, "catalog_acceptance_credit": False,
            "current_runtime_replayed_by_this_index": False}


def tracker_summaries(texts):
    result = []
    for path in TRACKERS:
        text = texts[path]
        row = {"path": path, "scope": "historical-scoped-accounting", "combined_os_score": None}
        if path in {"overview.txt", "overview2.txt"}:
            row["claims"] = [excerpt(text, r"^Functional dashboard average"),
                             excerpt(text, r"^McKernel-owned core row average"),
                             excerpt(text, r"^Mechanical LOC audit share")]
            row["rows"] = table_rows(text, "Current Progress Baseline" if path == "overview.txt" else "Completion Dashboard",
                                      r"^(.+?)\s{2,}(\d{1,3})\s{2,}.*$")
            row["interpretation"] = "Functional estimates; runtime and actual language closure are separate."
        elif path == "migration.txt":
            row["claims"] = [excerpt(text, r"^Current tracked standalone Rust sequencing score")]
            row["standalone_rows"] = table_rows(text, "Standalone Rust Readiness Table", r"^(.+?)\s{2,}(\d{1,3})\s{2,}.*$")
            row["core_rows"] = table_rows(text, "Core OS Ownership Table", r"^(.+?)\s{2,}(\d{1,3})\s{2,}(\d{1,3})\s{2,}.*$")
            row["interpretation"] = "Capped sequencing campaign; 500/500 does not prove every primitive is Rust."
        elif path == "full-port.txt":
            row["claims"] = [excerpt(text, r"^Overall non-arm full port"),
                             excerpt(text, r"^Current verified aggregate category movement")]
            row["rows"] = table_rows(text, "Current Full Standalone Percentages", r"^(.+?)\s{2,}(\d+\.\d+)%\s+(\d+\.\d+)%$")
            row["interpretation"] = "Closed historical category campaign, not current production acceptance."
        elif path == "rust-source-retirement.txt":
            row["rows"] = table_rows(text, "Master category completion table:",
                r"^\| (?!Category )(.+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(n/a|[\d.]+%)\s*\|\s*(n/a|[\d.]+%)\s*\|$")
            row["row_columns"] = ["category", "rows", "scored", "zero", "partial", "complete", "allowlisted", "completion", "left"]
            row["claims"] = [excerpt(text, r"614,183 / 783,847"), excerpt(text, r"783,895 total \(78\.356795%\)"),
                             excerpt(text, r"^  100\.0% source-retirement|^- The 100\.0% source-retirement")]
            row["interpretation"] = "Declaration/allowlist closure; 62 n/a boundaries include compiled C. Exact-image Rust bytes remain a separate historical artifact measurement."
        elif path == "VALIDATION_PROGRESS.MD":
            row["claims"] = [excerpt(text, r"Historical Rocky 8\.10 smoke completion")]
            row["rows"] = table_rows(text, "## Completion gates", r"^\| (?!Gate )(.+?) \| (\d+)% \| (PASS|TODO|IN_PROGRESS|BLOCKED) \| (.*?) \|$")
            row["interpretation"] = "Recorded ten-stage Rocky 8.10 smoke on its exact artifact set; no current catalog or whole-system acceptance."
        else:
            row["scope"] = "native-host-production-acceptance"
            row["claims"] = [excerpt(text, r"^OVERALL COMPLETION:"), excerpt(text, r"^TRACKED GATES:"),
                             excerpt(text, r"^RELEASE READY:")]
            row["interpretation"] = "All 130 original contracts remain mandatory; only authoritative PASS earns its fixed points."
        result.append(row)
    return result


def build_state(root, record_paths=(), snapshot_date="2026-09-13", compile_paths=(), retention_paths=(), baseline_paths=()):
    root = Path(root).resolve()
    auditor = module_from_path("verification_state_audit", root / "scripts/application-tests/audit_drafts.py")
    tracker = module_from_path("verification_state_final_push", root / "scripts/final_push_tracker.py")
    reader = auditor.Reader(root)
    for path in ("scripts/application-tests/verification_state.py", "scripts/tests/test_verification_state.py",
                 "scripts/final_push_tracker.py", "scripts/application-tests/audit_drafts.py"):
        reader.read(path)
    texts = {path: reader.read(path).decode("utf-8") for path in TRACKERS}
    production = tracker.summary_data(*tracker.parse_tracker(texts["final-push.txt"]))
    require(production["gate_count"] == 130, "production gate count differs")
    require(tracker.replace_summary(texts["final-push.txt"], tracker.render_summary(production)) == texts["final-push.txt"],
            "authoritative production generated summary is stale")
    for gate in production["gates"]:
        gate["source_line"] = excerpt(texts["final-push.txt"], r"^GATE\|" + re.escape(gate["ident"]) + r"\|")["line"]
        gate["dimensions"] = dimensions(acceptance=gate["status"])
    language = parse_language(reader.read(LANGUAGE).decode("utf-8"))
    audit_bytes = reader.read(DRAFT_AUDIT)
    draft = auditor.load_json(audit_bytes)
    require(auditor.canonical(auditor.audit(root)) == audit_bytes, "draft audit is stale or altered")
    for identity in draft["inputs"]:
        reader.verify(identity)
    questions = draft["question_classifications"]
    cases = []
    for index, case in enumerate(draft["cases"]):
        cases.append({
            "case_id": case["case_id"], "family": case["family"], "packet_id": case["packet_id"],
            "draft_status": case["draft_status"], "fixture": case["fixture"], "oracle": case["oracle"],
            "requires": case["requires"], "draft_audit_pointer": "/cases/" + str(index),
            "dimensions": dimensions(case["fixture_inspection"]["status"], case["review_status"],
                                     case["build_status"], case["runtime_status"], case["acceptance_status"]),
            "packet_question_indices": [q["index"] for q in questions if q["packet_id"] == case["packet_id"]],
            "question_attribution": "packet-level review questions; not all questions necessarily apply to every case",
        })
    baseline_rows = []
    for path in BASELINES:
        record = reader.json(path)
        require(record.get("production_gate_credit") is False, "unexpected baseline production credit")
        keys = ("status", "scope", "source_parent", "application_readiness_complete", "repetitions", "limitations",
                "actual_hello_applications", "original_core_replays", "original_control_replays", "new_futex_logical_cases",
                "new_signal_guest_cases", "new_valid_shared_vm_child_tid_case", "application_catalog_runtime_verified",
                "actual_vector_runtime_verified", "transport_runtime_injection_verified", "external_signal_restart_status",
                "runtime_inputs", "selected_pair")
        baseline_rows.append({"source": reader.inputs[path], "scope": "historical-exact-artifact-baseline",
                              "recorded_facts": {k: record[k] for k in keys if k in record},
                              "current_runtime_replayed_by_this_index": False, "catalog_acceptance_credit": False})
    infrastructure = []
    infrastructure_documents = []
    paths = [BOOTSTRAP, DRAFT_AUDIT, *record_paths]
    require(len(paths) == len(set(paths)), "duplicate infrastructure record")
    for path in paths:
        record = reader.json(path)
        archive = record.get("archive")
        if isinstance(archive, dict) and "path" in archive and "sha256" in archive:
            reader.verify(archive)
        infrastructure.append(infrastructure_record(reader.inputs[path], record))
        infrastructure_documents.append((path, record))
    retentions = load_retentions(reader, retention_paths)
    revisions = reviewed_compilations(reader, compile_paths, retentions, infrastructure_documents)
    require(set(revisions) <= {case["case_id"] for case in cases}, "compiled revision outside audited catalog")
    for case in cases:
        case["reviewed_revisions"] = [revisions[case["case_id"]]] if case["case_id"] in revisions else []
    require(len(baseline_paths) == len(set(baseline_paths)), "duplicate explicit baseline")
    baseline_rows.extend(baseline_relation(reader, path) for path in baseline_paths)
    components = []
    for name, source, tests in COMPONENTS:
        row = {"component": name, "dimensions": dimensions(implementation="source-not-present", acceptance="not-verified")}
        for label, path in (("source", source), ("test_source", tests)):
            if (root / path).exists():
                reader.read(path)
                row[label] = reader.inputs[path]
                if label == "source":
                    row["dimensions"]["implementation"] = "source-present-semantic-review-required"
            else:
                row[label] = {"path": path, "state": "not-present-at-snapshot"}
        row["test_source_is_test_result"] = False
        components.append(row)
    trackers = tracker_summaries(texts)
    for row in trackers:
        row["source"] = reader.inputs[row["path"]]
    reader.recheck()
    return {
        "schema_version": 2, "snapshot_date": snapshot_date, "status": "EVIDENCE_INDEX_ONLY",
        "objective": "Full functionality, stability, native production acceptance and Rust/assembly completion; no timeline limit.",
        "runtime_authorized_by_this_index": False, "combined_whole_os_percentage": None,
        "source_change_does_not_inherit_old_acceptance": True,
        "trackers": trackers, "native_production": production,
        "language": {"source": reader.inputs[LANGUAGE], "gates": language,
                     "status_counts": dict(sorted(Counter(r["status"] for r in language).items()))},
        "applications": {"source": reader.inputs[DRAFT_AUDIT], "counts": draft["counts"], "cases": cases,
                         "question_classifications": questions, "input_findings": draft["input_findings"],
                         "report_metadata_discrepancies": draft["report_metadata_discrepancies"],
                         "reviewed_and_compiled_cases": len(revisions), "executed_catalog_cases": 0,
                         "accepted_catalog_cases": 0, "acceptance_basis": "Drafting and explicitly bound compile revisions establish no catalog runtime acceptance."},
        "historical_baselines": baseline_rows, "infrastructure_records": infrastructure,
        "infrastructure_sources": components,
        "record_paths": list(record_paths),
        "compile_record_paths": list(compile_paths), "retention_paths": list(retention_paths),
        "baseline_record_paths": list(baseline_paths),
        "retentions": [{"source": item["source"], "captures": item["document"]["captures"],
                        "promotes_any_acceptance": False} for item in retentions],
        "inputs": [reader.inputs[path] for path in sorted(reader.inputs)],
        "limitations": [
            "Historical tracker scores have different denominators and are never averaged into OS completion.",
            "A gate's recorded acceptance status does not imply separately reviewed implementation, build or runtime evidence on the current source.",
            "Additional infrastructure records are linked without automatic status promotion, even when a record's status says PASS.",
            "Explicit compile records add source/review/build revisions only; original draft identities/statuses and every runtime/acceptance dimension are preserved.",
            "Compilation archive verification is bounded to 95 MiB expanded bytes per selected capture; archives are streamed and never extracted or executed.",
            "Only the original final-push tracker controls production points; only original MK-LANG rows control recorded language status.",
            "This is a dated snapshot. New runtime acceptances need their independently reviewed source-bound records and a fresh snapshot format/version that consumes them explicitly.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--record", action="append", default=[], help="explicit additional repository-relative infrastructure record")
    parser.add_argument("--compile-record", action="append", default=[], help="explicit compile-only record; requires its helper review via --record and a matching --retention")
    parser.add_argument("--retention", action="append", default=[], help="repository-relative retained capture manifest")
    parser.add_argument("--baseline-record", action="append", default=[], help="explicit exact-pair baseline with historical/current source comparison")
    parser.add_argument("--date", default="2026-09-13")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--output", type=Path, help="create a new snapshot exclusively")
    modes.add_argument("--check", type=Path, help="recompute and compare an existing immutable snapshot")
    args = parser.parse_args(argv)
    try:
        require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date), "invalid snapshot date")
        state = build_state(args.repo, args.record, args.date, args.compile_record, args.retention, args.baseline_record)
        encoded = (json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
        if args.output:
            with args.output.open("xb") as stream:
                stream.write(encoded)
        if args.check:
            require(not args.check.is_symlink() and args.check.read_bytes() == encoded, "saved state differs from current inputs")
        print(json.dumps({"status": state["status"], "trackers": len(state["trackers"]),
                          "production_gates": state["native_production"]["gate_count"],
                          "production_points": state["native_production"]["earned_points"],
                          "language_gates": len(state["language"]["gates"]),
                          "cases": len(state["applications"]["cases"]),
                          "reviewed_and_compiled_cases": state["applications"].get("reviewed_and_compiled_cases", 0),
                          "accepted_catalog_cases": state["applications"]["accepted_catalog_cases"]}, sort_keys=True))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        print("verification state rejected: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
