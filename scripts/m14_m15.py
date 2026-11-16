#!/usr/bin/env python3
"""Run, watch, or stop the existing McKernel M14/M15 closure campaign.

Functional OS/apps and Rust/allowed assembly only; NO SECURITY TESTING.
"""
import argparse
import json
from pathlib import Path
import sys
import time

from m14_m15_control import request_stop, status as control_status
from m14_m15_progress import render_progress
from os_goal_service import runtime_directory


REPO = Path(__file__).resolve().parents[1]
ROOT = "01a18bc3-e072-7810-9426-75101b0856c0"


def read_state(repo):
    path = Path(runtime_directory(repo)) / "state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def start_existing(repo):
    """Explicit user run only: resume the same owner, never launch another server."""
    repo = Path(repo).resolve()
    state = read_state(repo)
    if state.get("thread_id") != ROOT:
        raise ValueError("The saved M14/M15 Root is unavailable; no replacement was started")
    owner = control_status(repo)
    if (owner.get("worker_birth_observation") != state.get("worker_start")
            or owner.get("server_birth_observation") != state.get("server_start")):
        raise ValueError("The original controller is unavailable; preserve its saved state")
    if state.get("phase") == "running":
        if state.get("simple_m14_m15") is not True:
            raise ValueError("Stop the current campaign before switching to the simple loop")
        return {"status": "already_running", "thread_id": ROOT}
    if state.get("active_turns"):
        raise ValueError("Stop is still draining worker turns; inspect status before running")
    from run_os_goal import queue_instruction, queue_same_owner_resume, simple_dispatch_instruction
    instruction = simple_dispatch_instruction()
    source = "manual-simple-m14-m15-" + str(time.time_ns())
    directory = Path(runtime_directory(repo))
    control = queue_same_owner_resume(
        directory, instruction, source_id=source,
        allow_active_primary=False, simple_m14_m15=True)
    instruction_id = queue_instruction(directory, instruction, source_id=source + "-goal")
    return {"status": "resume_requested", "control": control,
            "instruction": instruction_id, "thread_id": ROOT,
            "new_controller_started": False}


def watch(repo, *, interval=2.0, stream=None, once=False):
    """Refresh every open row and the Markdown without any model calls."""
    stream = stream or sys.stdout
    previous = None
    while True:
        try:
            markdown = render_progress(repo, runtime_state=read_state(repo))
        except (OSError, ValueError, KeyError) as error:
            # Keep the last valid file if an input is being replaced or is invalid.
            stream.write("Progress refresh: " + str(error) + "\n")
            stream.flush()
        else:
            if markdown != previous:
                if getattr(stream, "isatty", lambda: False)():
                    stream.write("\033[2J\033[H")
                stream.write(markdown)
                if not markdown.endswith("\n"):
                    stream.write("\n")
                stream.flush()
                previous = markdown
        if once:
            return
        time.sleep(interval)


def watch_agents(repo, *, stream=None, once=False, lines=80):
    """Show the existing roster/log and refresh the milestone file read-only."""
    from watch_os_agents import Follower
    stream = stream or sys.stdout
    repo = Path(repo).resolve()
    follower = Follower(Path(runtime_directory(repo)) / "state.json", stream, lines=lines)
    stream.write("Live agents and logs. Milestone progress: " +
                 str(repo / "docs/verification/M14-M15-OPEN-DELIVERABLES.md") + "\n")
    stream.write("Stop campaign: python3 -B " + str(repo / "scripts/m14_m15.py") + " stop\n")
    stream.flush()
    last_error = None
    try:
        while True:
            state = follower.step()
            if state is not None:
                try:
                    render_progress(repo, runtime_state=state)
                    last_error = None
                except (OSError, ValueError, KeyError) as error:
                    message = "Progress refresh: " + str(error)
                    if message != last_error:
                        stream.write(message + "\n")
                        stream.flush()
                        last_error = message
            if once:
                return
            time.sleep(1)
    finally:
        follower.close()


def main(argv=None, *, repo=REPO):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    sub.required = True
    sub.add_parser("status", help="Show every open check and update its Markdown")
    viewer = sub.add_parser("watch", help="Continuously show all checks; no model calls")
    viewer.add_argument("--interval", type=float, default=2.0)
    viewer.add_argument("--once", action="store_true")
    agents = sub.add_parser("agents", help="Follow the live agent roster and logs; no new work")
    agents.add_argument("--once", action="store_true")
    agents.add_argument("--lines", type=int, default=80)
    sub.add_parser("stop", help="Stop dispatch and interrupt this campaign's active workers")
    run = sub.add_parser("run", help="Explicitly resume the same Root in the simple loop")
    run.add_argument("--no-watch", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "watch" and not 0.2 <= args.interval <= 60:
        parser.error("interval must be between0.2 and60 seconds")
    if args.command == "agents" and not 1 <= args.lines <= 10000:
        parser.error("lines must be between1and10000")
    if args.command == "status":
        print(render_progress(repo, runtime_state=read_state(repo)), end="")
    elif args.command == "watch":
        watch(repo, interval=args.interval, once=args.once)
    elif args.command == "agents":
        watch_agents(repo, once=args.once, lines=args.lines)
    elif args.command == "stop":
        result = request_stop(repo)
        summary = {key: result.get(key) for key in
                   ("controller_dispatch_enabled", "stop_reason", "active_turns", "supervision_timer")}
        summary["stop_request_status"] = (result.get("stop_request") or {}).get("status")
        print(json.dumps(summary, indent=2))
        print(render_progress(repo, runtime_state=read_state(repo)), end="")
    else:
        print(json.dumps(start_existing(repo), indent=2), flush=True)
        if not args.no_watch:
            watch_agents(repo)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nViewer closed. Stop campaign work with: python3 -B scripts/m14_m15.py stop")
        raise SystemExit(0)
    except (OSError, ValueError, RuntimeError) as error:
        print("M14/M15: " + str(error), file=sys.stderr)
        raise SystemExit(1)
