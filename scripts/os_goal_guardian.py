"""Independent supervisor guardian and mailbox loop; engine runs in another unit."""
from datetime import datetime, timezone
import fcntl
import math
import os
from pathlib import Path
import signal
import socket
import time
from uuid import uuid4

from os_goal_guard_protocol import (atomic_json, goal_digest, lease_free, process_start,
                                    read_json, recovery_blocker, signal_exact, validate_recovery_proof,
                                    EngineLaunchDeferred)
from os_goal_stop_log import write_stop_record, _text as bounded_diagnostic


def authorize_start(directory, *, request_id=None, source="explicit_user", authored_at=None):
    """Called only by an actual user start or a verified mailbox /resume action."""
    directory = Path(directory)
    inbox = directory / "guardian-intents"
    inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    request_id = request_id or uuid4().hex
    if not isinstance(request_id, str) or not 0 < len(request_id) <= 512:
        raise ValueError("Invalid explicit start identity")
    if source == "verified_mailbox_resume" and authored_at is None:
        raise ValueError("Verified mailbox resume requires its original server comment timestamp")
    authored_at = time.time() if authored_at is None else authored_at
    if (type(authored_at) not in (int, float) or not math.isfinite(authored_at)
            or authored_at <= 0 or authored_at > time.time() + 60):
        raise ValueError("Invalid original instruction timestamp")
    path = inbox / (goal_digest(request_id) + ".json")
    if path.exists():
        return read_json(path)
    intent = {"request_id": request_id, "source": source, "status": "pending", "created_at": time.time(),
              "authored_at": authored_at}
    # A per-intent exclusive file makes a repeated mailbox resume idempotent.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        import json
        with os.fdopen(fd, "w") as stream:
            json.dump(intent, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise  # Incomplete intent remains UNKNOWN, never an automatic start.
    return intent


def request_stop(directory, *, request_id=None):
    """An actual user stop pauses the engine while the mailbox remains alive."""
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    value = {"request_id": request_id or uuid4().hex, "created_at": time.time(), "status": "pending"}
    atomic_json(directory / "guardian-stop.json", value)
    return value


def sd_notify(status):
    destination = os.environ.get("NOTIFY_SOCKET")
    if not destination:
        return
    if destination.startswith("@"):
        destination = "\0" + destination[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
        connection.sendto(("READY=1\nWATCHDOG=1\nSTATUS=" + status[:200]).encode(), destination)


class Guardian:
    def __init__(self, repo, directory, *, launch_engine, mailbox_poll=None, mailbox_ack=None,
                 heartbeat=None, stale_seconds=90, checkpoint_grace=660):
        self.repo, self.directory = Path(repo), Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.fd = os.open(self.directory / "guardian.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.fd)
            raise
        self.launch_engine, self.mailbox_poll, self.mailbox_ack = launch_engine, mailbox_poll, mailbox_ack
        self.heartbeat = heartbeat or sd_notify
        self.stale_seconds, self.checkpoint_grace = stale_seconds, checkpoint_grace
        self.stopping = False
        self.guard = self._optional("guardian.json")
        self.guard.update(run_id=self.guard.get("run_id") or uuid4().hex,
                          pid=os.getpid(), start=process_start(os.getpid()), started_at=time.time())
        if not isinstance(self.guard["start"], str) or not self.guard["start"].isdigit():
            self.close()
            raise RuntimeError("Guardian process identity unavailable")
        self._save()

    def _optional(self, name):
        try:
            return read_json(self.directory / name)
        except FileNotFoundError:
            return {}

    def _save(self, **values):
        self.guard.update(values, heartbeat_at=time.time())
        atomic_json(self.directory / "guardian.json", self.guard)

    def _hold(self, reason, state):
        if self.guard.get("reason") != reason or self.guard.get("phase") != "HELD":
            write_stop_record(self.directory, state, event="guardian_held", reason=reason)
        self._save(phase="HELD", reason=reason)

    def _launch(self, proof=None, intent_path=None):
        receipt = {"status": "sending", "submitted_at": time.time(), "proof_path": str(proof) if proof else None}
        if intent_path:
            intent = read_json(intent_path)
            atomic_json(intent_path, dict(intent, status="sending"))
            receipt["request_id"] = intent["request_id"]
        self._save(launch=receipt, phase="STARTING", reason=None)
        try:
            outcome = self.launch_engine(proof)
            receipt.update(status="submitted", outcome=outcome if isinstance(outcome, dict) else {})
            self._save(launch=receipt)
            if intent_path:
                atomic_json(intent_path, dict(intent, status="submitted"))
            return True
        except EngineLaunchDeferred:
            if intent_path:
                atomic_json(intent_path, dict(intent, status="pending", deferred_at=intent.get("deferred_at", time.time())))
            self._save(launch=None, phase="WAITING", reason="engine_service_retiring")
            return False
        except Exception as error:
            # Launch acknowledgement can be lost after service acceptance.
            self._save(launch=dict(receipt, status="delivery_uncertain", error_type=type(error).__name__))
            write_stop_record(self.directory, {}, event="guardian_engine_launch_failed",
                              reason="rpc_delivery_uncertain", error=error)
            self._hold("engine_launch_delivery_uncertain", {})
            return True  # Actual/uncertain submission must never be retried.

    def _intent(self, state, watcher):
        for path in sorted((self.directory / "guardian-intents").glob("*.json")):
            intent = read_json(path)
            if intent.get("status") != "pending":
                continue
            if intent.get("deferred_at") and time.time() - intent["deferred_at"] > self.checkpoint_grace:
                atomic_json(path, dict(intent, status="held", reason="engine_service_retiring_timeout"))
                self._hold("engine_service_retiring_timeout", state)
                return True
            stopped = self.guard.get("user_stop")
            if stopped and intent.get("authored_at", intent.get("created_at", 0)) <= stopped["created_at"]:
                atomic_json(path, dict(intent, status="cancelled_by_user_stop"))
                continue
            blocker = recovery_blocker(state, explicit_user=True)
            if blocker:
                atomic_json(path, dict(intent, status="held", reason=blocker))
                self._hold(blocker, state)
                return True
            if watcher and watcher.get("guardian_run_id") == self.guard["run_id"] and process_start(watcher.get("watcher_pid")) == watcher.get("watcher_start"):
                if stopped:
                    self._hold("user_stop_checkpoint_still_in_progress", state)
                    return True
                atomic_json(path, dict(intent, status="already_supervised"))
                return False  # Existing live engine consumes the queued reply.
            if not lease_free(self.directory, "watch.lock") or not lease_free(self.directory, "run.lock"):
                self._hold("existing_model_owner_requires_reconciliation", state)
                return True
            for name in ("worker", "server"):
                if state.get(name + "_pid") is not None and process_start(state[name + "_pid"]) is not None:
                    self._hold("existing_model_process_requires_reconciliation", state)
                    return True
            self._save(user_stop=None, checkpoint=None, watcher_retirement=None)
            self._launch(intent_path=path)
            return True
        return False

    def _user_stop(self, state, watcher):
        control = self._optional("guardian-stop.json")
        if control.get("status") != "pending":
            return
        self._save(user_stop=control, checkpoint=None)
        # Persist intent before signalling. An uncertain signal is not replayed.
        atomic_json(self.directory / "guardian-stop.json", dict(control, status="sending"))
        if watcher.get("guardian_run_id") == self.guard["run_id"]:
            birth = process_start(watcher.get("watcher_pid"))
            if birth == watcher.get("watcher_start") and isinstance(birth, str) and birth.isdigit():
                signal_exact(watcher["watcher_pid"], birth, signal.SIGTERM)
                atomic_json(self.directory / "guardian-stop.json", dict(control, status="submitted"))
                return
            if birth is not None:
                self._hold("user_stop_supervisor_identity_unknown", state)
                return
        if state.get("guardian_run_id") == self.guard["run_id"]:
            birth = process_start(state.get("worker_pid"))
            if birth == state.get("worker_start") and isinstance(birth, str) and birth.isdigit():
                signal_exact(state["worker_pid"], birth, signal.SIGTERM)
        atomic_json(self.directory / "guardian-stop.json", dict(control, status="submitted"))

    def _request(self, watcher, state):
        request = {"request_id": uuid4().hex, "run_id": self.guard["run_id"],
                   "guardian_pid": self.guard["pid"], "guardian_start": self.guard["start"],
                   "worker_pid": state["worker_pid"], "worker_start": state["worker_start"],
                   "watcher_pid": watcher["watcher_pid"], "watcher_start": watcher["watcher_start"],
                   "thread_id": state.get("thread_id"), "log_dir": state.get("log_dir"),
                   "reason": "supervisor_unavailable", "requested_at": time.time(),
                   "expires_at": time.time() + self.checkpoint_grace}
        atomic_json(self.directory / "guardian-checkpoint.json", request)
        self._save(checkpoint=request, phase="CHECKPOINTING", reason="supervisor_unavailable")
        signal_exact(request["worker_pid"], request["worker_start"], signal.SIGUSR1)

    def _recover(self, state):
        request = self.guard["checkpoint"]
        blocker = recovery_blocker(state)
        if blocker:
            self._hold(blocker, state)
            return
        if time.time() - request["requested_at"] > self.checkpoint_grace:
            self._hold("supervisor_recovery_deadline_expired", state)
            return
        worker_birth = process_start(request["worker_pid"])
        if worker_birth is not None:
            if worker_birth != request["worker_start"] or time.time() - request["requested_at"] > self.checkpoint_grace:
                self._hold("worker_checkpoint_unreconciled", state)
            elif (request["guardian_pid"], request["guardian_start"]) != (self.guard["pid"], self.guard["start"]):
                # Same logical request after guardian service recovery. The worker
                # treats this exact checkpoint request idempotently; no RPC replay.
                request = dict(request, guardian_pid=self.guard["pid"], guardian_start=self.guard["start"])
                atomic_json(self.directory / "guardian-checkpoint.json", request)
                self._save(checkpoint=request)
                signal_exact(request["worker_pid"], request["worker_start"], signal.SIGUSR1)
            return
        final = state.get("guardian_checkpoint") or {}
        if (state.get("phase") != "stopped" or state.get("stop_reason") != "guardian_recovery"
                or final.get("request_id") != request["request_id"] or final.get("run_id") != self.guard["run_id"]
                or final.get("worker_pid") != request["worker_pid"] or final.get("worker_start") != request["worker_start"]
                or state.get("worker_pid") != request["worker_pid"] or state.get("worker_start") != request["worker_start"]
                or state.get("active_turns") or state.get("stop_errors") or state.get("server_close_errors")
                or (state.get("goal") or {}).get("status") != "paused"):
            self._hold("worker_final_checkpoint_missing_or_incomplete", state)
            return
        if state.get("server_pid") is not None and process_start(state["server_pid"]) is not None:
            self._hold("model_server_retirement_unreconciled", state)
            return
        watcher_birth = process_start(request["watcher_pid"])
        if watcher_birth is not None:
            if watcher_birth != request["watcher_start"]:
                self._hold("supervisor_identity_unreconciled", state)
                return
            retirement = self.guard.get("watcher_retirement")
            if retirement is None:
                self._save(watcher_retirement={"at": time.time(), "signal": "SIGTERM"})
                signal_exact(request["watcher_pid"], watcher_birth, signal.SIGTERM)
            elif time.time() - retirement["at"] > 20 and retirement["signal"] == "SIGTERM":
                self._save(watcher_retirement={"at": time.time(), "signal": "SIGKILL"})
                signal_exact(request["watcher_pid"], watcher_birth, signal.SIGKILL)
            return
        if not lease_free(self.directory, "watch.lock") or not lease_free(self.directory, "run.lock"):
            self._hold("retired_model_lease_still_owned", state)
            return
        proof = dict(request, guardian_pid=self.guard["pid"], guardian_start=self.guard["start"],
                     state_sha256=goal_digest(state), goal_after=state["goal"], goal_sha256=goal_digest(state["goal"]))
        path = self.directory / ("guardian-recovery-" + request["request_id"] + ".json")
        atomic_json(path, proof)
        validate_recovery_proof(self.directory, path, self.guard["run_id"])
        if self._launch(path):
            self._save(checkpoint=None, watcher_retirement=None)

    def tick(self):
        """One bounded health/mailbox cycle. It never replays an uncertain launch."""
        state, watcher = {}, {}
        try:
            metadata_error = None
            try:
                state, watcher = self._optional("state.json"), self._optional("watcher.json")
            except Exception as error:
                metadata_error = type(error).__name__
            if self.mailbox_poll:
                try:
                    reply = self.mailbox_poll(self.directory, dict(self.guard, engine_state=state)) or {}
                    if reply.get("status") == "ERROR":
                        self._save(mailbox_error={"type": "MailboxPollError", "at": time.time(),
                                                 "reason": bounded_diagnostic(reply.get("reason"), 500)})
                    elif reply.get("status") == "POLLED":
                        self._save(mailbox_error=None)
                    if reply.get("resume_request_id"):
                        ident = reply["resume_request_id"]
                        authorize_start(self.directory, request_id=ident, source="verified_mailbox_resume",
                                        authored_at=reply.get("resume_created_at"))
                        if self.mailbox_ack:
                            self.mailbox_ack(ident)
                except Exception as error:
                    self._save(mailbox_error={"type": type(error).__name__, "at": time.time(),
                                             "reason": bounded_diagnostic(str(error), 500)})
            # Bound each watchdog segment independently: mailbox/network first,
            # then service launch or ownership reconciliation.
            self.heartbeat(self.guard.get("phase", "monitoring"))
            if self.stopping == "requested" and not self.guard.get("user_stop"):
                request_stop(self.directory)
            if metadata_error:
                self._hold("engine_metadata_unreadable_" + metadata_error, state)
                return dict(self.guard)
            self._user_stop(state, watcher)
            if self._intent(state, watcher):
                return dict(self.guard)
            if self.guard.get("user_stop"):
                self._hold("user_requested", state)
                return dict(self.guard)
            if self.guard.get("checkpoint"):
                self._recover(state)
                return dict(self.guard)
            same_run = watcher.get("guardian_run_id") == self.guard["run_id"] and state.get("guardian_run_id") == self.guard["run_id"]
            birth = process_start(watcher.get("watcher_pid")) if watcher else None
            if same_run and birth == watcher.get("watcher_start") and isinstance(birth, str) and birth.isdigit():
                age = time.time() - watcher.get("at", 0)
                if 0 <= age <= self.stale_seconds:
                    self._save(phase="SUPERVISED", reason=None, launch=None)
                    return dict(self.guard)
            launch = self.guard.get("launch")
            if launch:
                if launch.get("status") == "submitted" and time.time() - launch["submitted_at"] < self.stale_seconds:
                    return dict(self.guard)
                self._hold("engine_start_unreconciled", state)
                return dict(self.guard)
            blocker = recovery_blocker(state)
            if blocker or not same_run or (state.get("goal") or {}).get("status") != "active":
                self._hold(blocker or "engine_stopped_or_waiting_for_explicit_input", state)
                return dict(self.guard)
            if process_start(state.get("worker_pid")) != state.get("worker_start"):
                self._hold("supervisor_and_worker_outcomes_unreconciled", state)
                return dict(self.guard)
            self._request(watcher, state)
        except Exception as error:
            # Mailbox faults and uncertain ownership do not terminate monitoring.
            self._hold("guardian_cycle_" + type(error).__name__, state)
        finally:
            self._save()
            self.heartbeat(self.guard.get("phase", "monitoring"))
        return dict(self.guard)

    def run(self, interval=10):
        previous = {}
        exit_at = None
        def stop(signum, frame):
            self.stopping = "requested"
        try:
            for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                previous[signum] = signal.signal(signum, stop)
            self.heartbeat("starting guardian health and mailbox monitoring")
            while True:
                if self.stopping == "requested" and exit_at is None:
                    request_stop(self.directory)
                    exit_at = time.monotonic() + self.checkpoint_grace
                self.tick()
                if exit_at is not None:
                    state = self._optional("state.json")
                    worker = state.get("worker_pid")
                    if worker is None or process_start(worker) is None or time.monotonic() >= exit_at:
                        break
                until = time.monotonic() + interval
                while time.monotonic() < until:
                    time.sleep(min(0.25, max(0, until - time.monotonic())))
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
            self.close()

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
