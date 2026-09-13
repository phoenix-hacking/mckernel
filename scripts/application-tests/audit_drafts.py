#!/usr/bin/env python3
"""Reconcile the immutable September 9 drafts without awarding execution credit.

The correction manifest is an explicit review of particular original bytes.
Nothing in this module repairs paths heuristically, edits released inputs, runs
fixtures, or treats a present source file as an implemented/accepted test.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


BASE = "docs/verification/evidence/application-drafts-20260909/ultra-handoff-1"
DEFAULT_CORRECTIONS = "docs/verification/application-draft-corrections-20260913.json"
CATALOG = "scripts/application-tests/cases.json"
QUEUE = "scripts/application-tests/draft-queue.json"
STATUSES = {"DRAFTED", "DRAFTED_WITH_UNRESOLVED", "BLOCKED", "FAILED"}
TAGS = {"already-specified-answer", "fixture-defect", "missing-observation", "missing-os-capability"}
MAX_INPUT_BYTES = 4 * 1024 * 1024


class AuditError(ValueError):
    """The frozen evidence cannot be reconciled exactly."""


def require(condition, message):
    if not condition:
        raise AuditError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def duplicate_free(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load_json(data):
    try:
        return json.loads(data, object_pairs_hook=duplicate_free)
    except (ValueError, UnicodeError) as error:
        raise AuditError("invalid JSON: " + str(error)) from error


class Reader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.inputs = {}

    def read(self, relative):
        pure = PurePosixPath(relative)
        require(not pure.is_absolute() and str(pure) == relative and ".." not in pure.parts,
                "not a canonical repository-relative path: " + relative)
        target = self.root
        for part in pure.parts:
            target /= part
            require(not target.is_symlink(), "symlink input forbidden: " + relative)
        require(target.is_file(), "missing regular input: " + relative)
        data = target.read_bytes()
        identity = {"path": relative, "sha256": digest(data), "size": len(data)}
        require(relative not in self.inputs or self.inputs[relative] == identity,
                "input changed during audit: " + relative)
        self.inputs[relative] = identity
        return data

    def json(self, path):
        return load_json(self.read(path))

    def verify(self, identity):
        data = self.read(identity["path"])
        require(digest(data) == identity["sha256"], "hash mismatch: " + identity["path"])
        if "size" in identity:
            require(len(data) == identity["size"], "size mismatch: " + identity["path"])
        return data

    def recheck(self):
        for identity in list(self.inputs.values()):
            self.verify(identity)


def pointer_escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def bounded_integer(value, name, maximum=MAX_INPUT_BYTES):
    require(type(value) is int and 0 <= value <= maximum, "invalid bounded " + name)
    return value


def hex_bytes(value):
    require(isinstance(value, str) and len(value) <= MAX_INPUT_BYTES * 2,
            "invalid hex input size")
    require(len(value) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in value),
            "invalid hexadecimal input")
    return bytes.fromhex(value)


def generated_bytes(generator):
    """Interpret explicit draft generators literally; never decode extra escapes.

    These bytes are audit observations, not independently approved runtime inputs.
    Descending padded integers mean count..1, width decimal columns plus newline.
    Unknown generators fail closed instead of being assumed correct.
    """
    kind = generator.get("kind")
    if kind in {"repeat-byte", "repeat-hex-sequence", "repeat-utf8"}:
        count = bounded_integer(generator.get("count"), "generator count")
        if kind == "repeat-utf8":
            require(isinstance(generator.get("text"), str), "missing generator text")
            unit = generator["text"].encode("utf-8")
        else:
            unit = hex_bytes(generator.get("hex_byte" if kind == "repeat-byte" else "hex"))
        require(kind != "repeat-byte" or len(unit) == 1, "repeat-byte requires exactly one byte")
        require(len(unit) * count <= MAX_INPUT_BYTES, "generated input exceeds bound")
        return unit * count
    if kind in {"numbered-lines", "descending-padded-integers"}:
        width = bounded_integer(generator.get("width"), "decimal width", 64)
        require(type(generator.get("newline")) is bool, "newline must be boolean")
        if kind == "numbered-lines":
            first = bounded_integer(generator.get("first"), "first number")
            last = bounded_integer(generator.get("last"), "last number")
            require(last >= first, "reversed numbered range")
            prefix = generator.get("prefix")
            require(isinstance(prefix, str), "missing numbered-line prefix")
            numbers = range(first, last + 1)
        else:
            count = bounded_integer(generator.get("count"), "integer count")
            numbers, prefix = range(count, 0, -1), ""
        result = bytearray()
        for number in numbers:
            result += (prefix + str(number).zfill(width) + ("\n" if generator["newline"] else "")).encode()
            require(len(result) <= MAX_INPUT_BYTES, "generated input exceeds bound")
        return bytes(result)
    raise AuditError("unreviewed generator kind: " + str(kind))


def input_observations(specification):
    observations = []
    entries = [("/input_files/" + pointer_escape(k), v)
               for k, v in sorted(specification.get("input_files", {}).items())]
    if "stdin" in specification:
        entries.append(("/stdin", specification["stdin"]))
    for pointer, entry in entries:
        representations = [key for key in ("hex", "generator") if key in entry]
        if not representations:
            require(entry == {"must_not_exist_before_run": True}, "missing input bytes at " + pointer)
            observations.append({"pointer": pointer, "state": "must-not-exist", "content_sha256": None})
            continue
        require(len(representations) == 1, "ambiguous input representation at " + pointer)
        data = hex_bytes(entry["hex"]) if "hex" in entry else generated_bytes(entry["generator"])
        claimed = entry.get("size")
        if claimed is not None:
            bounded_integer(claimed, "declared input length")
        claimed_hash = entry.get("sha256")
        observations.append({
            "pointer": pointer, "representation": representations[0],
            "declared_size": claimed, "observed_size": len(data),
            "size_matches": None if claimed is None else claimed == len(data),
            "declared_sha256": claimed_hash, "content_sha256": digest(data),
            "sha256_matches": None if claimed_hash is None else claimed_hash == digest(data),
            "state": "observed-literal-bytes-review-required",
        })
    return observations


def resolve_reference(reader, report_path, report_bytes, index, original, corrections):
    key = (report_path, index)
    correction = corrections.get(key)
    if correction is None:
        reader.verify(original)
        return original, False
    require(correction["report_sha256"] == digest(report_bytes), "correction report binding differs")
    require(correction["original"] == original, "correction original reference differs")
    target = correction["resolved"]
    reader.verify(target)
    require(correction["reason"], "correction has no explicit reason")
    return target, True


def audit(root, corrections_path=DEFAULT_CORRECTIONS):
    reader = Reader(root)
    reader.read("scripts/application-tests/audit_drafts.py")
    reader.read("scripts/tests/test_application_draft_audit.py")
    reader.read("docs/verification/evidence/application-draft-audit-initial-failure-20260913.json")
    policy = reader.json(corrections_path)
    require(policy["schema_version"] == 1 and policy["runtime_authorized"] is False,
            "invalid correction policy")
    for binding in policy["original_bindings"]:
        reader.verify(binding)
    queue = reader.json(QUEUE)
    catalog = reader.json(CATALOG)
    summary_path = BASE + "/queue-summary.json"
    summary = reader.json(summary_path)
    require(queue["execution_enabled"] is False, "released queue execution state changed")
    require(summary["queue_sha256"] == reader.inputs[QUEUE]["sha256"], "summary queue hash differs")
    catalog_cases = {c["id"]: c for c in catalog["cases"]}
    require(len(catalog_cases) == len(catalog["cases"]), "duplicate catalog case")
    require(len(queue["packets"]) == queue["packet_count"] == 97, "released packet count differs")
    require(len(catalog_cases) == queue["logical_case_count"] == 273, "released case count differs")
    summary_reports = {r["packet_id"]: r for r in summary["reports"]}
    require(len(summary_reports) == len(summary["reports"]) == 97, "summary report coverage differs")
    corrections = {(c["report_path"], c["reference_index"]): c for c in policy["reference_corrections"]}
    require(len(corrections) == len(policy["reference_corrections"]) == 9, "correction coverage differs")
    reviewed = {r["case_id"]: r for r in policy["fixture_reviews"]}
    require(len(reviewed) == len(policy["fixture_reviews"]), "duplicate fixture review")
    metadata = {r["report_path"]: r for r in policy["metadata_discrepancies"]}
    require(len(metadata) == len(policy["metadata_discrepancies"]), "duplicate metadata discrepancy")
    used_corrections, used_reviews, used_metadata, seen_cases = set(), set(), set(), set()
    packet_rows, case_rows, input_rows, report_documents = [], [], [], {}
    for packet in queue["packets"]:
        pid = packet["packet_id"]
        path = BASE + "/" + pid + "/report.json"
        require(summary_reports[pid]["path"] == path, "unexpected report path")
        report_bytes = reader.verify(summary_reports[pid])
        report = load_json(report_bytes)
        report_documents[pid] = report
        released_packet = reader.json(packet["path"])
        context_path = BASE + "/" + pid + "/context.json"
        context = load_json(reader.verify({"path": context_path, "sha256": report["context_sha256"]}))
        require(report["packet_id"] == pid, "report packet identity differs")
        if report["queue_sha256"] != summary["queue_sha256"]:
            discrepancy = metadata.get(path)
            require(discrepancy is not None and discrepancy["report_sha256"] == digest(report_bytes)
                    and discrepancy["field"] == "queue_sha256"
                    and discrepancy["original"] == report["queue_sha256"]
                    and discrepancy["expected"] == summary["queue_sha256"],
                    "unrecorded report queue identity discrepancy")
            used_metadata.add(path)
        require(report["packet_version"] == released_packet["version"], "packet version differs")
        expected_ids = packet["case_ids"]
        require(expected_ids == released_packet["case_ids"] == [c["case_id"] for c in report["cases"]]
                == [c["id"] for c in context["cases"]], "packet case coverage differs: " + pid)
        require(context["catalog_sha256"] == reader.inputs[CATALOG]["sha256"], "context catalog differs")
        references = []
        for index, original in enumerate(report["changed_files_with_sha256"]):
            resolved, corrected = resolve_reference(reader, path, report_bytes, index, original, corrections)
            references.append({"original": original, "resolved": resolved, "correction_applied": corrected})
            if corrected:
                used_corrections.add((path, index))
        resolved_paths = {r["resolved"]["path"] for r in references}
        for row in report["cases"]:
            cid = row["case_id"]
            require(cid in catalog_cases and cid not in seen_cases, "unknown or duplicate case: " + cid)
            seen_cases.add(cid)
            require(row["status"] in STATUSES, "invalid draft status: " + cid)
            fixture = row["fixture"]
            oracle = catalog_cases[cid]["oracle"]["artifact"]
            require(fixture in resolved_paths and oracle in resolved_paths, "case artifacts not bound: " + cid)
            fixture_bytes = reader.read(fixture)
            reader.json(oracle)
            inspection = {"status": "not-semantically-reviewed", "basis": "bytes present and hash-bound only"}
            if cid in reviewed:
                review = reviewed[cid]
                require(review["fixture"] == reader.inputs[fixture], "fixture review binding differs: " + cid)
                for evidence in review["source_evidence"]:
                    lines = fixture_bytes.decode("utf-8").splitlines()
                    require(lines[evidence["line"] - 1] == evidence["text"], "fixture review excerpt differs")
                require(review["status"] == "inspected-simulation-not-runtime-test", "invalid inspected verdict")
                inspection = review
                used_reviews.add(cid)
            elif fixture.endswith(".json"):
                specification = load_json(fixture_bytes)
                require(specification["case_id"] == cid, "input specification case differs")
                inspection = {"status": "input-specification-semantic-review-required",
                              "basis": "literal input bytes and generator sizes audited; utility execution not observed"}
                input_rows.append({"case_id": cid, "input": reader.inputs[fixture],
                                   "observations": input_observations(specification)})
            case_rows.append({
                "case_id": cid, "family": catalog_cases[cid]["family"], "packet_id": pid,
                "draft_status": row["status"], "fixture": reader.inputs[fixture],
                "oracle": reader.inputs[oracle], "fixture_inspection": inspection,
                "review_status": "not-approved-for-execution", "build_status": "not-established-by-draft-audit",
                "runtime_status": "not-established-by-draft-audit", "acceptance_status": "not-verified",
                "case_reviewer_question": row.get("max_reviewer_question"),
                "unresolved_oracle_notes": row.get("unresolved_oracle_notes", []),
                "requires": catalog_cases[cid]["requires"],
            })
        packet_rows.append({"packet_id": pid, "report": reader.inputs[path],
                            "context": reader.inputs[context_path], "case_ids": expected_ids,
                            "draft_status": report["draft_status"], "references": references})
    require(seen_cases == set(catalog_cases), "incomplete case coverage")
    require(used_corrections == set(corrections), "unused correction record")
    require(used_reviews == set(reviewed), "unused fixture review")
    require(used_metadata == set(metadata), "unused metadata discrepancy")
    counts = Counter(c["draft_status"] for c in case_rows)
    require(dict(counts) == {k: v for k, v in summary["case_status_counts"].items() if v}, "summary status counts differ")
    questions = policy["question_classifications"]
    require(len(questions) == len(summary["prioritized_max_questions"]) == 220, "question coverage differs")
    for index, question in enumerate(questions):
        require(question["index"] == index and question["text"] == summary["prioritized_max_questions"][index],
                "question identity differs")
        require(question["tags"] and set(question["tags"]) <= TAGS, "unknown question classification")
        require(question["text"] in report_documents[question["packet_id"]]["max_escalation"],
                "question source report differs")
        require(question["resolution_status"] == "review-routing-only", "classification attempts acceptance")
        for evidence in question["evidence"]:
            reader.verify(evidence["file"])
    input_findings = [{"case_id": r["case_id"], "input": r["input"], **o}
                      for r in input_rows for o in r["observations"]
                      if o.get("size_matches") is False or o.get("sha256_matches") is False]
    reader.recheck()
    return {
        "schema_version": 1, "audit_date": policy["audit_date"],
        "status": "AUDITED_WITH_BLOCKERS", "runtime_authorized": False,
        "acceptance_credit": False, "application_tests_accepted": 0,
        "scope": "Immutable draft reconciliation and conservative review routing; no compilation or execution.",
        "correction_manifest": reader.inputs[corrections_path],
        "counts": {"packets": len(packet_rows), "cases": len(case_rows),
                   "draft_status": dict(sorted(counts.items())), "corrected_references": len(used_corrections),
                   "report_metadata_discrepancies": len(used_metadata),
                   "prioritized_questions": len(questions),
                   "case_question_strings": sum(bool(c["case_reviewer_question"]) for c in case_rows),
                   "inspected_simulated_fixtures": len(used_reviews),
                   "input_specifications": len(input_rows), "input_length_or_hash_findings": len(input_findings)},
        "question_classifications": questions, "packets": packet_rows, "cases": case_rows,
        "report_metadata_discrepancies": policy["metadata_discrepancies"],
        "input_audit": input_rows, "input_findings": input_findings,
        "inputs": [reader.inputs[p] for p in sorted(reader.inputs)],
        "limitations": [
            "Question tags describe review work, not answers or accepted capabilities; missing-os-capability means missing acceptance evidence, not proof of absent implementation.",
            "Only the explicitly source-bound simulation fixtures have an implementation review verdict; all other fixtures still need individual semantic review.",
            "Generator bytes use literal JSON strings and explicit documented audit semantics; discrepancies require a new reviewed runtime input contract.",
            "Released packets, catalog, reports, queue summary, oracles, input files and historical scores remain unchanged.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--corrections", default=DEFAULT_CORRECTIONS)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--output", type=Path, help="create a new immutable audit; existing files are rejected")
    modes.add_argument("--check", type=Path, help="compare an existing audit to fresh deterministic recomputation")
    args = parser.parse_args(argv)
    try:
        result = audit(args.repo, args.corrections)
        encoded = canonical(result)
        if args.output:
            with args.output.open("xb") as stream:
                stream.write(encoded)
        elif args.check:
            require(not args.check.is_symlink(), "symlink audit forbidden")
            require(args.check.read_bytes() == encoded, "saved audit differs from fresh evidence")
        print(json.dumps({"status": result["status"], **result["counts"], "acceptance_credit": False}, sort_keys=True))
        return 0
    except (AuditError, OSError, KeyError, TypeError, IndexError) as error:
        print("draft audit rejected: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
