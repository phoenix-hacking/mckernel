"""Readable, bounded-buffer rendering of the launcher's app-server events."""

from datetime import datetime, timezone
import re
import time


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class LiveOutput:
    def __init__(self, log_dir, quiet=False):
        self.log = (log_dir / "console.log").open("a", buffering=1)
        self.quiet = quiet
        self.primary = None
        self.agents = {}
        self.pending = {}
        self.streamed = set()
        self.agent_event_count = 0

    def label(self, thread):
        if thread == "server":
            return "server"
        if thread == self.primary:
            return "dispatcher"
        return self.agents.get(thread, {}).get("name") or ("agent-" + str(thread)[-8:])

    def write(self, label, text, always=False):
        text = ANSI.sub("", str(text))
        text = "".join(c for c in text if c in "\n\t" or c.isprintable())
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        for line in text.splitlines():
            rendered = "[" + stamp + "][" + label + "] " + line
            self.log.write(rendered + "\n")
            if always or not self.quiet:
                print(rendered, flush=True)

    def notice(self, text):
        self.flush(force=True)
        self.write("os-goal", text, always=True)

    def delta(self, key, text):
        if not text:
            return
        self.streamed.add(key)
        previous, started = self.pending.get(key, ("", time.monotonic()))
        value = previous + text
        while "\n" in value or len(value) >= 4096:
            end = value.find("\n", 0, 4096)
            line, value = (value[:end], value[end + 1:]) if end >= 0 else (value[:4096], value[4096:])
            self.write(self.stream_label(key), line)
        self.pending[key] = (value, started)

    def flush(self, force=False, item=None):
        now = time.monotonic()
        for key, (value, started) in list(self.pending.items()):
            if item is not None and key[:2] != item:
                continue
            if force or now - started >= 0.25:
                if value:
                    self.write(self.stream_label(key), value)
                self.pending.pop(key, None)

    def stream_label(self, key):
        return self.label(key[0]) + "/" + key[2] + (":" + key[1][-8:] if key[2] == "output" else "")

    def snapshot(self):
        now = time.monotonic()
        return {thread: dict({k: v for k, v in row.items() if k != "seen"},
            label=self.label(thread), quiet_seconds=round(now - row["seen"], 1))
            for thread, row in self.agents.items()}

    def heartbeat(self, goal, active, uptime, worker_pid, server_pid):
        rows = self.snapshot()
        self.notice("HEARTBEAT alive; uptime=" + str(int(uptime)) + "s; worker_pid="
                    + str(worker_pid) + "; server_pid=" + str(server_pid)
                    + "; goal=" + str((goal or {}).get("status")) + "; " + str(len(active))
                    + " active agent(s); tokens=" + str((goal or {}).get("tokensUsed", "unknown")))
        for thread in active:
            row = rows.get(thread, {})
            quiet = row.get("quiet_seconds")
            warning = " POSSIBLY STALLED;" if quiet is not None and quiet >= 180 else ""
            self.write(self.label(thread), warning + " active; last event "
                       + (str(quiet) + "s ago" if quiet is not None else "unknown")
                       + "; " + row.get("activity", "waiting for events"), always=True)

    def event(self, message):
        method, data = message.get("method", ""), message.get("params", {})
        if method == "launcher/serverStderr":
            self.delta(("server", "stderr", "stderr"), data["delta"])
            return
        thread = data.get("threadId")
        if method == "thread/started":
            info = data["thread"]
            thread = info["id"]
        if thread and (method.startswith(("item/", "turn/")) or method in {
                "thread/started", "thread/status/changed", "error"}):
            row = self.agents.setdefault(thread, {"status": "unknown"})
            row.update(seen=time.monotonic(), last_event_at=datetime.now(timezone.utc).isoformat())
            if method.startswith(("item/", "turn/")):
                self.agent_event_count += 1
        else:
            row = None
        if method == "thread/started":
            if info.get("agentNickname"):
                row["name"] = info["agentNickname"]
        elif method in {"turn/started", "turn/completed"}:
            turn = data["turn"]
            row.update(turn_id=turn["id"], status=turn["status"])
            self.flush(force=True)
            self.write(self.label(thread), "Turn " + turn["status"] + " " + turn["id"])
            if turn.get("error"):
                self.write(self.label(thread), "ERROR: " + str(turn["error"]))
            if method == "turn/completed":
                self.streamed = {key for key in self.streamed if key[0] != thread}
        elif method == "thread/status/changed":
            row["status"] = data["status"]["type"]
            flags = data["status"].get("activeFlags") or []
            if flags:
                self.write(self.label(thread), "Waiting: " + ", ".join(flags))
        elif method in {"item/agentMessage/delta", "item/commandExecution/outputDelta"}:
            channel = "message" if method == "item/agentMessage/delta" else "output"
            self.delta((thread, data["itemId"], channel), data.get("delta", ""))
        elif method in {"item/started", "item/completed"}:
            item = data["item"]
            kind, ident = item["type"], item["id"]
            done = method == "item/completed"
            self.flush(force=True)
            if kind in {"agentMessage", "commandExecution"} and done:
                channel = "message" if kind == "agentMessage" else "output"
                key = (thread, ident, channel)
                if key not in self.streamed:
                    self.write(self.stream_label(key),
                               item.get("text" if channel == "message" else "aggregatedOutput") or "")
                self.streamed.discard(key)
            if kind == "agentMessage":
                description = "Speaking"
            elif kind == "reasoning":
                # Show activity without copying raw internal reasoning into the console.
                description = "Working"
            elif kind == "commandExecution":
                description = "Command: " + item["command"]
                if done:
                    description = "Command " + item["status"] + "; exit=" + str(item.get("exitCode"))
                    if item.get("durationMs") is not None:
                        description += "; duration=" + str(item["durationMs"]) + "ms"
                elif item.get("processId"):
                    description = "Command session=" + str(item["processId"]) + ": " + item["command"]
            elif kind == "fileChange":
                description = "Files " + item["status"] + ": " + ", ".join(c["path"] for c in item["changes"])
            elif kind == "subAgentActivity":
                child = item["agentThreadId"]
                child_row = self.agents.setdefault(child, {"seen": time.monotonic(), "status": "unknown"})
                child_row["name"] = item.get("agentPath") or self.label(child)
                description = "Agent " + self.label(child) + " " + item["kind"] + " (" + child + ")"
            elif kind in {"collabAgentToolCall", "collabToolCall", "mcpToolCall", "dynamicToolCall"}:
                description = "Tool " + item.get("tool", kind) + " " + item.get("status", "")
                if item.get("error"):
                    description += "; ERROR: " + str(item["error"])
                if item.get("success") is False:
                    description += "; FAILED"
            elif kind == "contextCompaction":
                description = "Context compaction " + ("completed" if done else "started")
            elif kind == "webSearch":
                description = "Search: " + item.get("query", "")
            else:
                description = kind + (" completed" if done else " started")
            if row is not None:
                row["activity"] = " ".join(description.split())[:240]
            if kind not in {"reasoning", "agentMessage", "userMessage"} or not done and kind == "reasoning":
                self.write(self.label(thread), description)
        elif method in {"error", "warning", "configWarning"}:
            self.flush(force=True)
            self.write(self.label(thread) if thread else "server", method.upper() + ": "
                       + str(data.get("error") or data.get("message") or data.get("summary")))
        elif "id" in message:
            self.write(self.label(thread), "Server request: " + method)

    def close(self):
        self.flush(force=True)
        self.log.close()
