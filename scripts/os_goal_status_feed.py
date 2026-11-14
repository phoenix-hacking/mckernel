"""Refresh the derived public text view without changing campaign execution."""
from pathlib import Path
import re
import subprocess
import time

from os_goal_guard_protocol import atomic_json, process_start, read_json
from os_goal_mailbox_status import read_mailbox_status
from os_goal_stop_log import _text as redacted_text
from os_goal_status_publish import StatusPublisher
from os_goal_status_text import write_status_text


STATE_FILE = "status-text-state.json"
PUBLIC_URL = "https://github.com/phoenix-hacking/mckernel/blob/codex/mckernel-control-mailbox/status.txt"


class StatusFeed:
    def __init__(self, repo, directory, *, interval_seconds=600, publisher=None):
        self.repo, self.directory = Path(repo), Path(directory)
        self.interval = interval_seconds
        self.publisher = publisher if publisher is not None else StatusPublisher(directory, interval_seconds=interval_seconds)

    @staticmethod
    def _identity(pid, birth):
        return (type(pid) is int and pid > 0 and isinstance(birth, str) and birth.isdigit()
                and process_start(pid) == birth)

    def _snapshot(self, name, notes):
        try:
            if name == "mailbox-state.json":
                return read_mailbox_status(self.directory / name)
            return read_json(self.directory / name)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as error:
            notes.append(name + " is unavailable: " + type(error).__name__)
            return {}

    def _revision(self):
        result = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=5, check=False)
        value = result.stdout.strip()
        return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None

    def tick(self, context=None, *, publish=True):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        now, notes = time.time(), []
        prior = self._snapshot(STATE_FILE, notes)
        if publish and now < prior.get("next_refresh_at", 0):
            return dict(prior, status="BACKOFF")
        result = {"schema_version": 1, "url": PUBLIC_URL, "path": str(self.directory / "status.txt"),
                  "attempted_at": now, "next_refresh_at": now + self.interval if publish else prior.get("next_refresh_at", 0)}
        try:
            ledger = read_json(self.repo / "docs/verification/m14-m15-closure-progress.json")
            if isinstance(context, dict):
                state = context.get("engine_state")
                state = state if isinstance(state, dict) else {}
            else:
                state = self._snapshot("state.json", notes)
            guardian = ({key: value for key, value in context.items() if key != "engine_state"}
                        if isinstance(context, dict) else self._snapshot("guardian.json", notes))
            runtime = None
            if state or guardian:
                runtime = {"state": state, "guardian": guardian,
                           "watcher": self._snapshot("watcher.json", notes),
                           "mailbox": self._snapshot("mailbox-state.json", notes),
                           "latest_stop": self._snapshot("latest-stop.json", notes)}
            publication = self._snapshot("status-publish.json", notes)
            if publication.get("published_verified_at"):
                notes.append("Last verified publication before this rendering: " + str(publication["published_verified_at"]))
            if publication.get("last_error"):
                notes.append("Status publication needs attention: " + (redacted_text(publication["last_error"], 500) or "unknown"))
            notes.append("The progress ledger is the current working-tree snapshot; checkout HEAD does not assert it is committed or that a milestone is accepted.")
            rendered = write_status_text(self.directory / "status.txt", ledger,
                                         source_commit=self._revision(), runtime=runtime,
                                         generated_at=now, identity_checker=self._identity, notes=notes)
            result.update(status="GENERATED", generated_at=now, report=rendered)
            atomic_json(self.directory / STATE_FILE, result)
            if publish:
                outcome = self.publisher.publish(self.directory / "status.txt")
                result.update(status=outcome["status"], publication=outcome)
        except Exception as error:
            # A malformed telemetry input must not consume or block a mailbox
            # command that the independent control path already received.
            result.update(status="ERROR", reason=redacted_text(str(error), 500), error_type=type(error).__name__)
        atomic_json(self.directory / STATE_FILE, result)
        return result
