"""Bounded workstation preflight for the existing overnight launcher.

This checks dependencies and briefly probes inhibition. It does not install units,
enable lingering, authorize a start, poll instructions, or call a model.
"""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

from os_goal_guard_protocol import lease_free, read_json
from os_goal_readiness import evaluate_readiness
from os_goal_stop_log import _text as redact


def _configuration(repo):
    from os_goal_service import _validated_arguments
    from run_os_goal import arguments
    values = _validated_arguments(repo, None)
    args = arguments(values)
    mailbox = read_json(Path(repo) / "scripts/os_goal_mailbox.json")
    if (args.hours != 0 or args.max_restarts != -1 or not args.repair_agent_failures
            or not args.stop_after_m14_m15 or args.max_agents != 2
            or args.build_jobs != 3 or args.memory_gib != 4 or mailbox.get("poll_seconds") != 600):
        raise ValueError("The prepared overnight defaults differ from the reviewed M14/M15 run")
    return {"hours": args.hours, "max_restarts": args.max_restarts,
            "repair_agent_failures": args.repair_agent_failures,
            "stop_after_m14_m15": args.stop_after_m14_m15,
            "max_agents": args.max_agents, "build_jobs": args.build_jobs,
            "memory_gib_total": args.memory_gib, "host_cpus": [0, 6, 7],
            "mailbox_poll_seconds": 600, "status_refresh_seconds": 600,
            "codex_executable": args.codex}


def _binaries(config):
    required = ("git", "gh", "systemctl", "loginctl", "systemd-inhibit", "taskset", config["codex_executable"])
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise RuntimeError("Missing workstation executables: " + ", ".join(missing))
    return {"required_executables_available": True}


def _manager():
    from os_goal_service import _systemctl
    version = _systemctl("show", "--property=Version", "--value", timeout=10)
    if not version:
        raise RuntimeError("User service manager did not return its version")
    return {"user_manager_reachable": True}


def _owners(directory):
    from os_goal_service import _legacy_owner
    blocked = [name for name in ("watch.lock", "run.lock", "guardian-service.lock")
               if not lease_free(directory, name)]
    legacy = _legacy_owner(directory)
    if blocked or legacy:
        raise RuntimeError(legacy or "Existing model or launch ownership must checkpoint before a new start")
    return {"model_and_submission_leases_free": True, "legacy_launch_reconciled": True}


def _resources(repo, config):
    from os_goal_resources import check_resources, resolve_resources
    snapshot = resolve_resources("aggressive", config["max_agents"], config["build_jobs"],
                                 config["memory_gib_total"], repo)
    check_resources(snapshot)
    if snapshot["available_memory_gib"] < 26:
        raise RuntimeError("The campaign requires fresh 26 GiB available memory, preserving 18 GiB reservations and a 4 GiB host floor")
    affinity = snapshot.get("cpu_affinity")
    if not isinstance(affinity, list) or not {0, 6, 7}.issubset(affinity):
        raise RuntimeError("The current workstation affinity does not permit the granted HOST CPUs 0,6,7")
    return {"available_memory_gib": snapshot["available_memory_gib"],
            "memory_gib_total": config["memory_gib_total"], "host_cpus_available": [0, 6, 7],
            "host_disk": snapshot["host_disk"], "scratch_disk": snapshot["scratch_disk"],
            "operation_admission": "Remeasure before actual work; this observation is not a resource lease"}


def _public_status():
    from os_goal_mailbox import _gh_api
    from os_goal_status_publish import _GET, _remote_file
    body, sha = _remote_file(_gh_api(_GET, timeout=10))
    return {"existing_status_file_verified": True, "bytes": len(body), "blob_sha": sha,
            "write_access": "Unverified until the current guardian publishes matching status bytes"}


def prepare_overnight(repo, directory):
    """Report local preparation honestly; never claim that a runtime was started."""
    from os_goal_power import check_linger, probe_inhibition
    from os_goal_service import mailbox_preflight
    repo, directory = Path(repo), Path(directory)
    checks = {}
    def observe(name, operation):
        try:
            details = operation()
            checks[name] = {"status": "PASS", "details": details}
            return details
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            checks[name] = {"status": "BLOCKED", "reason": redact(str(error), 500),
                            "error_type": type(error).__name__}
            return None
    config = observe("configuration", lambda: _configuration(repo))
    if config is not None:
        observe("executables", lambda: _binaries(config))
        observe("resources", lambda: _resources(repo, config))
    observe("user_service_manager", _manager)
    linger = observe("logout_persistence", check_linger)
    if linger is not None and not linger["enabled"]:
        checks["logout_persistence"]["status"] = "SETUP_NEEDED"
        checks["logout_persistence"]["next_action"] = "The explicit start command enables lingering for this user and verifies it before installing units"
    observe("sleep_and_lid_inhibitor_permission", probe_inhibition)
    observe("existing_ownership", lambda: _owners(directory))
    access = observe("github_identity_and_mailbox", lambda: mailbox_preflight(repo))
    if access is not None:
        observe("github_status_file", _public_status)
    blocked = [name for name, value in checks.items() if value["status"] == "BLOCKED"]
    setup = [name for name, value in checks.items() if value["status"] == "SETUP_NEEDED"]
    return {"schema_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
            "status": "BLOCKED" if blocked else "SETUP_NEEDED" if setup else "PREPARED",
            "checks": checks, "blocked_checks": blocked, "setup_checks": setup,
            "model_calls": 0, "services_started": False,
            "monitoring": evaluate_readiness(directory),
            "next_action": "After required setup, use scripts/start_os_overnight.py start; verify monitoring_ready with status",
            "limits": "Preparation does not prove service-context GitHub write access, current included allowance, live monitoring or original M14/M15 acceptance. The actual engine retains its normal account/source/native/resource gates."}
