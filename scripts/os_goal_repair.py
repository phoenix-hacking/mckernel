"""Same-Root repair guidance and bounded BLOCKED review context, without I/O.

Eligibility here permits one diagnostic instruction only. It never proves that a
blocked task is ordinary engineering, admits execution, releases a hold, clears a
goal, invokes an agent, or authorizes launcher/model recovery.
"""
import hashlib
import json


_GLOBAL_HOLDS = ("service_hold", "policy_hold", "auth_hold", "billing_hold", "budget_hold",
                 "permission_hold", "account_hold", "accounting_unknown", "budget_unknown",
                 "auth_unknown", "credit_budget_unknown", "included_usage_unknown",
                 "user_pause", "user_paused", "pause_requested")
_LANE_HOLDS = ("native_hold", "resource_hold", "source_hold", "operation_hold")
_HOLDS = _GLOBAL_HOLDS + _LANE_HOLDS
_VOLATILE_GOAL_FIELDS = frozenset({
    "createdAt", "updatedAt", "created_at", "updated_at", "tokensUsed",
    "tokens_used", "tokenUsage", "token_usage", "elapsedSeconds", "elapsed_seconds",
    "timeUsedSeconds", "time_used_seconds",
})


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _held(state, key):
    # An explicit unknown/malformed flag is not an affirmative clear flag.
    return key in state and state[key] is not False


def _historical_error(state):
    """Only positively different invocation identities establish historical data."""
    error = state.get("last_error")
    if error is None:
        return True
    provenance = state.get("last_error_provenance")
    if (not isinstance(provenance, dict) or provenance.get("error") != error
            or not _text(provenance.get("log_dir")) or not _text(state.get("log_dir"))):
        return False
    if provenance["log_dir"] != state["log_dir"]:
        return True
    return any(state.get(key) is not None and provenance.get(key) is not None
               and state[key] != provenance[key] for key in ("worker_pid", "worker_start"))


def blocked_task_slot_available(blocker):
    """A parked terminal model turn frees a logical slot, never its OS charges."""
    return (isinstance(blocker, dict) and _text(blocker.get("task_id"))
            and blocker.get("parked") is True
            and isinstance(blocker.get("turn_status"), str)
            and blocker.get("turn_status") in {"completed", "failed", "interrupted"}
            and blocker.get("runtime_resources_retained") is True)


def _isolated_context(state, held_lanes):
    """Validate caller-registered read-only isolation; never discover clearance.

    ``repair_context`` is harness-owned metadata, supplied only after the caller
    has registered and validated the current input/receipt revisions. A model's
    error string, inferred scope or readiness claim is not registration. Unknown
    scope, missing rows and any global hold remain closed.
    """
    context = state.get("repair_context")
    if context is None:
        return None
    try:
        if (not isinstance(context, dict) or type(context["schema_version"]) is not int
                or context["schema_version"] != 1
                or context["thread_id"] != state["thread_id"]
                or context["account_gate_clear"] is not True
                or context["source_overhead_accounted"] is not True):
            return None
        blocker, task = context["blocker"], context["task"]
        if not isinstance(blocker, dict) or not isinstance(task, dict):
            return None
        fields = blocker["hold_fields"]
        if (blocker["scope"] != "task" or not blocked_task_slot_available(blocker)
                or not isinstance(fields, list) or not fields
                or any(field not in _LANE_HOLDS for field in fields)
                or len(set(fields)) != len(fields) or set(fields) != held_lanes
                or not _text(task["task_id"]) or task["task_id"] == blocker["task_id"]
                or task["kind"] not in {"source", "test_preparation", "read_only_review"}
                or task["isolated_from_blocker"] is not True
                or task["requires_execution"] is not False):
            return None
        rows = context["registered_inputs"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
            return None
        inputs, identifiers = [], set()
        for row in rows:
            if not isinstance(row, dict):
                return None
            ident, digest = row["id"], row["sha256"]
            if (not _text(ident) or len(ident) > 256 or ident in identifiers
                    or not isinstance(digest, str) or len(digest) != 64
                    or any(char not in "0123456789abcdef" for char in digest)
                    or row["kind"] not in {"source", "input", "receipt", "review"}
                    or row["status"] != "registered" or row["current"] is not True
                    or row["thread_id"] != state["thread_id"]):
                return None
            identifiers.add(ident)
            inputs.append({"id": ident, "kind": row["kind"], "sha256": digest})
        return {"blocker_task_id": blocker["task_id"], "hold_fields": sorted(fields),
                "task_id": task["task_id"], "task_kind": task["kind"],
                "registered_inputs": sorted(inputs, key=lambda row: row["id"])}
    except (KeyError, TypeError, ValueError, RecursionError):
        return None


def blocked_repair_key(goal, state):
    """Return a stable key for one safe same-Root diagnosis, otherwise None.

    The caller durably remembers submitted keys and never reissues an unchanged
    blocked review merely because that review itself finished. Unknown failures
    remain closed; a raw string or a retryable flag cannot establish eligibility.
    Resource/source holds encoded in the plan still bind the Root's diagnosis;
    they may not be inferred clear from this guard or from available quota.
    """
    if not isinstance(goal, dict) or not isinstance(state, dict):
        return None
    if (goal.get("status") != "blocked" or not _text(goal.get("objective"))
            or not _text(state.get("thread_id"))
            or goal.get("threadId", state["thread_id"]) != state["thread_id"]):
        return None
    held_lanes = {key for key in _LANE_HOLDS if _held(state, key)}
    context = _isolated_context(state, held_lanes)
    if held_lanes and context is None:
        return None
    if state.get("repair_context") is not None and context is None:
        return None
    allowed_stops = {None, "goal_blocked", "engineering_failure"}
    if context is not None:
        allowed_stops.update(_LANE_HOLDS)
    stop = state.get("stop_reason")
    if stop is not None and not isinstance(stop, str):
        return None
    if (stop not in allowed_stops
            or any(_held(state, key) for key in _GLOBAL_HOLDS)
            or state.get("transport_uncertain") or state.get("pending_request")
            or state.get("stop_now") or state.get("checkpoint_requested")
            or state.get("credit_budget_error") is not None
            or not _historical_error(state)):
        return None
    # Unknown activity is not evidence that a diagnostic turn can safely start.
    active = state.get("active_turns")
    if not isinstance(active, dict) or active:
        return None
    for key in ("last_instruction", "resume_instruction"):
        receipt = state.get(key)
        if receipt is not None and (not isinstance(receipt, dict) or receipt.get("status")
                                   not in {"accepted_by_server", "delivered", "completed"}):
            return None
    data = {"thread_id": state["thread_id"],
            "goal": {key: value for key, value in goal.items() if key not in _VOLATILE_GOAL_FIELDS}}
    if context is not None:
        data["isolated_read_only_work"] = context
    try:
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError, RecursionError):
        return None
    if len(encoded) > 65536:
        return None
    return hashlib.sha256(encoded).hexdigest()


def repair_instruction():
    """Prompt addition for an opted-in run; ordinary Root routing remains intact."""
    return (
        "Ordinary engineering repair is enabled within this same Root. Log why "
        "progress stops: preserve the actual failed command/check and diagnostic, "
        "affected source/input, owner, blocker and next action in existing raw evidence "
        "and CAMPAIGN.md. For an established compiler/build/test/CI defect or "
        "source-fetch transport defect on already authorized ordinary source, give "
        "the smallest concrete fix to an existing same-Root Sol/MAX owner "
        "using followup_task, and use a separate independent owner for focused tests "
        "and review. Every new worker, auditor and reviewer turn uses explicit "
        "Sol/MAX. Reuse completed HIGH evidence without restarting healthy work. "
        "Respect the existing child cap, one compositor and shared "
        "resource grant; use ready disjoint work. Root integrates a reviewed fix and "
        "retries the necessary failed check only after meaningful relevant input "
        "changes and actual operation-specific admission. Retain one failed candidate "
        "and one bounded correction per failure family, then focused escalation "
        "may assign another repair owner and retry only after meaningful changed "
        "input; ordinary engineering failure alone is not a terminal stop. Do not "
        "repeat an unchanged failure or an already passing suite. Keep "
        "independent ready eligible M14/M15 preparation active when one lane blocks, "
        "retaining M14-before-M15 acceptance. Scope a source/operation block to its "
        "actual affected task only when positive registered current evidence proves "
        "independent read-only source/test preparation is isolated from it. Retain "
        "every UNKNOWN charge and exclusive scope; this routing grants no payload "
        "execution or hold release. Park the blocked task and stop issuing work "
        "on it. Once its model turn is terminal, release its logical agent slot; "
        "unjoined processes and UNKNOWN RAM/job/lease charges remain quarantined "
        "and accounted until their own genuine closure. No cancellation or signal "
        "is implied. Unknown/unscoped isolation remains held. "
        "Source custody/eligibility, permissions, "
        "credentials, native/resource ownership, UNKNOWN outcomes and actual "
        "service/account/budget holds remain binding. A service/external hold or "
        "unknown error is not a software repair. Never retry a policy/cyberPolicy "
        "or permission-rejected request through another agent, model, tool, "
        "equivalent task or fresh session. Continue useful work through original "
        "M14/M15 closure without an arbitrary time cap, preserving acceptance order. "
        "Continuous operation never overrides completion, a user stop, the included usage limit or "
        "another genuine binding hold. When no eligible work remains, checkpoint "
        "the precise blocker, owner, missing input and next trigger and use normal "
        "BLOCKED; do not busy-loop or consume quota artificially."
    )


def blocked_repair_instruction(goal, state):
    """Build one bounded diagnostic turn, never a forced active-goal transition."""
    key = blocked_repair_key(goal, state)
    if key is None:
        return None
    context = _isolated_context(state, {field for field in _LANE_HOLDS if _held(state, field)})
    isolated = (" Registered isolated read-only task " + context["task_id"] +
                " is separate from retained blocker " + context["blocker_task_id"] +
                "; consider only those registered current inputs. " if context is not None else " ")
    return (
        "One same-Root diagnostic review of blocked transition " + key + "." + isolated +
        "The saved goal remains BLOCKED. Inspect the actual stop reason and current "
        "CAMPAIGN.md; blocked status alone does not prove an ordinary software defect "
        "or authorize replay of the blocked task. Determine whether actual new "
        "eligible ordinary engineering work or independent ready work exists. "
        + repair_instruction() + " "
        "If eligible work exists, use the normal goal/agent tools under their actual "
        "gates. Otherwise retain BLOCKED and record the precise blocker and required "
        "changed input once. No forced goal/set active, hidden restart, repeated "
        "identical diagnostic, hold release, broad audit or unchanged replay is "
        "authorized. A waiting supervisor may monitor for queued user instructions "
        "and real changes without dispatching work or inventing progress."
    )
