#!/usr/bin/env python3
"""Manually start the saved M14/M15 run in the background; --check is read-only.

Functional McKernel OS/apps and Rust/allowed assembly; NO SECURITY TESTING.
The existing controller owns all model, account, resource and custody decisions.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread

from os_goal_service import runtime_directory
from os_goal_writer import require_saved_writer_ready

REPO = Path(__file__).resolve().parents[1]


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check settings and sleep inhibition; no model work")
    parser.add_argument("--no-follow", action="store_true", help="Start in the background and print the log path without following it")
    parser.add_argument("--agents", type=int, default=11)
    parser.add_argument("--jobs", type=int, default=5)
    parser.add_argument("--work-memory-gib", type=float, default=28)
    parser.add_argument("--memory-gib", type=float, help="Optional HOST-only sub-budget inside the shared total")
    parser.add_argument("--cpus", default="0,6,7")
    return parser.parse_args(argv)


def controller_command(args):
    command = [sys.executable, "-B", str(REPO / "scripts/run_os_goal.py"),
            "--supervisor", "--continuous", "--stop-after-m14-m15",
            "--model", "gpt-6.1-sol", "--effort", "max",
            "--max-agents", str(args.agents), "--build-jobs", str(args.jobs),
            "--work-memory-gib", str(args.work_memory_gib), "--host-cpus", args.cpus,
            "--hours", "0", "--max-restarts", "0", "--agent-windows", "off",
            "--progress-checkpoint-seconds", "1800", "--progress-stall-seconds", "1800",
            "--credit-run-id", "7c6ef3604bfb4008a917bba8cfb6cfaa",
            "--credit-budget", "52079.8011050000",
            "--startup-instruction-file", str(REPO / "instructions/M14-M15-OVERNIGHT.md")]
    if args.memory_gib is not None:
        command += ["--memory-gib", str(args.memory_gib)]
    return command


def follow_log(child, path, viewer):
    # tail --pid also sees an unreaped zombie as alive. Reap concurrently so
    # the viewer can finish; Popen.wait serializes concurrent callers safely.
    Thread(target=child.wait, daemon=True, name="m14-m15-child-wait").start()
    subprocess.run([viewer, "--pid=" + str(child.pid), "-n", "+1", "-F", str(path)], check=False)
    return child.wait()


def main(argv=None):
    args = arguments(argv)
    from run_os_goal import OBJECTIVE
    runtime = runtime_directory(REPO)
    require_saved_writer_ready(runtime, expected_repo=REPO, expected_objective=OBJECTIVE)
    command = controller_command(args)
    if args.check:
        from os_goal_power import probe_inhibition
        probe_inhibition()
        return subprocess.run(command + ["--check"], check=False, timeout=60).returncode
    # Validate locally before detaching. This creates no model or resource grant.
    checked = subprocess.run(command + ["--dry-run"], check=False, capture_output=True, text=True, timeout=15)
    if checked.returncode:
        sys.stderr.write(checked.stderr)
        return checked.returncode
    inhibitor = shutil.which("systemd-inhibit")
    taskset = shutil.which("taskset")
    if not inhibitor or not taskset:
        raise RuntimeError("Sleep inhibitor/taskset unavailable; no overnight run was started")
    command = [inhibitor, "--what=idle:sleep", "--mode=block", "--who=McKernel",
               "--why=Close original M14 and M15", "--", taskset, "-c", args.cpus, *command]
    directory = runtime / "manual-launches"
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = directory / (stamp + ".log")
    with path.open("x") as output:
        path.chmod(0o600)
        child = subprocess.Popen(command, cwd=str(REPO), stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    print(json.dumps({"status": "START_REQUESTED", "pid": child.pid, "log": str(path),
                      "note": "Verify actual dispatcher/worker readiness in this log; submission is not acceptance."}), flush=True)
    if not args.no_follow:
        viewer = shutil.which("tail")
        if viewer:
            try:
                return follow_log(child, path, viewer)
            except KeyboardInterrupt:
                print("Log view closed; the background run continues. Log: " + str(path), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
