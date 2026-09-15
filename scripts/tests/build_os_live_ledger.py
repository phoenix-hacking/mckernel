#!/usr/bin/env python3
"""Build the M00-B live ledger without granting execution or acceptance."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    "gate_map": "docs/verification/os-milestones-20260914/gate-map.json",
    "case_map": "docs/verification/os-milestones-20260914/case-map.json",
    "draft_audit": "docs/verification/application-draft-audit-20260913.json",
    "corrections": "docs/verification/application-draft-corrections-20260913.json",
    "state_index": "docs/verification/stability-state-20260913-2.json",
    "hard_review": "docs/verification/stability-prepublish-hard-independent-review-20260913.json",
    "permanent_review": "docs/verification/stability-permanent-backpressure-independent-review-20260913.json",
    "published_review": "docs/verification/stability-published-preparation-results-independent-review-20260913.json",
}


def load(relative):
    path = ROOT / relative
    raw = path.read_bytes()
    return json.loads(raw), {
        "path": relative,
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def unique(values, label, expected):
    if len(values) != expected or len(set(values)) != expected:
        raise ValueError(f"{label} must contain {expected} unique values")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    loaded, identities = {}, {}
    for name, relative in INPUTS.items():
        loaded[name], identities[name] = load(relative)

    gates = loaded["gate_map"]
    cases = loaded["case_map"]
    audit = loaded["draft_audit"]
    corrections = loaded["corrections"]
    state = loaded["state_index"]
    native = gates["native_gates"]
    language = gates["language_gates"]
    case_rows = cases["cases"]
    unique([row["id"] for row in native], "native gate IDs", 130)
    unique([row["id"] for row in language], "language gate IDs", 7)
    unique([row["id"] for row in case_rows], "case IDs", 273)
    packet_ids = sorted({row["packet_id"] for row in case_rows})
    unique(packet_ids, "packet IDs", 97)
    if sum(cases["family_counts"].values()) != 273:
        raise ValueError("family counts do not sum to 273")
    if {row["case_id"] for row in audit["cases"]} != {row["id"] for row in case_rows}:
        raise ValueError("draft and routing case IDs differ")
    if audit["correction_manifest"]["sha256"] != identities["corrections"]["sha256"]:
        raise ValueError("correction manifest hash mismatch")

    counts = audit["counts"]
    expected = {
        "cases": 273,
        "packets": 97,
        "corrected_references": 9,
        "input_length_or_hash_findings": 7,
        "inspected_simulated_fixtures": 22,
        "prioritized_questions": 220,
    }
    for name, value in expected.items():
        if counts[name] != value:
            raise ValueError(f"unexpected {name}: {counts[name]}")
    if len(corrections["reference_corrections"]) != 9:
        raise ValueError("expected nine reference corrections")
    if len(audit["input_findings"]) != 7:
        raise ValueError("expected seven input findings")
    if len(corrections["fixture_reviews"]) != 22:
        raise ValueError("expected 22 fixture reviews")
    if len(corrections["question_classifications"]) != 220:
        raise ValueError("expected 220 question classifications")
    if state["status"] != "EVIDENCE_INDEX_ONLY" or state["runtime_authorized_by_this_index"]:
        raise ValueError("state index unexpectedly authorizes runtime")

    packets = []
    for packet_id in packet_ids:
        members = [row for row in case_rows if row["packet_id"] == packet_id]
        paths = {row["packet_path"] for row in members}
        positions = {row["queue_position"] for row in members}
        if len(paths) != 1 or len(positions) != 1:
            raise ValueError(f"inconsistent packet mapping: {packet_id}")
        packets.append({
            "id": packet_id,
            "path": next(iter(paths)),
            "queue_position": next(iter(positions)),
            "case_ids": [row["id"] for row in members],
        })

    hard = loaded["hard_review"]
    permanent = loaded["permanent_review"]
    if hard.get("status") != "PASS_PREPUBLICATION_HARD_FAULT_ONLY" or not hard.get("hard_mode_verified"):
        raise ValueError("hard-fault review is not the accepted narrow record")
    if permanent.get("status") != "PASS_PERMANENT_BACKPRESSURE_FAULT_ONLY" or not permanent.get("permanent_backpressure_mode_verified"):
        raise ValueError("permanent-backpressure review is not the accepted narrow record")

    ledger = {
        "schema_version": 1,
        "record_kind": "os_milestone_live_ledger",
        "status": "LIVE_LEDGER_NO_NEW_ACCEPTANCE",
        "generated_from_commit": "5b2fc8ae8898aeded607d86557904173106d8b24",
        "execution_authorized": False,
        "acceptance_changed": False,
        "inputs": identities,
        "production": {
            "gate_count": 130,
            "total_points": gates["total_points"],
            "earned_points": gates["earned_points"],
            "status_counts": gates["status_counts"],
            "gates": native,
        },
        "language": {"gate_count": 7, "gates": language},
        "applications": {
            "case_count": 273,
            "packet_count": 97,
            "accepted_cases": cases["accepted_cases"],
            "executed_cases": cases["executed_cases"],
            "reviewed_compiled_cases": cases["reviewed_compiled_cases"],
            "global_execution_gates": cases["global_execution_gates"],
            "family_counts": cases["family_counts"],
            "packets": packets,
            "cases": case_rows,
        },
        "reconciliation": {
            "reference_corrections": [dict(id=f"correction-{i:03d}", **row) for i, row in enumerate(corrections["reference_corrections"], 1)],
            "input_findings": [dict(id=f"input-finding-{i:03d}", **row) for i, row in enumerate(audit["input_findings"], 1)],
            "simulated_fixture_reviews": [dict(id=f"fixture-review-{i:03d}", **row) for i, row in enumerate(corrections["fixture_reviews"], 1)],
            "reviewer_question_classifications": [dict(id=f"question-{i:03d}", **row) for i, row in enumerate(corrections["question_classifications"], 1)],
            "metadata_discrepancies": corrections["metadata_discrepancies"],
            "status": corrections["status"],
            "runtime_authorized": corrections["runtime_authorized"],
        },
        "transport_fault_modes": [
            {"id": "prepublication-hard", "status": "ACCEPTED_NARROW_ONLY", "review": identities["hard_review"], "whole_transport_gate_verified": False},
            {"id": "permanent-backpressure", "status": "ACCEPTED_NARROW_ONLY", "review": identities["permanent_review"], "whole_transport_gate_verified": False},
            {"id": "postpublish-notify", "status": "BLOCKED_SOURCE_BINDING_AND_RUNTIME", "review": identities["published_review"], "whole_transport_gate_verified": False},
            {"id": "recoverable-backpressure", "status": "OPEN", "whole_transport_gate_verified": False},
        ],
        "limitations": [
            "This ledger reconciles IDs and retained statuses only; it grants no build, guest, application, production, language or release acceptance.",
            "Historical baseline status and source review are never promoted to current runtime acceptance.",
            "The two accepted transport outcomes are narrow mode contracts and do not satisfy the whole transport gate or physical full-ring requirement.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": ledger["status"],
        "output": str(args.output),
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "native_gates": 130,
        "language_gates": 7,
        "cases": 273,
        "packets": 97,
        "corrections": 9,
        "input_findings": 7,
        "simulated_fixtures": 22,
        "questions": 220,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
