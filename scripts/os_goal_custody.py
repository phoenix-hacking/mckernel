"""Conservative owner retention for the functional OS/Rust harness.

This module performs no I/O and grants no operation, resume or release authority.
Completed turns, tool output and missing progress records cannot establish that
the original runtime has joined every child or closed its retained handles.
"""

from pathlib import PurePath


RETAINED_PHASE = "owner_retained"
RETENTION_SCHEMA = 1
IDENTITY_FIELDS = ("worker_pid", "worker_start", "server_pid", "server_start",
                   "thread_id", "log_dir")


class OwnerCustodyRetained(RuntimeError):
    """Closing the owner would discard unresolved original runtime custody."""


def retention_enabled(args):
    return (getattr(args, "retain_owner_on_stop", False) is True
            or getattr(args, "continuous", False) is True)


def retention_required(args, rpc):
    """Retain even a bare/preflight server; no operation metadata proves release."""
    return retention_enabled(args) and rpc is not None


def guard_owner_close(retained):
    """Call before stdin.close, wait, terminate or any other shutdown effect."""
    if retained:
        raise OwnerCustodyRetained("Original owner custody is UNKNOWN; server retained")


def retention_error(stage, error):
    """A diagnostic never turns an unconfirmed pause/pump/save into closure."""
    return {"stage": stage, "error_type": type(error).__name__, "error": str(error)}


def make_retention_record(state, *, watcher_pid=None, watcher_start=None,
                          reason=None, errors=()):
    """Describe this exact invocation without changing its holds or ledgers.

    Bind watcher_pid/start to the actual parent when one supervises this worker.
    Missing identities remain UNKNOWN and cannot authenticate a watcher receipt;
    the in-memory close guard must remain set even when publication fails.
    """
    row = {key: state.get(key) for key in IDENTITY_FIELDS}
    row.update(schema_version=RETENTION_SCHEMA, phase=RETAINED_PHASE,
               invocation=state.get("log_dir"), watcher_pid=watcher_pid,
               watcher_start=watcher_start, stop_reason=reason,
               custody="UNKNOWN", release_authorized=False,
               automatic_resume=False, controller_dispatch_enabled=False,
               inflight_turn_quiescence="unverified", operator_required=True,
               errors=[dict(error) for error in errors])
    return row


def _pid(value):
    return type(value) is int and value > 0


def _birth(value):
    return isinstance(value, str) and bool(value) and value.isascii() and value.isdigit()


def current_owner_identity(state, *, worker_pid, worker_start):
    """Return only a complete current-worker server identity, without probing it."""
    if (not isinstance(state, dict) or not _pid(worker_pid) or not _birth(worker_start)
            or state.get("worker_pid") != worker_pid
            or state.get("worker_start") != worker_start
            or not _pid(state.get("server_pid")) or not _birth(state.get("server_start"))
            or not isinstance(state.get("log_dir"), str)
            or not PurePath(state["log_dir"]).is_absolute()):
        return None
    return {key: state.get(key) for key in IDENTITY_FIELDS}


def retention_matches(state, *, worker_pid, worker_start, watcher_pid, watcher_start):
    """Validate a retained receipt against this watcher's exact current child.

    Callers supply their in-memory child identity and their own watcher identity;
    neither may be imported from the saved receipt being checked. No freshness
    timeout releases custody: a stale heartbeat still needs the original owner.
    """
    identity = current_owner_identity(state, worker_pid=worker_pid, worker_start=worker_start)
    if identity is None or not _pid(watcher_pid) or not _birth(watcher_start):
        return False
    row = state.get("owner_retention")
    if not isinstance(row, dict):
        return False
    return (state.get("phase") == RETAINED_PHASE
            and type(row.get("schema_version")) is int
            and row["schema_version"] == RETENTION_SCHEMA
            and row.get("phase") == RETAINED_PHASE
            and all(row.get(key) == value for key, value in identity.items())
            and row.get("invocation") == identity["log_dir"]
            and type(row.get("watcher_pid")) is int and row["watcher_pid"] == watcher_pid
            and row.get("watcher_start") == watcher_start
            and row.get("custody") == "UNKNOWN"
            and row.get("release_authorized") is False
            and row.get("automatic_resume") is False
            and row.get("controller_dispatch_enabled") is False
            and row.get("inflight_turn_quiescence") == "unverified"
            and row.get("operator_required") is True)
