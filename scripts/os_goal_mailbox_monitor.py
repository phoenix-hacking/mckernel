"""Independent, singleton mailbox observer; never owns engine lifecycle authority.

The lifetime lease covers polling and derived publication. A process restart only
reopens the durable mailbox queue and receipts. SIGTERM stops this observer alone.
"""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import time
from uuid import uuid4

from os_goal_guard_protocol import atomic_json, lease_free, process_start, read_json
from os_goal_mailbox import Mailbox
from os_goal_status_feed import StatusFeed
from os_goal_stop_log import _text as redact


STATE_FILE = "mailbox-monitor.json"
LOCK_FILE = "mailbox-monitor.lock"


class ObserverDeadline(BaseException):
    """Whole-stage deadline that ordinary transport/telemetry catches cannot eat."""


@contextmanager
def bounded_stage(seconds):
    """Bound a complete synchronous stage, including locks and multiple API calls."""
    def expired(signum, frame):
        raise ObserverDeadline("Independent mailbox observer stage exceeded its deadline")
    previous = signal.signal(signal.SIGALRM, expired)
    prior_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *prior_timer)
        signal.signal(signal.SIGALRM, previous)


def legacy_poller(directory):
    """An already running pre-migration guardian must retain its polling lease."""
    if lease_free(directory, "guardian.lock"):
        return False
    try:
        guard = read_json(Path(directory) / "guardian.json")
    except FileNotFoundError:
        raise RuntimeError("Guardian lease is held without a readable poll-owner identity") from None
    if (not isinstance(guard.get("start"), str) or not guard["start"].isdigit()
            or process_start(guard.get("pid")) != guard["start"]):
        raise RuntimeError("Held guardian lease has no verified current poll-owner process identity")
    return guard.get("mailbox_poll_owner") != "independent"


def status_source(repo, directory, context):
    """Bind publication to the saved controller's actual working tree.

    Observer code and mailbox configuration may live in another worktree. One
    bounded Git read verifies that the ledger source belongs to this runtime;
    it never grants engine, account, resource or source execution authority.
    """
    if context.get("controller_state_present") is False:
        source, mode = Path(repo), "OBSERVER_CHECKOUT_NO_CONTROLLER"
    elif context.get("controller_state_present") is True:
        saved = context.get("engine_state")
        value = saved.get("repo") if isinstance(saved, dict) else None
        if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
            raise ValueError("Saved controller checkout is unknown; status publication withheld")
        source, mode = Path(value), "SAVED_CONTROLLER_WORKTREE"
    else:
        raise ValueError("Controller source snapshot is unknown; status publication withheld")
    source = source.resolve()
    if not source.is_dir():
        raise ValueError("Status source checkout is unavailable; status publication withheld")
    result = subprocess.run(["git", "-C", str(source), "rev-parse", "--path-format=absolute",
                             "--show-toplevel", "--git-common-dir"],
                            capture_output=True, text=True, timeout=5, check=False)
    paths = result.stdout.splitlines()
    if (result.returncode or len(paths) != 2 or Path(paths[0]).resolve() != source
            or (Path(paths[1]) / "os-autopilot").resolve() != Path(directory).resolve()):
        raise ValueError("Status source does not match this runtime Git common directory; publication withheld")
    return {"mode": mode, "repo": str(source), "live_source_verified": False}


class MailboxMonitor:
    def __init__(self, repo, directory, *, mailbox=None, feed=None, heartbeat=None):
        self.repo, self.directory = Path(repo), Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.fd = os.open(self.directory / LOCK_FILE, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if legacy_poller(self.directory):
                raise RuntimeError("A legacy guardian still owns network polling; restart it through the normal explicit service transition first")
            self.mailbox = mailbox if mailbox is not None else Mailbox(
                self.repo, self.directory, self.repo / "scripts/os_goal_mailbox.json")
            # Resolve the source lazily so a publication binding failure cannot
            # disable authenticated instruction reception.
            self.feed = feed
            if heartbeat is None:
                from os_goal_guardian import sd_notify
                heartbeat = sd_notify
            self.heartbeat = heartbeat
            birth = process_start(os.getpid())
            if not isinstance(birth, str) or not birth.isdigit():
                raise RuntimeError("Mailbox observer process identity unavailable")
            self.snapshot = {"schema_version": 1, "monitor_id": uuid4().hex,
                             "pid": os.getpid(), "start": birth, "started_at": time.time(),
                             "phase": "STARTING", "poll_error": None, "publication_error": None}
            self.stopping = False
            self._save()
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise

    def _save(self, **fields):
        self.snapshot.update(fields, heartbeat_at=time.time())
        atomic_json(self.directory / STATE_FILE, self.snapshot)

    @staticmethod
    def _error(error):
        return {"type": type(error).__name__, "reason": redact(str(error), 500), "at": time.time()}

    def _publish(self, context):
        if self.feed is not None:
            return self.feed.tick(context)
        source = status_source(self.repo, self.directory, context)
        self._save(publication_source=source)
        return StatusFeed(Path(source["repo"]), self.directory).tick(
            dict(context, publication_source=source))

    def tick(self):
        """Poll and publish independently; neither failure changes engine controls."""
        if legacy_poller(self.directory):
            self._save(phase="BLOCKED", poll_error={"type": "LegacyPoller", "at": time.time(),
                       "reason": "A legacy guardian owns network polling"})
            self.heartbeat("Mailbox observer blocked by legacy poll owner")
            return dict(self.snapshot)
        self._save(phase="POLLING")
        self.heartbeat("Independent mailbox observer polling")
        context = {"observer": dict(self.snapshot)}
        try:
            snapshots, notes = {}, []
            for name in ("state.json", "guardian.json"):
                try:
                    snapshots[name] = read_json(self.directory / name)
                    if name == "state.json":
                        context["controller_state_present"] = True
                except FileNotFoundError:
                    snapshots[name] = {}
                    if name == "state.json":
                        context["controller_state_present"] = False
                except (OSError, ValueError) as error:
                    snapshots[name] = {}
                    if name == "state.json":
                        context["controller_state_present"] = True
                    notes.append(name + ": " + type(error).__name__)
            state, guard = snapshots["state.json"], snapshots["guardian.json"]
            live_guard = (isinstance(guard.get("start"), str) and guard["start"].isdigit()
                          and process_start(guard.get("pid")) == guard["start"]
                          and not lease_free(self.directory, "guardian.lock"))
            context.update(engine_state=state, guardian=guard,
                           status=guard.get("phase") if live_guard else
                           "MANUAL" if state.get("supervision_mode") == "manual" else "UNVERIFIED",
                           reason=guard.get("reason") if live_guard else state.get("stop_reason"))
            self._save(metadata_issues=notes)
            with bounded_stage(50):
                reply = self.mailbox.poll(context)
            self._save(last_poll_result=reply.get("status"),
                       poll_error={"type": "MailboxPollError", "reason": redact(reply.get("reason"), 500),
                                   "at": time.time()} if reply.get("status") == "ERROR" else None)
        except (Exception, ObserverDeadline) as error:
            self._save(poll_error=self._error(error))
        self.heartbeat("Independent mailbox observer checked; refreshing public status")
        if not self.stopping:
            self._save(phase="PUBLISHING")
            try:
                with bounded_stage(25):
                    publication = self._publish(context)
                self._save(last_publication_result=publication.get("status"),
                           publication_error={"type": "StatusFeedError", "at": time.time(),
                               "reason": redact(publication.get("reason") or publication.get("publication", {}).get("last_error"), 500)}
                           if publication.get("status") == "ERROR" else None)
            except (Exception, ObserverDeadline) as error:
                self._save(last_publication_result="ERROR", publication_source={"mode": "UNKNOWN"},
                           publication_error=self._error(error))
        self._save(phase="MONITORING")
        self.heartbeat("Independent mailbox observer monitoring")
        return dict(self.snapshot)

    def run(self, interval=10):
        previous = {}
        def stop(signum, frame):
            self.stopping = True
        try:
            for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                previous[signum] = signal.signal(signum, stop)
            while not self.stopping:
                self.tick()
                deadline = time.monotonic() + interval
                while not self.stopping and time.monotonic() < deadline:
                    time.sleep(min(0.25, max(0, deadline - time.monotonic())))
        finally:
            self._save(phase="STOPPED")
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        return 0

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
