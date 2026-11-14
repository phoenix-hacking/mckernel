"""Bounded QMP transactions and live-guest pause/resume for verification.

This module collects control evidence. It never awards application acceptance.
The caller retains transcript.json, raw captures and any original exception.
"""
from contextlib import contextmanager
import json
import math
import socket
import time


class QmpError(RuntimeError):
    pass


class QmpResumeError(QmpError):
    pass


def _decode(raw):
    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            raise QmpError("nonfinite QMP numeric literal")
        return value
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise QmpError("duplicate QMP JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_float=finite_float,
                           parse_constant=lambda value: (_ for _ in ()).throw(QmpError("nonfinite QMP value")))
    except (UnicodeError, ValueError) as error:
        raise QmpError("invalid QMP JSON") from error
    if type(value) is not dict:
        raise QmpError("QMP message must be an object")
    return value


class QmpSession:
    def __init__(self, connection, timeout_seconds=5.0, frame_limit=1024 * 1024,
                 transcript_limit=8 * 1024 * 1024):
        if (type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 30
                or type(frame_limit) is not int or not 256 <= frame_limit <= 1024 * 1024):
            raise ValueError("invalid QMP limits")
        if type(transcript_limit) is not int or not frame_limit <= transcript_limit <= 16 * 1024 * 1024:
            raise ValueError("invalid transcript limit")
        self.connection = connection
        self.timeout = float(timeout_seconds)
        self.frame_limit = frame_limit
        self.transcript_limit = transcript_limit
        self.buffer = bytearray()
        self.sequence = 0
        self.events = []
        self.transcript = []
        self.transcript_bytes = 0
        self.recovery = []
        self.recovering = False
        self.capture_deadline = None
        self.pending_replies = set()
        self.stale_recovery_replies = []

    @classmethod
    def connect(cls, path, timeout_seconds=5.0):
        if type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 30:
            raise ValueError("invalid QMP connection timeout")
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.settimeout(timeout_seconds)
            connection.connect(str(path))
            session = cls(connection, timeout_seconds)
            greeting = session._receive(time.monotonic() + session.timeout)
            if "QMP" not in greeting:
                raise QmpError("missing QMP greeting")
            session.execute("qmp_capabilities")
            return session
        except BaseException:
            connection.close()
            raise

    def _retain(self, direction, raw):
        self.transcript_bytes += len(raw)
        # Reserve bounded recording space for cont/query-status even when the
        # ordinary capture reaches its transcript cap. Retain the offending
        # read before failing, rather than losing the last received bytes.
        if self.transcript_bytes > self.transcript_limit + 2 * 1024 * 1024:
            raise QmpError("QMP transcript limit exceeded")
        self.transcript.append({"direction": direction, "monotonic": time.monotonic(),
                                "raw_hex": raw.hex()})
        if not self.recovering and self.transcript_bytes > self.transcript_limit:
            raise QmpError("QMP ordinary transcript budget exceeded")

    def _remaining(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise QmpError("QMP transaction deadline")
        self.connection.settimeout(remaining)

    def _receive(self, deadline):
        while True:
            end = self.buffer.find(b"\n")
            if end >= 0:
                if end + 1 > self.frame_limit:
                    raise QmpError("QMP frame limit exceeded")
                raw = bytes(self.buffer[:end + 1])
                del self.buffer[:end + 1]
                return _decode(raw)
            if len(self.buffer) >= self.frame_limit:
                raise QmpError("QMP frame limit exceeded")
            self._remaining(deadline)
            try:
                raw = self.connection.recv(min(65536, self.frame_limit - len(self.buffer)))
            except (OSError, TimeoutError) as error:
                raise QmpError("QMP read failed or timed out") from error
            if not raw:
                raise QmpError("QMP disconnected with incomplete response")
            self.buffer.extend(raw)
            self._retain("received", raw)

    def execute(self, command, arguments=None):
        self.sequence += 1
        request = {"execute": command, "id": self.sequence}
        if arguments is not None:
            request["arguments"] = arguments
        raw = (json.dumps(request, allow_nan=False, separators=(",", ":")) + "\n").encode()
        if len(raw) > self.frame_limit:
            raise QmpError("QMP request limit exceeded")
        deadline = time.monotonic() + self.timeout
        if not self.recovering and self.capture_deadline is not None:
            deadline = min(deadline, self.capture_deadline)
        self._remaining(deadline)
        self._retain("sent", raw)
        self.pending_replies.add(self.sequence)
        try:
            self.connection.sendall(raw)
        except (OSError, TimeoutError) as error:
            raise QmpError("QMP send failed or timed out") from error
        for _ in range(129):
            message = self._receive(deadline)
            if "event" in message and "id" not in message:
                if len(self.events) >= 128:
                    raise QmpError("QMP event limit exceeded")
                self.events.append(message)
                continue
            response_id = message.get("id")
            if (self.recovering and type(response_id) is int and response_id < self.sequence
                    and response_id in self.pending_replies):
                if len(self.stale_recovery_replies) >= 8:
                    raise QmpError("too many stale replies during QMP recovery")
                self.pending_replies.remove(response_id)
                self.stale_recovery_replies.append(message)
                continue
            if type(response_id) is not int or response_id != self.sequence:
                raise QmpError("QMP reply identity mismatch")
            self.pending_replies.discard(response_id)
            if "error" in message:
                raise QmpError("QMP command rejected: " + json.dumps(message["error"]))
            if "return" not in message:
                raise QmpError("QMP reply has no result")
            if time.monotonic() > deadline:
                raise QmpError("QMP completion observed after deadline")
            return message["return"]
        raise QmpError("too many QMP events before reply")

    @contextmanager
    def paused(self, timeout_seconds=10.0):
        """Always attempt and verify resume, including failed stop/capture paths."""
        if not 0 < timeout_seconds <= 20 or self.capture_deadline is not None:
            raise ValueError("invalid or nested QMP capture")
        self.capture_deadline = time.monotonic() + timeout_seconds
        original = None
        row = {"started_monotonic": time.monotonic(), "resume_verified": False}
        self.recovery.append(row)
        try:
            self.execute("stop")
            state = self.execute("query-status")
            if state.get("status") != "paused" or state.get("running") is not False:
                raise QmpError("QMP did not confirm pause")
            row["pause_confirmed_monotonic"] = time.monotonic()
            yield
            if time.monotonic() > self.capture_deadline:
                raise QmpError("QMP capture body exceeded deadline")
        except BaseException as error:
            original = error
            row["original_error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            self.recovering = True
            recovery_errors = []
            try:
                try:
                    self.execute("cont")
                except BaseException as error:
                    recovery_errors.append(error)
                    row["continue_error"] = {"type": type(error).__name__, "message": str(error)}
                # Independently query even after a rejected or lost cont reply.
                # Only this request's exact ID can confirm resumed execution.
                try:
                    state = self.execute("query-status")
                    if state.get("status") != "running" or state.get("running") is not True:
                        raise QmpError("QMP did not confirm resumed execution")
                    row["resume_verified"] = True
                except BaseException as error:
                    recovery_errors.append(error)
                    row["status_error"] = {"type": type(error).__name__, "message": str(error)}
                if recovery_errors:
                    row["resume_error"] = [{"type": type(error).__name__, "message": str(error)}
                                           for error in recovery_errors]
                    raise QmpResumeError("guest recovery had control errors; capture cannot be acknowledged") from (original or recovery_errors[0])
            finally:
                row["finished_monotonic"] = time.monotonic()
                self.recovering = False
                self.capture_deadline = None

    def close(self):
        self.connection.close()
