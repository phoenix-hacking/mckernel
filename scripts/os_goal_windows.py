"""Per-run agent logs and read-only GNOME terminal followers (stdlib only).

Each new run may open new windows. Old windows stop following at completion or
owner death and remain at a dismissal prompt; no user terminals are killed.
Closed/shutdown child viewers exit automatically; their historical logs remain.
The live-agent limit does not limit finished windows waiting for dismissal.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


class TerminalText:
    """Strip terminal controls, including escape sequences split across deltas."""

    def __init__(self):
        self.state = "text"

    def feed(self, value):
        result = []
        for char in str(value):
            if self.state == "string":
                if char in "\a\x9c":
                    self.state = "text"
                elif char == "\x1b":
                    self.state = "string_escape"
            elif self.state == "string_escape":
                self.state = "text" if char == "\\" else "string"
            elif self.state == "csi":
                if "@" <= char <= "~":
                    self.state = "text"
            elif self.state == "escape":
                if char == "[":
                    self.state = "csi"
                elif char in "]PX^_":
                    self.state = "string"
                elif not " " <= char <= "/":
                    self.state = "text"
            elif char == "\x1b":
                self.state = "escape"
            elif char == "\x9b":
                self.state = "csi"
            elif char in "\x90\x98\x9d\x9e\x9f":
                self.state = "string"
            elif char in "\n\t" or char.isprintable():
                result.append(char)
        return "".join(result)


def clean_text(value):
    return TerminalText().feed(value)


def clean_name(value):
    return " ".join(clean_text(value).split())[:96]


def process_birth(pid):
    """Include boot identity and start ticks; PID reuse must not keep a viewer alive."""
    try:
        fields = (Path("/proc") / str(int(pid)) / "stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] in {"Z", "X"}:
            return None
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip() + ":" + fields[19]
    except (OSError, ValueError, TypeError, IndexError):
        return None


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def window_capability(mode="auto"):
    """JSON-safe desktop preflight; never starts a terminal or an agent."""
    if mode not in {"auto", "on", "off"}:
        raise ValueError("agent_windows must be auto, on, or off")
    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or None
    backend = shutil.which("gnome-terminal") if mode != "off" else None
    error = None
    if mode != "off":
        if not display:
            error = "DISPLAY/WAYLAND_DISPLAY is unset"
        elif not backend:
            error = "gnome-terminal is unavailable"
    return {"enabled": mode != "off" and error is None, "backend": backend,
            "display": display, "error": error}


class AgentWindows:
    def __init__(self, run_dir, mode, notice):
        if mode not in {"auto", "on", "off"}:
            raise ValueError("agent_windows must be auto, on, or off")
        self.directory = Path(run_dir).resolve() / "agents"
        self.directory.mkdir(mode=0o700)
        self.index_path = self.directory / "index.json"
        self.owner_path = self.directory / "owner.json"
        self.complete_path = self.directory / "complete"
        self.mode, self.notice = mode, notice
        self.rows, self.launches = {}, {}
        self.closed, self.last_index = False, None
        capability = window_capability(mode)
        self.terminal, self.unavailable = capability["backend"], capability["error"]
        owner = {"pid": os.getpid(), "birth": process_birth(os.getpid())}
        atomic_json(self.owner_path, owner)
        if not owner["birth"] and mode != "off":
            self.unavailable = "cannot record the worker PID birth identity"
        self.save()
        if self.unavailable:
            self.notice("Agent windows " + mode + " unavailable: " + self.unavailable
                        + "; fallback readable logs: " + str(self.directory))

    def ensure(self, thread):
        if thread not in self.rows:
            digest = hashlib.sha256(str(thread).encode("utf-8", errors="surrogatepass")).hexdigest()
            path = self.directory / (digest + ".log")
            path.touch()
            self.rows[thread] = {"id": thread, "name": "", "path": str(path),
                                 "closed_path": str(path.with_suffix(".closed")),
                                 "generation": 0,
                                 "status": "unknown", "window_status": "pending_primary"}
        return self.rows[thread]

    def revive(self, thread):
        row = self.ensure(thread)
        row["generation"] += 1
        row.update(closed_path=str(Path(row["path"]).with_suffix(
            "." + str(row["generation"]) + ".closed")), window_status="pending_primary")
        row.pop("window_error", None)
        # Keep all earlier markers: old followers may not have observed them yet.

    def write(self, thread, rendered):
        row = self.ensure(thread)
        # Retired children cost no file descriptors; resumed output appends safely.
        with Path(row["path"]).open("a", encoding="utf-8", errors="replace") as stream:
            stream.write(rendered)

    def save(self):
        # Whitelist metadata only: no events, prompts, environment or credentials.
        data = {"schema_version": 1, "mode": self.mode, "owner_path": str(self.owner_path),
                "complete_path": str(self.complete_path), "agents": list(self.rows.values())}
        serialized = json.dumps(data, sort_keys=True)
        if serialized != self.last_index:
            atomic_json(self.index_path, data)
            self.last_index = serialized

    def failed(self, row, reason):
        row.update(window_status="failed", window_error=clean_name(reason))
        self.notice("Agent window failed for " + row["name"] + ": " + row["window_error"]
                    + "; fallback readable log: " + row["path"])

    def sync(self, agents, primary, label):
        if self.closed:
            return
        for thread, agent in agents.items():
            row = self.ensure(thread)
            row.update(name=clean_name(label(thread)), status=clean_name(agent.get("status", "unknown")))
            if thread == primary:
                row["window_status"] = "primary"
                continue
            if agent.get("retired"):
                marker = Path(row["closed_path"])
                if not marker.exists():
                    marker.write_text("Child closed; final output flushed.\n", encoding="utf-8")
                row["window_status"] = "closed"
                continue
            if row["window_status"] != "pending_primary":
                continue
            if self.mode == "off":
                row["window_status"] = "off"
            elif self.unavailable:
                row.update(window_status="unavailable", window_error=self.unavailable)
            elif primary is not None or agent.get("child"):
                errors = tempfile.TemporaryFile()
                try:
                    argv = [self.terminal, "--window", "--title", "McKernel " + row["name"],
                            "--", sys.executable, "-u", str(Path(__file__).resolve()),
                            "follow", "--log", row["path"], "--owner", str(self.owner_path),
                            "--complete", str(self.complete_path), "--index", str(self.index_path),
                            "--closed", row["closed_path"]]
                    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                            stderr=errors, start_new_session=True)
                except OSError as error:
                    errors.close()
                    self.failed(row, str(error))
                else:
                    row["window_status"] = "launching"
                    self.launches[(thread, row["generation"])] = (proc, errors)
        for (thread, generation), (proc, errors) in list(self.launches.items()):
            code = proc.poll()
            if code is None:
                continue
            row = self.rows[thread]
            errors.seek(0)
            detail = errors.read(4096).decode("utf-8", errors="replace")
            errors.close()
            del self.launches[(thread, generation)]
            if generation != row["generation"]:
                continue
            if code:
                self.failed(row, "gnome-terminal exit " + str(code) + ": " + detail)
            elif row["window_status"] != "closed":
                # Acknowledges the terminal launch, not proof of a visible window.
                row["window_status"] = "launched"
        self.save()

    def close(self):
        if self.closed:
            return
        self.complete_path.write_text("Run complete; followers may stop.\n", encoding="utf-8")
        for row in self.rows.values():
            row["run_complete"] = True
        self.save()
        # Never terminate terminal processes: the marker stops only our followers.
        for proc, errors in self.launches.values():
            proc.poll()
            errors.close()
        self.closed = True


def follow(log_path, owner_path, complete_path, index_path, closed_path=None):
    """Follow only this run's log. No RPC, inference, shell or worker signalling."""
    owner = json.loads(owner_path.read_text())
    closed_path = closed_path if closed_path is not None else log_path.with_suffix(".closed")
    title = None
    sanitizer = TerminalText()
    with log_path.open(encoding="utf-8", errors="replace") as stream:
        while True:
            if sys.stdout.isatty():
                try:
                    rows = json.loads(index_path.read_text())["agents"]
                    row = next(row for row in rows if row["path"] == str(log_path))
                    name = "McKernel " + clean_name(row["name"])
                    if name != title:
                        sys.stdout.write("\x1b]0;" + name + "\a")
                        title = name
                except (OSError, ValueError, KeyError, StopIteration):
                    pass
            child_closed = closed_path.exists()
            stopped = child_closed or complete_path.exists() or not owner.get("birth") or (
                process_birth(owner.get("pid")) != owner["birth"])
            chunk = stream.read(65536)
            if chunk:
                sys.stdout.write(sanitizer.feed(chunk))
                sys.stdout.flush()
                continue
            if stopped:
                break
            time.sleep(0.2)
    if child_closed:
        print("\nChild closed; final output retained in " + str(log_path), flush=True)
        return
    print("\nRun complete or worker exited; stopped following. This is a log viewer only.", flush=True)
    if sys.stdin.isatty():
        try:
            input("Press Enter to close this window. A new run may open new windows. ")
        except (EOFError, KeyboardInterrupt):
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["follow"])
    for name in ("log", "owner", "complete", "index"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--closed", type=Path, help="This viewer generation's closure marker; default: LOG.with_suffix('.closed')")
    args = parser.parse_args(argv)
    follow(args.log, args.owner, args.complete, args.index, args.closed)


if __name__ == "__main__":
    main()
