#!/usr/bin/env python3
"""Follow functional McKernel agent logs across worker resets; no security testing.

Read-only: this viewer never starts, resumes, signals or cleans up a campaign.
"""

import argparse
import codecs
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time


def process_alive(pid, birth):
    if type(pid) is not int or not isinstance(birth, str) or not birth.isdigit():
        return False
    try:
        fields = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        return fields[0] not in {"Z", "X"} and fields[19] == birth
    except (OSError, IndexError):
        return False


def tail_offset(stream, lines, maximum=1024 * 1024):
    """Find a bounded initial tail without reading an entire multi-hour log."""
    end = stream.seek(0, 2)
    position, data = end, b""
    while position and len(data) < maximum and data.count(b"\n") <= lines:
        size = min(65536, position, maximum - len(data))
        position -= size
        stream.seek(position)
        data = stream.read(size) + data
    rows = data.splitlines(keepends=True)
    return end - len(b"".join(rows[-lines:]))


def supervisor_status(state_path):
    """A live worker alone does not prove its recovery supervisor is alive."""
    try:
        record = json.loads((Path(state_path).parent / "watcher.json").read_text())
        if record.get("event") == "watcher_stopped":
            return "stopped"
        if not record.get("watcher_start"):
            return "unknown"
        return "live" if process_alive(record.get("watcher_pid"), record["watcher_start"]) else "absent"
    except (OSError, ValueError, TypeError, AttributeError):
        return "unknown"


class Follower:
    def __init__(self, state_path, output=sys.stdout, *, lines=80, primary=False):
        self.state_path, self.output = Path(state_path), output
        self.lines, self.primary = lines, primary
        self.file, self.identity, self.last_status = None, None, None
        self.last_agents = None
        self.last_error = None
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")

    def notice(self, message):
        self.output.write("[agent-watch] " + message + "\n")

    def roster(self, state):
        agents = state.get("agents") or {}
        turns = state.get("active_turns") or {}
        if not isinstance(agents, dict) or not isinstance(turns, dict):
            return
        rows = []
        for thread in agents.keys() | turns.keys():
            agent = agents.get(thread) or {}
            if not isinstance(agent, dict):
                continue
            name = agent.get("name") or thread
            status = agent.get("status") or "unknown"
            if thread in turns:
                status = "running"
            elif status == "inProgress":
                status = "inProgress (last recorded; no active turn)"
            rows.append((thread, name, status))
        rows.sort(key=lambda row: (row[0] != state.get("thread_id"), row[1], row[0]))
        signature = (len(turns), tuple(rows))
        if signature != self.last_agents:
            self.notice("agents: {} active turn(s); {} known".format(len(turns), len(rows)))
            for _, name, status in rows:
                self.notice("  {} — {}".format(name, status))
            self.last_agents = signature

    def step(self):
        try:
            with self.state_path.open("rb") as source:
                raw = source.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError("state snapshot exceeds8MiB")
            state = json.loads(raw)
            if not isinstance(state, dict):
                raise ValueError("state snapshot is not an object")
            phase = state.get("phase", "unknown")
            supervisor = supervisor_status(self.state_path)
            if phase == "running" and not process_alive(state.get("worker_pid"), state.get("worker_start")):
                phase = "stale_running_snapshot"
            elif phase == "running" and supervisor in {"stopped", "absent"}:
                phase = "unmonitored_worker"
            elif phase == "running" and (state.get("heartbeat_at") or state.get("updated_at")):
                stamp = state.get("heartbeat_at") or state["updated_at"]
                updated = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - updated).total_seconds() > 60:
                    phase = "heartbeat_stale"
            goal = state.get("goal") or {}
            status = (phase, goal.get("status"), state.get("stop_reason"),
                      state.get("worker_pid"), state.get("log_dir"), supervisor)
            if status != self.last_status:
                self.notice("phase={} goal={} reason={} worker={} supervisor={}".format(
                    *status[:4], supervisor))
                self.last_status = status
            self.roster(state)
            path = state.get("console_log")
            if self.primary:
                path = (state.get("agents", {}).get(state.get("thread_id"), {})
                        .get("path")) or path
            if path:
                path = Path(path)
                path.resolve().relative_to((self.state_path.parent / "runs").resolve())
                info = path.stat()
                identity = (str(path), info.st_dev, info.st_ino)
                if identity != self.identity:
                    self.close()
                    self.file = path.open("rb")
                    self.file.seek(tail_offset(self.file, self.lines))
                    self.identity = identity
                    self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
                    self.notice("following " + str(path))
                elif self.file.tell() > info.st_size:
                    self.file.seek(0)
                    self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
                    self.notice("log truncated; following retained current file")
                chunk = self.file.read(65536)
                if chunk:
                    self.output.write(self.decoder.decode(chunk))
            self.output.flush()
            self.last_error = None
            return state
        except (OSError, ValueError, TypeError, AttributeError) as error:
            marker = ("unavailable", type(error).__name__, str(error))
            if marker != self.last_error:
                self.notice("waiting for readable current state/log: " + str(error))
                self.last_error = marker
            self.output.flush()
            return None

    def close(self):
        if self.file is not None:
            self.file.close()
        self.file, self.identity = None, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path,
                        default=Path(__file__).resolve().parents[1] / ".git/os-autopilot/state.json")
    parser.add_argument("--lines", type=int, default=80)
    parser.add_argument("--primary", action="store_true", help="Show only the coordinator's agent log")
    parser.add_argument("--once", action="store_true", help="Print current status/tail and exit")
    args = parser.parse_args(argv)
    if not 1 <= args.lines <= 10000:
        parser.error("lines must be between1and10000")
    follower = Follower(args.state, lines=args.lines, primary=args.primary)
    try:
        while True:
            follower.step()
            if args.once:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        follower.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
