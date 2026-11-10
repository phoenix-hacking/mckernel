"""Same-Root repair guidance and bounded BLOCKED review context, without I/O.

Eligibility here permits one diagnostic instruction only. It never proves that a
blocked task is ordinary engineering, admits execution, releases a hold, clears a
goal, invokes an agent, or authorizes launcher/model recovery.
"""
import hashlib
import json


_HOLDS = ("service_hold", "policy_hold", "auth_hold", "billing_hold", "budget_hold",
          "permission_hold", "native_hold", "resource_hold", "source_hold")
_VOLATILE_GOAL_FIELDS = frozenset({
    "createdAt", "updatedAt", "created_at", "updated_at", "tokensUsed",
    "tokens_used", "tokenUsage", "token_usage", "elapsedSeconds", "elapsed_seconds",
    "timeUsedSeconds", "time_used_seconds",
})


def _text(value):
    return isinstance(value, str) and bool(value.strip())


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
    if (state.get("stop_reason") not in (None, "goal_blocked", "engineering_failure")
            or any(state.get(key) for key in _HOLDS)
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
        "the smallest concrete fix to an existing same-Root Sol/HIGH-or-higher owner "
        "using followup_task, and use a separate independent owner for focused tests "
        "and review. Respect the existing child cap, one compositor and shared "
        "resource grant; use ready disjoint work. Root integrates a reviewed fix and "
        "retries the necessary failed check only after meaningful relevant input "
        "changes and actual operation-specific admission. Retain one failed candidate "
        "and one bounded correction per failure family, then focused escalation "
        "may assign another repair owner and retry only after meaningful changed "
        "input; ordinary engineering failure alone is not a terminal stop. Do not "
        "repeat an unchanged failure or an already passing suite. Keep "
        "independent ready eligible M14/M15 preparation active when one lane blocks, "
        "retaining M14-before-M15 acceptance. Source custody/eligibility, permissions, "
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
    return (
        "One same-Root diagnostic review of blocked transition " + key + ". "
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
