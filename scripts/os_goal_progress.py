"""Closure-driven, read-only projection and bounded same-Root review advice.

The canonical closure ledger remains the only acceptance ledger. Neither a
target, a result receipt nor this monitor can close a check, admit an operation,
release a resource, restart a process or clear a hold. The controller persists
``observe_progress(...)["monitor"]`` as ``state["progress_monitor"]`` before
delivering its advisory through the existing guarded instruction mechanism.

Targets are finite plans, submitted through the controller's checked CLI. A
target has schema_version=1, an exact counted original_check, owner, next_action,
input_bindings (name -> SHA256), evidence ([{path, sha256}]), and operation (null
or {name, deadline_at, receipt:{path, sha256}}). Paths are repository-relative,
stable regular JSON files. Empty bindings/evidence are legal planning records,
but never prove readiness. Evidence adapters bind the original done_when digest
and exact input bindings; they do not create new acceptance conditions.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat


LEDGER_PATH = Path("docs/verification/m14-m15-closure-progress.json")
LEDGER_SCHEMA = "mckernel-m14-m15-closure-progress-v1"
ORIGINAL_COUNT = 156
# Freeze original identities and parentage, not noisy narrative or timestamps.
ORIGINAL_TASKS_SHA256 = "ccfef384dc2feed9aeac59f5fbc7c182e6189a03c5451a91d09236b9de59ee10"
ORIGINAL_REQUIREMENTS_SHA256 = "26ccae254b5e6112f24955cd1245279825b345a0960abfa58a1b3c2a80e6ce9d"
ORIGINAL_CONDITIONS_SHA256 = "e237f9433a4c0c79ac0757a76f8cd84c3b61ccd77856a4745e3ea708dbadf7da"
MAX_JSON_BYTES = 4 * 1024 ** 2
CHECKPOINT_SECONDS = 20 * 60
STALL_SECONDS = 2 * CHECKPOINT_SECONDS
VELOCITY_WINDOW_SECONDS = 30 * 60
VELOCITY_TARGET_LOW = 1
VELOCITY_TARGET_HIGH = 5
OPERATION_FRESH_SECONDS = 120
MAX_OPERATION_SECONDS = 24 * 60 * 60
MAX_TARGET_EVIDENCE = 64
EVIDENCE_SCHEMA = "mckernel-closure-evidence-v1"
OPERATION_SCHEMA = "mckernel-closure-operation-v1"
INPUT_RESOLUTION_SCHEMA = "mckernel-input-resolution-attempt-v1"
GATE_NAMES = ("source", "account", "owner", "resources", "permission")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _sha(value):
    _require(isinstance(value, str) and len(value) == 64
             and all(c in "0123456789abcdef" for c in value), "Expected a SHA256 identity")
    return value


def _text(value, name, maximum=2048):
    _require(isinstance(value, str) and value.strip() and len(value) <= maximum
             and not any(ord(c) < 32 or ord(c) == 127 for c in value), name + " must be bounded text")
    return value


def _epoch(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif type(value) in (float, int):
        _require(math.isfinite(value), "Timestamp must be finite")
        return float(value)
    else:
        raise ValueError("Timestamp is missing or malformed")
    _require(parsed.tzinfo is not None, "Timestamp must include a timezone")
    return parsed.timestamp()


def _utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def _json_file(path):
    """Bounded stable read, with no symlink or named-file replacement fallback."""
    path = Path(path)
    _require(not any(part.is_symlink() for part in (path, *path.parents)), "Symlinked evidence is not exact")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_JSON_BYTES,
                 "Expected bounded regular JSON")
        chunks, size = [], 0
        while size <= before.st_size:
            chunk = os.read(fd, min(65536, before.st_size + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        after, named = os.fstat(fd), path.stat(follow_symlinks=False)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        _require(size == before.st_size and identity(before) == identity(after) == identity(named),
                 "JSON changed during its read")
        raw = b"".join(chunks)
        def unique(pairs):
            value = {}
            for key, item in pairs:
                _require(key not in value, "Duplicate JSON field is UNKNOWN")
                value[key] = item
            return value
        result = json.loads(raw, object_pairs_hook=unique,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON is UNKNOWN")))
        _require(isinstance(result, dict), "JSON record must be an object")
        return result, hashlib.sha256(raw).hexdigest()
    finally:
        os.close(fd)


def load_ledger(repo):
    ledger, _ = _json_file(Path(repo) / LEDGER_PATH)
    validate_ledger(ledger)
    return ledger


def validate_ledger(ledger):
    """Reject invented/reparented originals and changing the fixed denominator."""
    _require(isinstance(ledger, dict) and ledger.get("schema") == LEDGER_SCHEMA
             and ledger.get("original_criteria_unchanged") is True,
             "Canonical original closure criteria are missing or changed")
    maps = {}
    for key in ("tasks", "requirements"):
        rows = ledger.get(key)
        _require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
                 "Canonical " + key + " are missing")
        ids = [row.get("id") for row in rows]
        _require(all(isinstance(ident, str) and ident for ident in ids)
                 and len(ids) == len(set(ids)), "Duplicate or malformed canonical identities")
        maps[key] = {row["id"]: row for row in rows}
    counted = {ident: row for ident, row in maps["tasks"].items()
               if row.get("counted_in_requirement_rollup") is True}
    identity = lambda rows: _digest(sorted((ident, row.get("parent")) for ident, row in rows.items()))
    _require(len(counted) == ORIGINAL_COUNT and identity(counted) == ORIGINAL_TASKS_SHA256,
             "Original 156 counted checks or their parentage changed")
    _require(identity(maps["requirements"]) == ORIGINAL_REQUIREMENTS_SHA256,
             "Original requirement identities or parentage changed")
    _require(all(type(row.get("percent_complete")) in (int, float)
                 and row["percent_complete"] in (0, 100) and isinstance(row.get("done_when"), str)
                 and row["done_when"].strip() for row in counted.values()),
             "Counted checks require original binary completion and conditions")
    _require(_digest(sorted((ident, row["done_when"]) for ident, row in counted.items()))
             == ORIGINAL_CONDITIONS_SHA256, "Original completion conditions changed")
    _require(all(type(row.get("accepted")) is bool for row in maps["requirements"].values()),
             "Original acceptance must remain explicit and binary")
    for milestone, files, integrations in (("M14", 6, 3), ("M15", 8, 4)):
        expected = ({f"{milestone}-F{n:02d}" for n in range(1, files + 1)} |
                    {f"{milestone}-I{n:02d}" for n in range(1, integrations + 1)})
        summary = ledger.get("summaries", {}).get(milestone, {})
        actual = summary.get("original_gate_ids")
        _require(isinstance(actual, list) and len(actual) == len(expected) and set(actual) == expected
                 and summary.get("original_file_gate_count") == files
                 and summary.get("original_integration_gate_count") == integrations
                 and type(summary.get("milestone_accepted")) is bool,
                 milestone + " original gate/acceptance metadata changed")
    return {"tasks": counted, "requirements": maps["requirements"]}


def original_check_ids(*, repo=None, ledger=None):
    """Exact membership for source-work attachments, including original gates."""
    if ledger is None:
        ledger = load_ledger(repo if repo is not None else Path(__file__).resolve().parents[1])
    rows = validate_ledger(ledger)
    return frozenset(rows["tasks"]) | frozenset(rows["requirements"])


def condition_sha256(row):
    return hashlib.sha256(row["done_when"].encode("utf-8")).hexdigest()


def priority_milestone(ledger):
    """One acceptance lane at a time; independent agents share its open work."""
    validate_ledger(ledger)
    return next((name for name in ("M14", "M15")
                 if ledger["summaries"][name]["milestone_accepted"] is not True), None)


def dispatcher_agent_instruction(priority):
    """Describe actual finite agent assignments, not imaginary RPC authority."""
    lane = ("The current closure lane is " + priority + ". " if priority else
            "M14 and M15 are accepted; continue the remaining original whole-OS milestones in their recorded order. ")
    return (
        lane + "The GPT-6.1 Sol/MAX Root is the sole dispatcher/compositor. At each eligible dispatch "
        "cycle, account for EVERY existing active or idle child owner and each genuinely free "
        "admitted child slot. Give each eligible owner a specific finite original-check "
        "deliverable through followup_task (or the already supported child-assignment method): "
        "exact original ID, unchanged done_when, source/header/ABI input to resolve, smallest "
        "implementation action, focused verification, evidence path, and return-to-Root handoff. "
        "Assign disjoint changes and independent verification in parallel WITHIN the current "
        "milestone; do not start new next-milestone closure work before its predecessor is "
        "accepted. Reuse existing owners before spawning within the actual child/resource "
        "limits. Never redirect or duplicate healthy in-flight work, held/unknown owners, "
        "rejected requests or uncertain delivery. One Root integrates and qualifies evidence. "
        "Target 1-5 NEW verified original-check closures per rolling 30 minutes; this is an "
        "operational goal, never a reason to weaken acceptance, invent work or overrun limits. "
        "At each checkpoint count only new binary original-check closures, name the next "
        "finite fix for any deficit, and keep progressing after each verified closure. "
    )


def remaining_work_view(ledger):
    """Finite original obligations, without readiness claims or a new task graph."""
    tasks = validate_ledger(ledger)["tasks"]
    return [{"original_check": ident, "parent": row.get("parent"), "done_when": row["done_when"],
             "execution_profile": row.get("execution_profile"), "dependencies": row.get("dependencies", []),
             "title": row.get("title"), "admission": "UNASSESSED"}
            for ident, row in tasks.items() if row["percent_complete"] == 0]


def remaining_work_instruction(remaining, priority=None):
    """Select bounded candidates from the earliest unfinished acceptance lane."""
    if not remaining:
        return ("No counted original check remains open. Review only the exact original binary gate/milestone "
                "acceptance still absent; do not invent another counted check. ")
    if priority in ("M14", "M15"):
        candidates = [row for row in remaining
                      if row["original_check"].startswith(priority + "-")][:5]
    else:
        candidates = remaining[:5]
    text = (f"The canonical finite remaining-work view has {len(remaining)} open original checks. "
            + ("Current required milestone: " + priority + ". " if priority else "")
            + "Concrete candidates for the existing Root to assess (UNASSESSED, not execution grants): ")
    if candidates:
        text += "; ".join(row["original_check"] + " [parent=" + str(row.get("parent"))
                          + ", recorded profile=" + str(row.get("execution_profile")) + "]: " + str(row.get("title"))
                          for row in candidates) + ". "
    else:
        text += ("No counted check remains open in " + priority +
                 "; finish its unchanged original file/integration gates and binary acceptance before advancing. ")
    return text + ("Use " + str(LEDGER_PATH) + " for every exact original done_when condition and recorded dependency. "
                   "Assign independent eligible work in the current milestone to existing admitted agents; "
                   "do not dispatch next-milestone closure before the current milestone's original acceptance. "
                   "Recorded dependencies mix source work, native admission and acceptance order, so this list confers no readiness or resource grant. ")


def input_resolution_instruction():
    return (
        "Missing engineering inputs are finite next actions, not terminal blockers: derive the real source/header/caller/ABI and behavior "
        "contracts; fetch pinned dependencies or SDKs; install missing required packages within actual permissions and aggregate resource "
        "admission; and implement real missing adapters/provider code while preserving the complete original supported behavior. "
        "Then run the affected verification after its genuine admission and qualify its actual scope. Implement the future ordinary HOST "
        "runner's real provider adapter as our engineering work when needed; do not ask the user for an inventory or substitute a fake provider. "
        "Precisely block only an absent external artifact, external access/hardware, or an actual hold, supported by a concrete attempted "
        "resolution, its recorded outcome and supplying owner. Never fabricate an input/result, replace an original condition or clear an actual hold. ")


def _bindings(value):
    _require(isinstance(value, dict) and len(value) <= 64, "Input bindings must be a finite map")
    return {_text(name, "Input name", 256): _sha(digest) for name, digest in sorted(value.items())}


def _reference(value):
    _require(isinstance(value, dict) and set(value) == {"path", "sha256"}, "Exact evidence reference required")
    path = Path(_text(value["path"], "Evidence path", 4096))
    _require(not path.is_absolute() and ".." not in path.parts and ".git" not in path.parts,
             "Evidence must name a repository-relative file")
    return {"path": str(path), "sha256": _sha(value["sha256"])}


def validate_target(data, ledger, repo):
    """Validate a finite controller-submitted plan; no admission is implied."""
    rows = validate_ledger(ledger)
    _require(isinstance(data, dict) and set(data) == {
        "schema_version", "original_check", "owner", "next_action", "input_bindings", "evidence", "operation"}
        and type(data["schema_version"]) is int and data["schema_version"] == 1,
        "Exact closure target schema_version=1 is required")
    _require(data["original_check"] in rows["tasks"], "Target must name one of the original 156 counted checks")
    _require(isinstance(data["evidence"], list) and len(data["evidence"]) <= MAX_TARGET_EVIDENCE,
             "Target evidence must be a bounded list")
    result = {"schema_version": 1, "original_check": data["original_check"],
              "owner": _text(data["owner"], "Target owner", 512),
              "next_action": _text(data["next_action"], "Target next action"),
              "input_bindings": _bindings(data["input_bindings"]),
              "evidence": [_reference(ref) for ref in data["evidence"]], "operation": None}
    if data["operation"] is not None:
        operation = data["operation"]
        _require(isinstance(operation, dict) and set(operation) == {"name", "deadline_at", "receipt"},
                 "Exact bounded operation reference required")
        result["operation"] = {"name": _text(operation["name"], "Operation name", 512),
                               "deadline_at": _utc(_epoch(operation["deadline_at"])),
                               "receipt": _reference(operation["receipt"])}
    # Resolve existing parents without opening or granting any referenced payload.
    root = Path(repo).resolve()
    for ref in result["evidence"] + ([result["operation"]["receipt"]] if result["operation"] else []):
        path = root / ref["path"]
        _require(root in path.resolve().parents and not any(part.is_symlink() for part in (path, *path.parents)),
                 "Evidence reference escapes the repository or uses a symlink")
    return result


def load_target(path, repo):
    data, _ = _json_file(path)
    return validate_target(data, load_ledger(repo), repo)


def _read_reference(repo, ref):
    value, actual = _json_file(Path(repo) / ref["path"])
    _require(actual == ref["sha256"], "Evidence bytes changed from the submitted reference")
    return value


def _matching(receipt, target, row):
    return (receipt.get("original_check") == row["id"]
            and receipt.get("condition_sha256") == condition_sha256(row)
            and bool(target["input_bindings"])
            and receipt.get("input_bindings") == target["input_bindings"])


def _resolution(receipt, target, row, repo):
    value = receipt.get("resolution")
    _require(isinstance(value, dict) and set(value) == {
        "classification", "attempted_action", "outcome", "missing_input", "supplying_owner", "evidence"},
        "A blocked input needs an exact recorded resolution attempt")
    _require(value["classification"] in {"engineering", "external", "actual_hold"}, "Unknown input-resolution classification")
    for field in ("attempted_action", "outcome", "missing_input", "supplying_owner"):
        _text(value[field], "Input resolution " + field)
    reference = _reference(value["evidence"])
    attempt = _read_reference(repo, reference)
    if attempt.get("schema") == "mckernel-host-operation-v1":
        _require(attempt.get("payload_state") in {"PASS", "FAIL"}
                 and isinstance(attempt.get("spec"), dict)
                 and attempt["spec"].get("closure_target") == {
                     "original_check": row["id"], "condition_sha256": condition_sha256(row),
                     "input_bindings": target["input_bindings"]},
                 "Input-resolution runner result has no actual matching attempted payload")
        attempt_status = "completed" if attempt["payload_state"] == "PASS" else "failed"
    else:
        _require(attempt.get("schema") == INPUT_RESOLUTION_SCHEMA and _matching(attempt, target, row)
                 and attempt.get("status") in {"completed", "failed", "refused_by_actual_hold"}
                 and all(attempt.get(field) == value[field] for field in (
                     "classification", "attempted_action", "outcome", "missing_input", "supplying_owner")),
                 "Input-resolution attempt is absent, unknown or mismatched")
        attempt_status = attempt["status"]
    return dict(value, attempt_status=attempt_status)


def _evidence_semantics(receipt, target, row, repo=None):
    if receipt.get("schema") == "mckernel-host-operation-v1":
        # A runner PASS is a payload outcome, never qualification. Only the
        # runner's explicit ordinary payload failure adapter is understood here.
        adapter = receipt.get("ordinary_failure")
        _require(receipt.get("payload_state") == "FAIL" and isinstance(adapter, dict)
                 and isinstance(receipt.get("spec"), dict)
                 and receipt["spec"].get("closure_target") == {
                     "original_check": row["id"], "condition_sha256": condition_sha256(row),
                     "input_bindings": target["input_bindings"]},
                 "Runner result has no matching ordinary failure adapter")
        receipt = adapter
    _require(receipt.get("schema") == EVIDENCE_SCHEMA and _matching(receipt, target, row),
             "Evidence does not match the original condition and exact nonempty inputs")
    kind = receipt.get("kind")
    common = {"original_check": row["id"], "condition_sha256": condition_sha256(row),
              "input_bindings": target["input_bindings"], "kind": kind}
    if kind == "required_evidence":
        facts = receipt.get("qualified_fact_sha256s")
        _require(receipt.get("status") == "qualified" and receipt.get("scope") in {"partial", "whole"}
                 and isinstance(facts, list) and 1 <= len(facts) <= 64,
                 "Required evidence needs positively qualified, finite result facts")
        return dict(common, scope=receipt["scope"], facts=sorted(set(_sha(fact) for fact in facts)))
    if kind == "blocker_disposition":
        _require(receipt.get("status") in {"blocked", "resolved"}, "Blocker disposition is unknown")
        result = dict(common, blocker_sha256=_sha(receipt.get("blocker_sha256")), disposition=receipt["status"])
        resolution = _resolution(receipt, target, row, repo)
        if receipt["status"] == "blocked":
            result["resolution_classification"] = resolution["classification"]
        else:
            _require(resolution["attempt_status"] == "completed",
                     "A resolved blocker requires an actual matching completed resolution result")
        return result
    if kind == "ordinary_failure":
        _require(receipt.get("status") == "failed", "Failure result is unknown")
        return dict(common, stage=_text(receipt.get("stage"), "Failed stage", 256),
                    diagnostic_sha256=_sha(receipt.get("diagnostic_sha256")))
    raise ValueError("Unknown evidence kind")


def _operation_view(repo, target, row, now):
    operation = target["operation"]
    if operation is None:
        return {"status": "UNKNOWN", "reason": "No current bounded operation evidence"}
    receipt = _read_reference(repo, operation["receipt"])
    _require(receipt.get("schema") == OPERATION_SCHEMA and _matching(receipt, target, row)
             and receipt.get("name") == operation["name"], "Operation evidence does not match the target")
    started, deadline, observed = (_epoch(receipt.get(key)) for key in ("started_at", "deadline_at", "observed_at"))
    _require(started <= observed <= now + 5 and started < deadline <= started + MAX_OPERATION_SECONDS
             and _utc(deadline) == operation["deadline_at"], "Operation has no exact finite declared deadline")
    if receipt.get("status") == "running" and receipt.get("healthy") is True and now < deadline:
        # This receipt positively establishes one named healthy bounded
        # operation. Its frozen deadline survives heartbeat silence; it cannot
        # be extended by changing attempt IDs or generic activity.
        return {"status": "HEALTHY_BOUNDED_OPERATION", "name": operation["name"],
                "deadline_at": _utc(deadline), "operation_binding_sha256": _digest({
                    "original_check": row["id"], "condition_sha256": condition_sha256(row),
                    "input_bindings": target["input_bindings"]}),
                "liveness": "FRESH_DECLARED_HEALTH" if -5 <= now - observed <= OPERATION_FRESH_SECONDS else "DECLARED_BOUNDED_PROTECTION_ONLY",
                "reason": "A matching durable receipt declared this named operation healthy; preserve its original bounded deadline. This is not a process-liveness verification"}
    if (receipt.get("status") == "ready" and now < deadline
            and -5 <= now - observed <= OPERATION_FRESH_SECONDS
            and isinstance(receipt.get("gates"), dict)
            and all(receipt["gates"].get(name) == "clear" for name in GATE_NAMES)):
        return {"status": "READY_FOR_CONTROLLER_REVIEW", "name": operation["name"],
                "deadline_at": _utc(deadline), "reason": "Positive matching operation evidence; actual fresh admission remains required"}
    return {"status": "UNKNOWN", "reason": "Operation is expired, unhealthy or lacks positive matching gates"}


def _last_closure(ledger, closed):
    candidates = []
    for record in ledger.get("verified_completion_updates", []):
        if isinstance(record, dict) and isinstance(record.get("task_ids"), list):
            ids = [ident for ident in record["task_ids"] if ident in closed]
            if ids:
                try:
                    candidates.append((_epoch(record.get("at")), ids))
                except (ValueError, TypeError, OverflowError):
                    pass
    for row in ledger["tasks"]:
        if row["id"] in closed and row.get("verified_at") is not None:
            try:
                candidates.append((_epoch(row["verified_at"]), [row["id"]]))
            except (ValueError, TypeError, OverflowError):
                pass
    if not candidates:
        return {"original_checks": [], "at": None}
    at, ids = max(candidates, key=lambda item: item[0])
    return {"original_checks": sorted(ids), "at": _utc(at)}


def project_progress(ledger, *, repo=None, state=None, now=None):
    """Pure derived status apart from optional exact evidence-file reads."""
    rows, state = validate_ledger(ledger), state or {}
    now = _epoch(now if now is not None else datetime.now(timezone.utc))
    closed = sorted(ident for ident, row in rows["tasks"].items() if row["percent_complete"] == 100)
    snapshot = {"schema_version": 1, "authority": "derived_only", "counted_total": ORIGINAL_COUNT,
                "closed_original_checks": closed, "remaining_count": ORIGINAL_COUNT - len(closed),
                "accepted_original_gates": sorted(ident for ident, row in rows["requirements"].items()
                                                  if row.get("accepted") is True),
                "unaccepted_original_gates": sorted(ident for summary in ledger["summaries"].values()
                    for ident in summary["original_gate_ids"] if rows["requirements"][ident]["accepted"] is not True),
                "milestone_acceptance": {name: ledger["summaries"][name]["milestone_accepted"] for name in ("M14", "M15")},
                "priority_milestone": priority_milestone(ledger),
                "last_original_closure": _last_closure(ledger, set(closed)),
                "remaining_work": remaining_work_view(ledger),
                "current_target": None, "target_status": "NEEDS_TARGET", "remaining_conditions": [],
                "next_action": "Existing Root must choose one exact original check and submit a finite closure target",
                "evidence_records": [], "ordinary_failures": [], "evidence_errors": [],
                "operation": {"status": "UNKNOWN", "reason": "No current target"},
                "retained_capacity": "UNKNOWN; retain all existing owner/resource/UNKNOWN reservations"}
    retained = state.get("progress_retained_capacity")
    if isinstance(retained, dict) and retained.get("verified") is True:
        # Display only: resource authority and progress never come from this metadata.
        snapshot["retained_capacity"] = {key: retained[key] for key in ("owner_count", "bytes", "jobs")
                                         if type(retained.get(key)) is int and retained[key] >= 0}
    data = state.get("closure_target")
    if data is None:
        return snapshot
    try:
        target = validate_target(data, ledger, repo if repo is not None else Path(__file__).resolve().parents[1])
        row = rows["tasks"][target["original_check"]]
        snapshot.update(current_target={"original_check": row["id"], "owner": target["owner"]},
                        target_status="CLOSED_IN_CANONICAL_LEDGER" if row["id"] in closed else "UNKNOWN",
                        next_action=target["next_action"], remaining_conditions=[] if row["id"] in closed else [row["done_when"]])
        snapshot["target_binding_sha256"] = _digest({"original_check": row["id"],
            "condition_sha256": condition_sha256(row), "input_bindings": target["input_bindings"], "owner": target["owner"]})
        snapshot["scope_limit"] = row.get("scope_limit")
        snapshot["dependency_caveat"] = "Ledger dependencies mix source prerequisites, native admission and acceptance order; they are not execution grants"
        for ref in target["evidence"]:
            receipt = None
            try:
                receipt = _read_reference(repo, ref)
                semantic = _evidence_semantics(receipt, target, row, repo)
                record = {"key": _digest(semantic), "semantic": semantic, "reference": ref}
                if semantic["kind"] == "ordinary_failure":
                    adapter = receipt.get("ordinary_failure", receipt)
                    record["defect"] = _text(adapter.get("defect"), "Concrete defect")
                    record["owner"] = _text(adapter.get("owner"), "Defect owner", 512)
                    snapshot["ordinary_failures"].append(record)
                else:
                    snapshot["evidence_records"].append(record)
                    if (row["id"] not in closed and semantic["kind"] == "blocker_disposition"
                            and semantic["disposition"] == "blocked"):
                        engineering = semantic["resolution_classification"] == "engineering"
                        if engineering or snapshot["target_status"] != "INPUT_RESOLUTION_REQUIRED":
                            snapshot["target_status"] = "INPUT_RESOLUTION_REQUIRED" if engineering else "BLOCKED_BY_MATCHING_RECEIPT"
                            snapshot["input_resolution"] = {key: receipt["resolution"][key] for key in (
                                "classification", "attempted_action", "outcome", "missing_input", "supplying_owner")}
            except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
                snapshot["evidence_errors"].append(str(error))
                if (isinstance(receipt, dict) and receipt.get("schema") == EVIDENCE_SCHEMA
                        and receipt.get("kind") == "blocker_disposition" and receipt.get("status") in {"blocked", "resolved"}
                        and row["id"] not in closed):
                    snapshot["target_status"] = "INPUT_RESOLUTION_REQUIRED"
                    snapshot["input_resolution_error"] = "A proposed blocker has no matching actual resolution attempt: " + str(error)
        try:
            snapshot["operation"] = _operation_view(repo, target, row, now)
            if snapshot["target_status"] not in {"CLOSED_IN_CANONICAL_LEDGER", "BLOCKED_BY_MATCHING_RECEIPT", "INPUT_RESOLUTION_REQUIRED"}:
                snapshot["target_status"] = snapshot["operation"]["status"]
        except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
            snapshot["operation"] = {"status": "UNKNOWN", "reason": str(error)}
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        snapshot.update(target_status="UNKNOWN", next_action="Correct the rejected finite target; existing holds remain",
                        target_error=str(error))
    from os_goal_repair import _GLOBAL_HOLDS, _LANE_HOLDS
    held = [key for key in _GLOBAL_HOLDS + _LANE_HOLDS if key in state and state[key] is not False]
    if state.get("stop_now") or state.get("checkpoint_requested") or state.get("stop_reason"):
        held.append("controller_stop_or_checkpoint")
    if held:
        snapshot["current_holds"] = held
        snapshot["unheld_target_status"] = snapshot["target_status"]
        if snapshot["target_status"] != "CLOSED_IN_CANONICAL_LEDGER":
            snapshot["target_status"] = "HELD_OR_UNKNOWN"
    snapshot["results"] = {"qualified_matching_records": len(snapshot["evidence_records"]),
                           "ordinary_failed_stages": [record["semantic"]["stage"] for record in snapshot["ordinary_failures"]],
                           "evidence_error_count": len(snapshot["evidence_errors"])}
    return snapshot


def _advisory(snapshot, reason):
    target = snapshot.get("current_target") or {}
    ident = target.get("original_check", "UNSELECTED original check")
    failures = snapshot.get("ordinary_failures", [])
    text = ("Harness-origin closure review instruction (not a live user instruction). "
            "Functional McKernel OS/apps and Rust/allowed-assembly migration only; no security testing. "
            + reason + " Original target: " + ident + ". ")
    text += input_resolution_instruction()
    text += dispatcher_agent_instruction(snapshot.get("priority_milestone"))
    if snapshot.get("input_resolution"):
        resolution = snapshot["input_resolution"]
        text += ("Recorded missing input: " + resolution["missing_input"] + "; supplying owner: " + resolution["supplying_owner"]
                 + "; attempted resolution: " + resolution["attempted_action"] + "; actual recorded outcome: " + resolution["outcome"] + ". ")
    if snapshot.get("remaining_work") is not None:
        text += remaining_work_instruction(snapshot["remaining_work"], snapshot.get("priority_milestone"))
    if failures:
        failure = failures[0]
        text += ("Preserve the exact failed " + failure["semantic"]["stage"] + " result and diagnostic "
                 + failure["semantic"]["diagnostic_sha256"] + ". Give existing owner " + failure["owner"]
                 + " one bounded correction for this concrete defect: " + failure["defect"] + ". Reuse passing evidence; "
                 "run only the affected check after its actual fresh admission. ")
    text += ("The existing Root must make and record one concrete decision: accept already complete matching evidence "
             "against the unchanged original condition in the canonical ledger; fix the exact confirmed ordinary defect once; "
             "supply the specifically missing input through its named owner; or precisely block this original check with "
             "the missing input, supplying owner and next action. Submit/update the finite target through the checked controller. "
             "Partial cases and source-only preparation cannot close a whole original condition. "
             "Do not treat heartbeat, new attempt IDs, generic activity, dependency order or this advisory as progress or "
             "execution authority. Preserve healthy named operations, all stops, holds, ownership and retained capacity; "
             "do not kill/restart processes, release holds or replay held work.")
    return text


def _accepted_record(record, tasks):
    """Validate a controller-owned durable accepted record, never narrative."""
    _require(isinstance(record, dict) and set(record) == {"key", "semantic", "reference"},
             "Malformed durable accepted progress record")
    value = record["semantic"]
    _require(isinstance(value, dict) and value.get("original_check") in tasks
             and value.get("condition_sha256") == condition_sha256(tasks[value["original_check"]]),
             "Accepted progress record has an unknown original condition")
    common = {"original_check", "condition_sha256", "input_bindings", "kind"}
    _require(bool(_bindings(value.get("input_bindings"))), "Accepted evidence lacks actual input bindings")
    if value.get("kind") == "required_evidence":
        _require(set(value) == common | {"scope", "facts"} and value["scope"] in {"partial", "whole"}
                 and isinstance(value["facts"], list) and 1 <= len(value["facts"]) <= 64,
                 "Malformed accepted evidence facts")
        for fact in value["facts"]:
            _sha(fact)
    else:
        expected = common | {"blocker_sha256", "disposition"}
        if value.get("disposition") == "blocked":
            expected |= {"resolution_classification"}
            _require(value.get("resolution_classification") in {"engineering", "external", "actual_hold"},
                     "Unknown accepted input-resolution classification")
        _require(value.get("kind") == "blocker_disposition" and set(value) == expected
                 and value["disposition"] in {"blocked", "resolved"}, "Malformed accepted blocker disposition")
        _sha(value["blocker_sha256"])
    _reference(record["reference"])
    _require(_sha(record["key"]) == _digest(value), "Accepted semantic record identity changed")
    return record


def observe_progress(repo, state, now=None):
    """Observe once; caller atomically persists monitor before advisory delivery.

    Unchanged state yields one review key. ``review_required`` and
    ``decision_pending_seconds`` remain visible until qualified evidence or an
    original closure changes; heartbeat or finishing the review cannot rearm it.
    This deliberately returns advice even under a stop: only the controller's
    existing hard-stop and dispatch guards can decide whether advice is sent.
    """
    _require(isinstance(state, dict), "Controller state must be an object")
    now = _epoch(now if now is not None else datetime.now(timezone.utc))
    interval, stall = state.get("progress_checkpoint_seconds", CHECKPOINT_SECONDS), state.get("progress_stall_seconds", STALL_SECONDS)
    _require(type(interval) in (int, float) and math.isfinite(interval) and interval > 0
             and type(stall) in (int, float) and math.isfinite(stall) and stall >= interval,
             "Progress checkpoint/stall intervals must be finite and ordered")
    previous = state.get("progress_monitor")
    previous = previous if isinstance(previous, dict) and previous.get("schema_version") == 1 else {}
    tasks = {}
    try:
        ledger = load_ledger(repo)
        tasks = validate_ledger(ledger)["tasks"]
        snapshot = project_progress(ledger, repo=repo, state=state, now=now)
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        snapshot = {"schema_version": 1, "authority": "derived_only", "target_status": "UNKNOWN",
                    "ledger_error": str(error), "closed_original_checks": [], "evidence_records": [],
                    "ordinary_failures": [], "operation": {"status": "UNKNOWN"},
                    "next_action": "Reconcile the exact canonical ledger/input error; do not infer acceptance or execute"}
    protections = previous.get("operation_deadlines", {})
    protections = ({key: value for key, value in protections.items()
                    if isinstance(key, str) and type(value) in (float, int) and math.isfinite(value)}
                   if isinstance(protections, dict) else {})
    operation = snapshot["operation"]
    if operation.get("status") == "HEALTHY_BOUNDED_OPERATION":
        operation_key = operation["operation_binding_sha256"]
        deadline = _epoch(operation["deadline_at"])
        protections[operation_key] = min(protections.get(operation_key, deadline), deadline)
        operation["deadline_at"] = _utc(protections[operation_key])
        if now >= protections[operation_key]:
            operation.update(status="UNKNOWN", reason="The original bounded operation deadline expired; target/attempt metadata cannot renew it")
            if snapshot.get("target_status") == "HEALTHY_BOUNDED_OPERATION":
                snapshot["target_status"] = "UNKNOWN"
    records = {}
    # A durable accepted semantic record is retained across target changes. Never
    # import arbitrary model activity, receipt text, timestamps or attempt IDs.
    for record in previous.get("accepted_records", []):
        try:
            if not tasks and "ledger_error" in snapshot:
                # Retain the already durable observation during a read error;
                # it earns no new credit and will be revalidated on recovery.
                _require(isinstance(record, dict) and isinstance(record.get("semantic"), dict)
                         and record.get("key") == _digest(record["semantic"]), "Malformed retained record")
                records[record["key"]] = record
                continue
            record = _accepted_record(record, tasks)
            records[record["key"]] = record
        except (ValueError, KeyError, TypeError):
            snapshot.setdefault("evidence_errors", []).append("A retained evidence record is UNKNOWN or no longer matches the original condition")
    for record in snapshot.get("evidence_records", []):
        records[record["key"]] = record
    previous_closed = previous.get("known_closed_original_checks", [])
    previous_gates = previous.get("known_accepted_original_gates", [])
    previous_closed = set(previous_closed) if isinstance(previous_closed, list) and all(isinstance(x, str) for x in previous_closed) else set()
    previous_gates = set(previous_gates) if isinstance(previous_gates, list) and all(isinstance(x, str) for x in previous_gates) else set()
    current_closed, current_gates = set(snapshot["closed_original_checks"]), set(snapshot.get("accepted_original_gates", []))
    known_closed, known_gates = previous_closed | current_closed, previous_gates | current_gates
    # Do not credit the initial 111/156 (or any baseline) as new closures.
    # Retain only observed canonical 0->100 transitions, keyed by original ID.
    velocity_start = _epoch(previous.get("velocity_started_at", now))
    clock_rollback = now < velocity_start
    closure_events = {}
    for event in previous.get("verified_closure_events", []):
        if not isinstance(event, dict) or event.get("original_check") not in current_closed:
            continue
        try:
            observed_at = _epoch(event.get("observed_at"))
            if observed_at >= now - 4 * VELOCITY_WINDOW_SECONDS:
                closure_events.setdefault(event["original_check"], observed_at)
        except (ValueError, TypeError, OverflowError):
            continue
    if previous and "ledger_error" not in snapshot and not (previous_closed - current_closed):
        for ident in current_closed - previous_closed:
            closure_events.setdefault(ident, now)
    recent = sum(now - VELOCITY_WINDOW_SECONDS <= at <= now for at in closure_events.values())
    velocity_state = ("UNKNOWN" if "ledger_error" in snapshot or previous_closed - current_closed or clock_rollback
                      else "warming_up" if now - velocity_start < VELOCITY_WINDOW_SECONDS
                      else "below_target" if recent < VELOCITY_TARGET_LOW else "meeting_target")
    snapshot["closure_velocity"] = {
        "window_seconds": VELOCITY_WINDOW_SECONDS, "target_min": VELOCITY_TARGET_LOW,
        "target_max": VELOCITY_TARGET_HIGH, "new_verified_in_window": recent,
        "state": velocity_state, "baseline_started_at": _utc(velocity_start)}
    if previous_closed - current_closed or previous_gates - current_gates:
        snapshot["acceptance_regression"] = "UNKNOWN or regressed original closure; reconcile canonical evidence before claiming progress"
    progress_keys = {key for key, record in records.items() if record["semantic"]["kind"] == "required_evidence"
                     or record["semantic"].get("disposition") == "resolved"}
    old_progress = previous.get("earned_progress_keys", [])
    old_progress = set(old_progress) if isinstance(old_progress, list) and all(isinstance(x, str) and len(x) == 64 for x in old_progress) else set()
    earned_progress = old_progress | progress_keys
    semantic = {"closed_original_checks": sorted(known_closed),
                "accepted_original_gates": sorted(known_gates),
                "accepted_evidence_keys": sorted(records), "earned_progress_keys": sorted(earned_progress)}
    fingerprint = _digest(semantic)
    if "ledger_error" in snapshot and previous.get("semantic_fingerprint"):
        fingerprint = previous["semantic_fingerprint"]
    changed = bool(previous) and bool((current_closed - previous_closed) | (current_gates - previous_gates)
                                     | (progress_keys - old_progress)) and "ledger_error" not in snapshot
    last_semantic = now if not previous or changed else _epoch(previous.get("last_semantic_at", now))
    # Clock rollback is UNKNOWN timing, never negative progress or an immediate restart.
    last_semantic = min(last_semantic, now)
    last_checkpoint = _epoch(previous.get("last_checkpoint_at", now))
    checkpoint_due = not previous or now - last_checkpoint >= interval
    monitor = {"schema_version": 1, "semantic_fingerprint": fingerprint,
               "last_semantic_at": last_semantic, "last_checkpoint_at": now if checkpoint_due else last_checkpoint,
               "accepted_records": [records[key] for key in sorted(records)],
               "velocity_started_at": velocity_start,
               "verified_closure_events": [{"original_check": ident, "observed_at": _utc(at)}
                                           for ident, at in sorted(closure_events.items())],
               "known_closed_original_checks": sorted(known_closed), "known_accepted_original_gates": sorted(known_gates),
               "earned_progress_keys": sorted(earned_progress),
               "last_review_key": previous.get("last_review_key"),
               "last_review_at": previous.get("last_review_at"),
               "issued_review_keys": previous.get("issued_review_keys", {}),
               "operation_deadlines": protections,
               "accepted_review_times": previous.get("accepted_review_times", {}),
               "review_required": False, "decision_pending_seconds": 0}
    issued = monitor["issued_review_keys"]
    if not isinstance(issued, dict) or len(issued) > 4096:
        issued = {}
    issued = {key: value for key, value in issued.items()
              if isinstance(key, str) and type(value) in (int, float) and math.isfinite(value)}
    monitor["issued_review_keys"] = issued
    accepted_times = monitor["accepted_review_times"]
    accepted_times = ({key: value for key, value in accepted_times.items()
                      if key in issued and type(value) in (float, int) and math.isfinite(value)}
                     if isinstance(accepted_times, dict) else {})
    receipt = state.get("progress_review")
    if isinstance(receipt, dict) and receipt.get("status") == "accepted_by_server" and receipt.get("key") in issued:
        try:
            delivered = _epoch(receipt.get("delivered_at"))
            if issued[receipt["key"]] <= delivered <= now + 5:
                accepted_times.setdefault(receipt["key"], delivered)
        except (ValueError, TypeError, OverflowError):
            pass
    monitor["accepted_review_times"] = accepted_times
    reason, advisory_key = None, None
    failures = snapshot.get("ordinary_failures", [])
    healthy = snapshot["operation"].get("status") == "HEALTHY_BOUNDED_OPERATION"
    binding = snapshot.get("target_binding_sha256")
    if healthy:
        pass
    elif snapshot.get("remaining_count") == 0:
        if snapshot.get("unaccepted_original_gates") or not all(snapshot.get("milestone_acceptance", {}).values()):
            advisory_key = "original-acceptance-review-" + fingerprint
            reason = "All 156 counted checks are closed. Review the exact still-unaccepted original gates/milestones using complete matching evidence; do not invent another counted check."
    elif snapshot.get("unheld_target_status", snapshot.get("target_status")) == "CLOSED_IN_CANONICAL_LEDGER":
        advisory_key = "next-target-" + _digest({"target": binding, "semantic": fingerprint})
        reason = "The current original target is closed in the canonical ledger. Select the next eligible original check and submit its finite next action now."
    elif snapshot.get("target_error"):
        invalid = state.get("closure_target")
        advisory_key = "invalid-target-" + _digest({"error": snapshot["target_error"],
            "original_check": invalid.get("original_check") if isinstance(invalid, dict) else None})
        reason = "The finite target was rejected: " + snapshot["target_error"] + ". Correct the exact target through the checked CLI now."
    elif snapshot.get("unheld_target_status", snapshot.get("target_status")) == "INPUT_RESOLUTION_REQUIRED":
        advisory_key = "input-resolution-" + _digest({"target": binding,
            "resolution_keys": sorted(record["key"] for record in snapshot.get("evidence_records", [])
                if record["semantic"]["kind"] == "blocker_disposition"
                and record["semantic"].get("resolution_classification") == "engineering")})
        reason = ("Resolve this missing engineering input through a finite admitted engineering action now. "
                  "An unsupported or failed attempt does not establish a terminal external blocker. "
                  + snapshot.get("input_resolution_error", ""))
    elif snapshot.get("unheld_target_status", snapshot.get("target_status")) == "BLOCKED_BY_MATCHING_RECEIPT":
        blockers = sorted(record["key"] for record in snapshot["evidence_records"]
                          if record["semantic"]["kind"] == "blocker_disposition"
                          and record["semantic"]["disposition"] == "blocked")
        advisory_key = "blocked-target-" + _digest({"target": binding, "blockers": blockers})
        reason = "A matching receipt precisely blocks this original target. Record its exact missing input and supplying owner, then select another genuinely eligible original check; dependency order grants no execution."
    elif failures:
        advisory_key = "ordinary-failure-" + _digest({"target": binding,
            "failures": sorted(record["key"] for record in failures)})
        reason = "A concrete matching ordinary operation failed; make one bounded repair decision now."
    elif snapshot.get("target_status") == "NEEDS_TARGET":
        advisory_key = "needs-target-" + fingerprint
        reason = "The unattended run has no finite original-check closure target."
    elif snapshot.get("closure_velocity", {}).get("state") == "below_target":
        advisory_key = "closure-velocity-" + _digest({"priority": snapshot.get("priority_milestone"),
            "semantic": fingerprint})
        reason = ("The rolling 30-minute window has fewer than one newly verified original-check "
                  "closure. Assign finite independent fixes to all eligible existing child owners "
                  "within the earliest unfinished milestone; the 1-5 closure target does not grant "
                  "resource admission or relax any original acceptance.")
    elif now - last_semantic >= stall:
        advisory_key = "closure-stall-" + _digest({"target": binding, "semantic": fingerprint})
        reason = f"No original closure or new qualified matching evidence for {int(now - last_semantic)} seconds."
    text = None
    applicable_key = advisory_key
    monitor["decision_status"] = "no_review_due"
    if advisory_key is not None:
        monitor["review_required"] = True
        monitor["decision_status"] = "review_required"
        initial_key = advisory_key
        if advisory_key in accepted_times and now - accepted_times[initial_key] >= stall:
            advisory_key = "decision-overdue-" + _digest(initial_key)
            applicable_key = advisory_key
            monitor["decision_status"] = "owner_action_required"
            reason = ("The prior harness review was accepted by the server but has no completed original-check decision or qualified result. "
                      "This is the one bounded followup: the existing owner must record a finite action or precise block now. " + reason)
        if advisory_key not in issued:
            monitor.update(last_review_key=advisory_key, last_review_at=now)
            issued[advisory_key] = now
            text = _advisory(snapshot, reason)
        else:
            advisory_key = None
        monitor["decision_pending_seconds"] = max(0, now - accepted_times.get(initial_key, issued[initial_key]))
    snapshot.update(semantic_fingerprint=fingerprint, semantic_progress_changed=changed,
                    seconds_since_semantic_progress=max(0, now - last_semantic),
                    review_required=monitor["review_required"], decision_pending_seconds=monitor["decision_pending_seconds"],
                    decision_status=monitor["decision_status"])
    return {"snapshot": snapshot, "monitor": monitor, "checkpoint_due": checkpoint_due,
            "advisory_key": advisory_key, "advisory_text": text, "applicable_advisory_key": applicable_key}
