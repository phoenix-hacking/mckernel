#!/usr/bin/env python3
"""User-service adapter: systemd watches the guardian, which watches the engine.

The two services have separate cgroups. Restarting this monitor never implicitly
starts a model, and an engine recovery must carry the guardian's exact proof.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from uuid import uuid4

from os_goal_guard_protocol import EngineLaunchDeferred, atomic_json, lease_free, process_start, read_json


REPO = Path(__file__).resolve().parents[1]
CONFIG = "guardian-engine-config.json"
NEXT = "guardian-engine-launch.json"


def runtime_directory(repo):
    path = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
                                   text=True, timeout=5).strip()
    return (Path(repo) / path).resolve() / "os-autopilot"


def unit_names(directory):
    suffix = hashlib.sha256(str(Path(directory).resolve()).encode()).hexdigest()[:12]
    return {"guardian": "mckernel-guardian-" + suffix + ".service",
            "engine": "mckernel-engine-" + suffix + ".service"}


def _quote(value, *, expand_dollars=True):
    value = str(value)
    if any(c in value for c in ("\0", "\r", "\n")):
        raise ValueError("Newlines and NUL are not valid service arguments")
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return '"' + (value.replace("$", "$$") if expand_dollars else value) + '"'


def render_units(repo, directory, *, python=None, path_environment=None):
    repo, directory = Path(repo).resolve(), Path(directory).resolve()
    executable = python or sys.executable
    environment = path_environment if path_environment is not None else os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
    command = " ".join(_quote(v) for v in (executable, "-B", repo / "scripts/os_goal_service.py"))
    inhibit = shutil.which("systemd-inhibit")
    if not inhibit or not Path(inhibit).is_absolute():
        raise RuntimeError("The guardian requires an absolute systemd-inhibit executable; no uninhibited fallback")
    # The guardian keeps idle, suspend and lid handling inhibited while its
    # separate engine is held/stopped. No power-off or shutdown inhibitor is taken.
    # The long-lived Python child sends READY/WATCHDOG, so NotifyAccess=all lets
    # systemd accept its notifications within the inhibitor wrapper's cgroup.
    guardian_command = " ".join(_quote(v) for v in (
        inhibit, "--what=idle:sleep:handle-lid-switch", "--mode=block", "--who=McKernel guardian",
        "--why=Keep overnight monitoring and the phone mailbox awake", "--")) + " " + command
    # WorkingDirectory is a single path, not an ExecStart-style quoted word.
    # Literal quotes would become part of the path and fail systemd validation.
    path = str(repo)
    if any(c in path for c in ("\0", "\r", "\n")) or path != path.strip():
        raise ValueError("Invalid service working directory")
    shared = ("WorkingDirectory=" + path.replace("%", "%%") + "\nUMask=0077\n"
              "Environment=" + _quote("PATH=" + environment, expand_dollars=False) + "\n"
              "Environment=PYTHONUNBUFFERED=1\nStandardOutput=journal\nStandardError=journal\n")
    names = unit_names(directory)
    guardian = ("[Unit]\nDescription=McKernel independent supervisor watchdog and mailbox\n"
                "After=network-online.target\nStartLimitIntervalSec=0\n\n[Service]\n"
                "Type=notify\nNotifyAccess=all\nWatchdogSec=90\nRestart=always\nRestartSec=5\n"
                "TimeoutStartSec=60\nTimeoutStopSec=700\nKillMode=control-group\n" + shared
                + "ExecStart=" + guardian_command + " guardian\n\n[Install]\nWantedBy=default.target\n")
    engine = ("[Unit]\nDescription=McKernel model supervisor (owned by the guardian)\n"
              "StartLimitIntervalSec=0\n\n[Service]\nType=exec\nRestart=no\n"
              "TimeoutStopSec=700\nKillMode=process\n" + shared
              + "ExecStart=" + command + " engine\n")
    return {names["guardian"]: guardian, names["engine"]: engine}


def _systemctl(*arguments, timeout=50):
    binary = shutil.which("systemctl")
    if binary is None:
        raise RuntimeError("The guarded launcher requires systemd user services")
    result = subprocess.run([binary, "--user", *arguments], stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError("systemd user operation failed: " + " ".join(arguments[:2])
                           + "; check the local user service manager/journal")
    return result.stdout.strip()


@contextmanager
def _service_lock(directory):
    """Serialize settings and OS-unit submission, including the pre-lease gap."""
    fd = os.open(Path(directory) / "guardian-service.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise EngineLaunchDeferred("Another service submission is still publishing") from error
        yield
    finally:
        os.close(fd)


def _engine_idle(directory):
    state = _systemctl("show", unit_names(directory)["engine"], "--property=ActiveState", "--value", timeout=10)
    if state not in {"active", "activating", "deactivating", "reloading", "inactive", "failed"}:
        raise RuntimeError("Engine service state is unknown; reconcile before starting")
    return state in {"inactive", "failed"}


def _legacy_owner(directory):
    """Old detached starts have a receipt before acquiring the model leases."""
    if not lease_free(directory, "overnight-start.lock"):
        return "The legacy launcher is still publishing its launch receipt"
    from start_os_overnight import status as legacy_status
    legacy = legacy_status(directory)
    if legacy["status"] not in {"NOT_STARTED", "EXITED", "FAILED"}:
        return "The legacy detached launch is live or unresolved; checkpoint it before migration"
    return None


def install_units(repo, directory):
    # The explicit start must keep this user's monitor alive after logout.
    # No sudo or interactive privilege fallback; failure remains observable.
    from os_goal_power import ensure_linger
    ensure_linger()
    root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "systemd/user"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name, content in render_units(repo, directory).items():
        target = root / name
        if target.is_symlink():
            raise ValueError("Refusing a symlinked service destination")
        temporary = root / (name + "." + uuid4().hex + ".mckernel-tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    _systemctl("daemon-reload")
    return unit_names(directory)


def mailbox_preflight(repo):
    """Read-only identity and destination checks; never dispatches a notification."""
    from os_goal_mailbox import Mailbox, _gh_api
    mailbox = Mailbox(repo, Path(repo), Path(repo) / "scripts/os_goal_mailbox.json")
    user = _gh_api("user")
    if (not isinstance(user, dict) or user.get("id") != mailbox.user_id
            or user.get("login") != mailbox.login or user.get("type") != "User"):
        raise RuntimeError("GitHub CLI identity does not match the configured mailbox owner")
    pull = _gh_api(f"repos/{mailbox.remote}/pulls/{mailbox.issue}")
    if (not isinstance(pull, dict) or pull.get("state") != "open" or pull.get("draft") is not True
            or pull.get("merged") is True or (pull.get("user") or {}).get("id") != mailbox.user_id
            or ((pull.get("base") or {}).get("repo") or {}).get("full_name") != mailbox.remote):
        raise RuntimeError("The configured GitHub mailbox is not the expected open draft PR")
    workflow = _gh_api(f"repos/{mailbox.remote}/actions/workflows/{mailbox.workflow}")
    if not isinstance(workflow, dict) or workflow.get("state") != "active":
        raise RuntimeError("GitHub mailbox notification workflow is not active")
    return {"status": "READ_ACCESS_VERIFIED", "authorized_user": mailbox.login,
            "issue_number": mailbox.issue, "workflow": mailbox.workflow,
            "email_delivery": "unverified"}


def default_arguments(repo):
    return ["--hours", "0", "--max-restarts", "-1", "--repair-agent-failures", "--stop-after-m14-m15",
            "--profile", "aggressive", "--max-agents", "2", "--build-jobs", "3", "--memory-gib", "4",
            "--startup-instruction-file", str(Path(repo) / "scripts/m14-m15-overnight-instruction.txt"),
            "--agent-windows", "off"]


def _validated_arguments(repo, arguments):
    from run_os_goal import arguments as parse_arguments
    values = list(arguments if arguments is not None else default_arguments(repo))
    hidden = {"--worker", "--recovered", "--supervisor", "--guardian-run-id", "--guardian-recovery-proof",
              "--fresh-recovery-proof", "--recovery-goal-sha256", "--recovery-require-active"}
    if any(value.split("=", 1)[0] in hidden for value in values):
        raise ValueError("Internal recovery controls cannot be supplied as a new service start")
    parsed = parse_arguments(values)
    if any((parsed.status, parsed.progress, parsed.check, parsed.check_sudo, parsed.dry_run,
            parsed.instruct is not None)):
        raise ValueError("Read-only and instruction commands do not start a service")
    return values


def status(repo, directory):
    from os_goal_readiness import evaluate_readiness
    names = unit_names(directory)
    result = {"units": names, "mailbox_url": "https://github.com/phoenix-hacking/mckernel/pull/3",
              "state_directory": str(directory),
              "status_text_url": "https://github.com/phoenix-hacking/mckernel/blob/codex/mckernel-control-mailbox/status.txt",
              "status_text_path": str(Path(directory) / "status.txt"),
              "readiness": evaluate_readiness(directory)}
    try:
        result["status_text"] = read_json(Path(directory) / "status-text-state.json")
    except FileNotFoundError:
        result["status_text"] = {"status": "NOT_GENERATED"}
    try:
        guard = read_json(Path(directory) / "guardian.json")
    except FileNotFoundError:
        return dict(result, status="NOT_STARTED")
    alive = (isinstance(guard.get("start"), str) and guard["start"].isdigit()
             and process_start(guard.get("pid")) == guard["start"]
             and not lease_free(directory, "guardian.lock"))
    result.update(status=guard.get("phase", "STARTING") if alive else "GUARDIAN_NOT_LIVE",
                  guardian_live=alive, guardian_pid=guard.get("pid"),
                  heartbeat_at=guard.get("heartbeat_at"), reason=guard.get("reason"),
                  mailbox_error=guard.get("mailbox_error"))
    try:
        mailbox = read_json(Path(directory) / "mailbox-state.json")
        event = mailbox.get("active_notice_event_id")
        notice = (mailbox.get("notices") or {}).get(event, {})
        result["mailbox"] = {key: mailbox.get(key) for key in
                             ("last_poll_at", "last_successful_poll_at", "next_poll_at", "last_error", "pending_resumes", "messages")}
        result["mailbox"].update(active_notice_event_id=event, notice_requested=bool(notice.get("requested")),
                                  observed_notice=bool(notice.get("observed_comment_id")),
                                  observed_comment_id=notice.get("observed_comment_id"))
    except FileNotFoundError:
        pass
    return result


def start(repo, directory, arguments=None):
    from os_goal_guardian import authorize_start
    repo, directory = Path(repo).resolve(), Path(directory).resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    values = _validated_arguments(repo, arguments)
    # The monitor may restart at any time. Keep its launch callback serialized
    # with config/intent publication, without holding this lock during READY.
    try:
        with _service_lock(directory):
            if not lease_free(directory, "watch.lock") or not lease_free(directory, "run.lock"):
                return dict(status(repo, directory), status="EXISTING_OWNER",
                            reason="Existing model work must checkpoint before a new guarded launch")
            legacy = _legacy_owner(directory)
            if legacy:
                return dict(status(repo, directory), status="EXISTING_OWNER", reason=legacy)
            if shutil.which("systemd-inhibit") is None or shutil.which("taskset") is None:
                raise RuntimeError("systemd-inhibit and taskset are required for the guarded engine")
            names = install_units(repo, directory)
            if not _engine_idle(directory):
                return dict(status(repo, directory), status="EXISTING_OWNER",
                            reason="The engine service already owns a launch")
            guard = read_json(directory / "guardian.json") if (directory / "guardian.json").exists() else {}
            if guard.get("launch"):
                return dict(status(repo, directory), status="EXISTING_OWNER",
                            reason="The previous engine launch still requires reconciliation")
            pending = [read_json(path) for path in (directory / "guardian-intents").glob("*.json")]
            pending = [intent for intent in pending if intent.get("status") in {"pending", "sending"}]
            if pending:
                # A crash before enable --now must not lose an already authorized
                # start or replace its settings. Re-enable only the monitor below.
                intent = pending[0]
            else:
                verified = mailbox_preflight(repo)
                from run_os_goal import arguments as parse_arguments
                parsed = parse_arguments(values)
                # Guardian recovery reconstructs this durable argv, rather than
                # the first supervisor's in-memory worker command.
                if parsed.credit_budget is not None and parsed.credit_run_id is None:
                    values += ["--credit-run-id", uuid4().hex]
                atomic_json(directory / CONFIG, {"schema_version": 1, "repo": str(repo),
                                                  "arguments": values, "mailbox_preflight": verified})
                intent = authorize_start(directory)
    except EngineLaunchDeferred:
        return dict(status(repo, directory), status="EXISTING_OWNER",
                    reason="Another service launch is publishing its ownership receipt")
    _systemctl("enable", "--now", names["guardian"])
    return dict(status(repo, directory), start_request_id=intent["request_id"])


def _launch_engine(repo, directory, proof):
    with _service_lock(directory):
        guard = read_json(Path(directory) / "guardian.json")
        if process_start(guard.get("pid")) != guard.get("start"):
            raise RuntimeError("Guardian identity unavailable for engine launch")
        if not lease_free(directory, "watch.lock") or not lease_free(directory, "run.lock"):
            raise RuntimeError("Existing model lease prevents engine launch")
        if not _engine_idle(directory):
            raise EngineLaunchDeferred("The previous engine service has not yet retired")
        atomic_json(Path(directory) / NEXT, {"run_id": guard["run_id"], "guardian_pid": guard["pid"],
                    "guardian_start": guard["start"], "proof_path": str(proof) if proof else None,
                    "created_at": time.time()})
        name = unit_names(directory)["engine"]
        _systemctl("start", name, timeout=10)
    return {"started": True, "unit": name}


def engine(repo, directory):
    config, launch, guard = (read_json(Path(directory) / name) for name in (CONFIG, NEXT, "guardian.json"))
    if (config.get("repo") != str(Path(repo).resolve()) or launch.get("run_id") != guard.get("run_id")
            or launch.get("guardian_pid") != guard.get("pid") or launch.get("guardian_start") != guard.get("start")
            or process_start(guard.get("pid")) != guard.get("start") or lease_free(directory, "guardian.lock")):
        raise RuntimeError("Engine launch is not bound to the live guardian")
    values = _validated_arguments(repo, config.get("arguments"))
    if launch.get("proof_path"):
        from watch_os_goal import saved_recovery_argv
        values = saved_recovery_argv(values)
    values += ["--supervisor", "--guardian-run-id", guard["run_id"]]
    if launch.get("proof_path"):
        values += ["--guardian-recovery-proof", launch["proof_path"]]
    inhibit, taskset = shutil.which("systemd-inhibit"), shutil.which("taskset")
    if not inhibit or not taskset:
        raise RuntimeError("Sleep protection and taskset are required; engine was not started")
    command = [inhibit, "--what=idle:sleep", "--mode=block", "--who=McKernel",
               "--why=Unattended M14/M15 work", "--", taskset, "-c", "0,6,7", sys.executable,
               "-B", str(Path(repo) / "scripts/run_os_goal.py"), *values]
    os.execv(command[0], command)


def campaign_blocker(repo):
    """A small attributed excerpt from the public campaign, not invented diagnosis."""
    try:
        with (Path(repo) / "CAMPAIGN.md").open() as stream:
            text = stream.read(48000)
    except OSError:
        return None
    section = text.split("## Current decision", 1)
    if len(section) < 2:
        return None
    section = section[1].split("\n## ", 1)[0]
    paragraphs = section.split("\n\n")
    for paragraph in paragraphs:
        if re.search(r"critical.path blocker", paragraph, re.I):
            return "Latest recorded CAMPAIGN.md: " + " ".join(paragraph.split())[:1000]
    for paragraph in paragraphs:
        if re.search(r"SOURCE/BINDING IMPASSE|missing input|remaining prerequisite", paragraph, re.I):
            return "Latest recorded CAMPAIGN.md: " + " ".join(paragraph.split())[:1000]
    return None


def guardian(repo, directory):
    from os_goal_guardian import Guardian, sd_notify
    from os_goal_mailbox import Mailbox
    from os_goal_status_feed import StatusFeed
    mailbox = Mailbox(repo, directory, Path(repo) / "scripts/os_goal_mailbox.json")
    feed = StatusFeed(repo, directory)
    def poll(control_directory, context):
        state = context.get("engine_state") or {}
        if (state.get("goal") or {}).get("status") == "blocked":
            context = dict(context, missing_input=campaign_blocker(repo))
        try:
            reply = mailbox.poll(context)
        except Exception as error:
            from os_goal_stop_log import _text
            reply = {"status": "ERROR", "reason": _text(str(error), 500)}
        # The comment poll and the status upload are separate bounded segments;
        # a slow GitHub response cannot consume the whole watchdog interval.
        sd_notify("Mailbox checked; refreshing the generated status view")
        try:
            feed.tick(context)
        except Exception as error:
            from os_goal_stop_log import _text
            failure = {"status": "ERROR", "reason": _text(str(error), 500),
                       "next_refresh_at": time.time() + 600}
            try:
                atomic_json(Path(directory) / "status-text-state.json", failure)
            except (OSError, ValueError):
                print(json.dumps({"status_text_error": failure}), flush=True)
        return reply
    monitor = Guardian(repo, directory,
                       launch_engine=lambda proof: _launch_engine(repo, directory, proof),
                       mailbox_poll=poll, mailbox_ack=mailbox.ack_resume)
    try:
        return monitor.run()
    finally:
        monitor.close()


def main(argv=None, *, engine_arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="start",
                        choices=("start", "prepare", "status", "status-text", "stop", "dry-run", "guardian", "engine"))
    args = parser.parse_args(argv)
    os.umask(0o077)
    directory = None
    try:
        directory = runtime_directory(REPO)
        if args.command == "guardian":
            return guardian(REPO, directory) or 0
        if args.command == "engine":
            return engine(REPO, directory) or 0
        if args.command == "start":
            result = start(REPO, directory, engine_arguments)
        elif args.command == "prepare":
            from os_goal_overnight_prepare import prepare_overnight
            result = prepare_overnight(REPO, directory)
        elif args.command == "status-text":
            from os_goal_status_feed import StatusFeed
            result = StatusFeed(REPO, directory).tick(publish=False)
            if result["status"] == "GENERATED":
                print((directory / "status.txt").read_text(encoding="utf-8"), end="")
                return 0
        elif args.command == "status":
            result = status(REPO, directory)
        elif args.command == "stop":
            from os_goal_guardian import request_stop
            if lease_free(directory, "guardian.lock"):
                raise RuntimeError("No verified live guardian is available for a stop request")
            result = dict(status(REPO, directory), status="STOP_REQUESTED", stop_request=request_stop(directory))
        else:
            result = {"status": "DRY_RUN", "model_calls": 0,
                      "arguments": _validated_arguments(REPO, engine_arguments),
                      "units": render_units(REPO, directory),
                      "mailbox_url": "https://github.com/phoenix-hacking/mckernel/pull/3"}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        result = {"status": "FAILED", "reason": str(error)}
        if directory is not None and args.command in {"start", "guardian", "engine"}:
            try:
                from os_goal_stop_log import write_stop_record
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                result["stop_log"] = write_stop_record(directory, {}, event="guarded_service_failed",
                                                       reason="launcher_error", error=error)["journal_path"]
            except (OSError, ValueError, RuntimeError) as logging_error:
                result["stop_log_error"] = type(logging_error).__name__
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["status"] in {"FAILED", "GUARDIAN_NOT_LIVE", "ERROR", "BLOCKED", "SETUP_NEEDED"} else 0


if __name__ == "__main__":
    sys.exit(main())
