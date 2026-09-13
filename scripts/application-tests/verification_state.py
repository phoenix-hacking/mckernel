#!/usr/bin/env python3
"""Generate a source-bound index of separate McKernel verification scopes.

This index copies authoritative statuses; it never promotes a gate, combines
historical scores, or converts infrastructure/source presence into runtime PASS.
Outputs are immutable snapshots: use a fresh filename after any input changes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys


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
)


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


def build_state(root, record_paths=(), snapshot_date="2026-09-13"):
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
    paths = [BOOTSTRAP, DRAFT_AUDIT, *record_paths]
    require(len(paths) == len(set(paths)), "duplicate infrastructure record")
    for path in paths:
        record = reader.json(path)
        archive = record.get("archive")
        if isinstance(archive, dict) and "path" in archive and "sha256" in archive:
            reader.verify(archive)
        infrastructure.append(infrastructure_record(reader.inputs[path], record))
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
        "schema_version": 1, "snapshot_date": snapshot_date, "status": "EVIDENCE_INDEX_ONLY",
        "objective": "Full functionality, stability, native production acceptance and Rust/assembly completion; no timeline limit.",
        "runtime_authorized_by_this_index": False, "combined_whole_os_percentage": None,
        "source_change_does_not_inherit_old_acceptance": True,
        "trackers": trackers, "native_production": production,
        "language": {"source": reader.inputs[LANGUAGE], "gates": language,
                     "status_counts": dict(sorted(Counter(r["status"] for r in language).items()))},
        "applications": {"source": reader.inputs[DRAFT_AUDIT], "counts": draft["counts"], "cases": cases,
                         "question_classifications": questions, "input_findings": draft["input_findings"],
                         "report_metadata_discrepancies": draft["report_metadata_discrepancies"],
                         "accepted_catalog_cases": 0, "acceptance_basis": "No catalog runtime acceptance is established by the immutable draft audit."},
        "historical_baselines": baseline_rows, "infrastructure_records": infrastructure,
        "infrastructure_sources": components,
        "record_paths": list(record_paths),
        "inputs": [reader.inputs[path] for path in sorted(reader.inputs)],
        "limitations": [
            "Historical tracker scores have different denominators and are never averaged into OS completion.",
            "A gate's recorded acceptance status does not imply separately reviewed implementation, build or runtime evidence on the current source.",
            "Additional infrastructure records are linked without automatic status promotion, even when a record's status says PASS.",
            "Only the original final-push tracker controls production points; only original MK-LANG rows control recorded language status.",
            "This is a dated snapshot. New runtime acceptances need their independently reviewed source-bound records and a fresh snapshot format/version that consumes them explicitly.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--record", action="append", default=[], help="explicit additional repository-relative infrastructure record")
    parser.add_argument("--date", default="2026-09-13")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--output", type=Path, help="create a new snapshot exclusively")
    modes.add_argument("--check", type=Path, help="recompute and compare an existing immutable snapshot")
    args = parser.parse_args(argv)
    try:
        require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date), "invalid snapshot date")
        state = build_state(args.repo, args.record, args.date)
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
                          "accepted_catalog_cases": state["applications"]["accepted_catalog_cases"]}, sort_keys=True))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        print("verification state rejected: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
