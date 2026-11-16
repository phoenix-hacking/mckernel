"""Local user STOP for the existing functional OS/Rust campaign controller.

No account reads, new RPC client, process signals, runtime cleanup or hold release.
The existing controller consumes the request using its original owning channel.
"""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import subprocess
import time

from os_goal_guard_protocol import atomic_json, process_start, read_json
from os_goal_service import runtime_directory


REQUEST = "user-stop.json"
SUPERVISION_TIMER = "mckernel-m14-window-supervision-20261106.timer"
IDENTITY = ("worker_pid", "worker_start", "server_pid", "server_start", "thread_id", "log_dir")


def _boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def _read(path):
    try:
        return read_json(path)
    except FileNotFoundError:
        return {}


def _owner(state):
    owner = {key: state.get(key) for key in IDENTITY}
    for name in ("worker", "server"):
        if (type(owner[name + "_pid"]) is not int or owner[name + "_pid"] <= 0
                or not isinstance(owner[name + "_start"], str) or not owner[name + "_start"].isdigit()):
            raise ValueError("Current " + name + " birth identity is unavailable")
    if any(not isinstance(owner[key], str) or not owner[key] for key in ("thread_id", "log_dir")):
        raise ValueError("Current campaign thread/invocation identity is unavailable")
    owner["repo"] = str(Path(state["repo"]).resolve())
    return owner


def _resumed(request, owner, state):
    # A successful explicit resume permanently supersedes that exact old STOP.
    # Later error/stop flags still halt dispatch, but must not resurrect the old
    # request or replace their actual cause. A new user STOP gets a fresh ID.
    if request.get("status") != "consumed" or request.get("errors") != [] or not request.get("id"):
        return False
    receipts = [state.get("last_instruction")]
    acknowledged = state.get("acknowledged_user_stop") or {}
    if acknowledged.get("request_id") == request["id"]:
        receipts.append(acknowledged.get("resume"))
    for receipt in receipts:
        if not isinstance(receipt, dict):
            continue
        resumed_owner = receipt.get("owner") or {}
        if (receipt.get("user_stop_request_id") == request["id"]
                and receipt.get("status") == "accepted_by_server" and receipt.get("control_kind") == "resume_same_owner"
                and all(resumed_owner.get(key) == value for key, value in owner.items())):
            return True
    return False


@contextmanager
def _locked(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "user-stop.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def _timer_stop():
    try:
        result = subprocess.run(["systemctl", "--user", "is-active", SUPERVISION_TIMER],
                                capture_output=True, text=True, timeout=5, check=False)
        observed = result.stdout.strip()
        if result.returncode == 0 and observed == "active":
            stopped = subprocess.run(["systemctl", "--user", "stop", SUPERVISION_TIMER],
                                     capture_output=True, text=True, timeout=10, check=False)
            return "stop_requested" if stopped.returncode == 0 else "stop_failed"
        return observed if observed in {"inactive", "failed", "unknown"} else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _status(repo, directory):
    state, request = _read(directory / "state.json"), _read(directory / REQUEST)
    try:
        owner = _owner(state)
    except (ValueError, KeyError, TypeError) as error:
        owner, identity_error = None, str(error)
    else:
        identity_error = None
    matching = bool(owner and request.get("owner") == owner and request.get("boot_id") == _boot_id())
    return {"state_directory": str(directory), "owner": owner, "identity_error": identity_error,
            "worker_birth_observation": process_start(state.get("worker_pid")),
            "server_birth_observation": process_start(state.get("server_pid")),
            "controller_dispatch_enabled": state.get("controller_dispatch_enabled"),
            "stop_reason": state.get("stop_reason"), "stop_now": state.get("stop_now"),
            "active_turns": state.get("active_turns"), "goal": state.get("goal"),
            "turn_observation": "saved state; interruption is not runtime cleanup or quiescence proof",
            "stop_request": request if matching else None,
            "stop_request_matches_owner": matching, "stale_stop_request": bool(request and not matching)}


def status(repo):
    """Report observed state honestly; absent processes never release charges."""
    return _status(repo, Path(runtime_directory(repo)))


def request_stop(repo):
    """Persist a user stop for this exact saved owner, without an RPC connection."""
    repo, directory = Path(repo).resolve(), Path(runtime_directory(repo))
    with _locked(directory):
        state = _read(directory / "state.json")
        owner = _owner(state)
        if owner["repo"] != str(repo):
            raise ValueError("Saved campaign belongs to a different repository")
        boot_id = _boot_id()
        path = directory / REQUEST
        request = _read(path)
        if (request.get("owner") != owner or request.get("boot_id") != boot_id
                or _resumed(request, owner, state)):
            requested = time.time_ns()
            request = {"schema_version": 1, "id": str(requested), "owner": owner, "boot_id": boot_id,
                       "reason": "user_stop", "requested_at_ns": requested,
                       "status": "pending", "pause_attempted": False, "interrupts": [], "errors": []}
            atomic_json(path, request)
    result = _status(repo, directory)
    result["supervision_timer"] = _timer_stop()
    return result


def consume_stop(campaign):
    """Latch and consume matching STOP on the SAME Campaign/RPC, even if retained.

    Return True for this owner's stop (including an already consumed one), False
    for no request or a different owner. Attempts are durable before submission;
    uncertain delivery is reported and never automatically replayed.
    """
    directory = Path(campaign.directory)
    if not (directory / REQUEST).exists():
        return False
    with _locked(directory):
        path = directory / REQUEST
        request = _read(path)
        try:
            owner = _owner(campaign.state)
        except (ValueError, KeyError, TypeError):
            return False
        if (request.get("schema_version") != 1 or request.get("reason") != "user_stop"
                or request.get("owner") != owner
                or request.get("boot_id") != _boot_id()
                or owner["worker_pid"] != os.getpid()
                or owner["repo"] != str(Path(campaign.repo).resolve())
                or owner["log_dir"] != str(campaign.log_dir)
                or owner["server_pid"] != getattr(getattr(campaign.rpc, "proc", None), "pid", None)):
            return False
        if _resumed(request, owner, dict(campaign.state, stop_reason=campaign.stop_reason, stop_now=campaign.stop_now)):
            return False
        births = [process_start(owner[name + "_pid"]) for name in ("worker", "server")]
        if births[0] not in {"unknown", owner["worker_start"]}:
            return False
        campaign.stop_reason, campaign.stop_now = "user_stop", True
        campaign.checkpoint_requested, campaign.stopping = False, True
        if hasattr(campaign, "args"):
            campaign.args.retain_owner_on_stop = True
        if campaign.rpc is not None:
            campaign.rpc.owner_custody_retained = True
        campaign.state.update(stop_reason="user_stop", stop_now=True, checkpoint_requested=False,
                              controller_dispatch_enabled=False)
        if request.get("status") != "pending":
            if request.get("status") == "consuming":
                request["status"] = "uncertain"
                request["errors"].append("Previous stop attempt did not finish; no mutating RPC is replayed")
                atomic_json(path, request)
                campaign.state["user_stop"] = request
            campaign.save()
            return True
        errors = request["errors"]
        request["status"] = "consuming"
        atomic_json(path, request)
        try:
            campaign.save()
        except Exception as error:
            errors.append("stop state publication: " + str(error))
        unavailable = (campaign.state.get("transport_failure") or {}).get("channel_unusable") is True
        if ("unknown" in births or births[1] != owner["server_start"]
                or not campaign.controlled or not campaign.rpc or unavailable):
            errors.append("Owner/control/channel uncertain; dispatch is off, pause and interrupts unconfirmed")
        else:
            request["pause_attempted"] = True
            atomic_json(path, request)
            try:
                campaign.pause()
                if campaign.controlled and (campaign.goal or {}).get("status") == "blocked":
                    campaign.goal = campaign.rpc.call("thread/goal/set", {
                        "threadId": owner["thread_id"], "status": "paused"}, timeout=10)["goal"]
                    campaign.save(goal=campaign.goal)
                request["goal_status"] = (campaign.goal or {}).get("status")
            except Exception as error:
                errors.append("pause: " + str(error))
            active = dict(campaign.active)
            if campaign.controlled:
                try:
                    cursor = None
                    while True:
                        params = {} if cursor is None else {"cursor": cursor}
                        loaded = campaign.rpc.call("thread/loaded/list", params, timeout=10)
                        for ident in loaded["data"]:
                            turns = campaign.rpc.call("thread/turns/list", {
                                "threadId": ident, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"}, timeout=10)
                            for turn in turns["data"]:
                                if turn["status"] == "inProgress":
                                    active[ident] = turn["id"]
                        following = loaded.get("nextCursor")
                        if not following:
                            break
                        if following == cursor:
                            raise ValueError("Loaded-thread cursor did not advance")
                        cursor = following
                except Exception as error:
                    errors.append("loaded/current turn discovery: " + str(error))
                for ident, turn in active.items():
                    attempt = {"thread_id": ident, "turn_id": turn, "status": "delivery_uncertain"}
                    request["interrupts"].append(attempt)
                    atomic_json(path, request)
                    try:
                        campaign.rpc.call("turn/interrupt", {"threadId": ident, "turnId": turn}, timeout=10)
                        attempt["status"] = "accepted"
                    except Exception as error:
                        errors.append("interrupt " + ident + ": " + str(error))
                    atomic_json(path, request)
            else:
                errors.append("Goal ownership changed; no loaded-thread interruption attempted")
        request["status"] = "uncertain" if errors else "consumed"
        atomic_json(path, request)
        campaign.stop_reason, campaign.stop_now = "user_stop", True
        campaign.save(user_stop=request, controller_dispatch_enabled=False,
                      stop_reason="user_stop", stop_now=True, cleanup_verified=False)
        return True
