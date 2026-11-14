"""STF1 host control coordinator. Collection metadata, never OS acceptance.

The caller owns the connected socket, QMP, capture validation and an independent
watchdog. A synchronous capture callback cannot be preempted here; a late return
is rejected before ACK. No socket, process, guest or QMP is created by this file.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import select
import socket
import time

MODES = frozenset(("prepublish-hard", "postpublish-notify",
                   "recoverable-backpressure", "permanent-backpressure"))
UART_LIMIT = 16384
FRAME_LIMIT = 512
EVENT_LIMIT = 1024 * 1024
CALLBACK_RECORD_LIMIT = 16384
_COMMON = (rb" (?P<nonce>[0-9a-f]{32}) (?P<sequence>[1-9][0-9]{0,9})"
           rb" (?P<phase>[A-Z][A-Z0-9_]{0,63}) (?P<mode>[a-z][a-z-]{0,31})"
           rb" (?P<tgid>[1-9][0-9]{0,9}) (?P<tid>[1-9][0-9]{0,9})"
           rb" (?P<start_ticks>[1-9][0-9]{0,19})")
_REQ = re.compile(rb"STF1 REQ" + _COMMON + rb"\n")
_FAIL = re.compile(rb"STF1 FAIL" + _COMMON +
                   rb" (?P<reason>[a-z][a-z0-9-]{0,79}) (?P<errno>0|[1-9][0-9]{0,3})\n")


class FaultControlError(Exception):
    """Invalid framing/state or failed collection; caller captures externally."""


def _seconds(value, maximum, name, allow_zero=False):
    if (type(value) not in (int, float) or not math.isfinite(value) or value > maximum or
            (value < 0 if allow_zero else value <= 0)):
        raise ValueError(name + " must be finite and within its declared bounds")
    return float(value)


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False, ensure_ascii=True) + "\n").encode("ascii")


def _bounded_result(value):
    budget, nodes = CALLBACK_RECORD_LIMIT, 256
    def visit(item, depth):
        nonlocal budget, nodes
        nodes -= 1
        if depth > 8 or nodes < 0:
            raise ValueError("capture callback metadata nesting/node bound")
        kind = type(item)
        if kind is dict:
            if len(item) > 64:
                raise ValueError("capture callback object bound")
            budget -= 2 + len(item) * 2
            for key, child in item.items():
                if type(key) is not str or len(key) > 128:
                    raise ValueError("capture callback key bound")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif kind is list:
            if len(item) > 64:
                raise ValueError("capture callback list bound")
            budget -= 2 + len(item)
            for child in item:
                visit(child, depth + 1)
        elif kind is str:
            if len(item) > 4096:
                raise ValueError("capture callback string bound")
            budget -= len(_json(item))
        elif kind in (int, float, bool) or item is None:
            if kind is int and item.bit_length() > 64 or kind is float and not math.isfinite(item):
                raise ValueError("capture callback numeric bound")
            budget -= len(_json(item))
        else:
            raise ValueError("capture callback requires plain JSON values")
        if budget < 0:
            raise ValueError("capture callback record exceeds bound")
    visit(value, 0)
    if len(_json(value)) > CALLBACK_RECORD_LIMIT:
        raise ValueError("capture callback record exceeds bound")


class FaultControl:
    """Poll one connected control socket until the caller observes guest exit.

    capture_phase receives a fresh parsed-request dict. It must return a plain
    dict with lowercase sha256 and continued is True only after retaining and
    checking the actual capture, continuing QMP, and verifying running. Its
    return is an assertion by the caller, not provenance verified by this class.
    A FAIL callback uses ack_phase=EMERGENCY_CAPTURED and may retain failing
    observations; the original failure is never cleared by successful capture.
    """

    def __init__(self, connection, *, nonce, mode, capture_root, capture_phase,
                 timeout_seconds=180, frame_timeout_seconds=5, capture_timeout_seconds=8):
        if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{32}", nonce) is None:
            raise ValueError("nonce must be exactly 32 lowercase hexadecimal characters")
        if type(mode) is not str or mode not in MODES or not callable(capture_phase):
            raise ValueError("known mode and callable capture_phase required")
        total = _seconds(timeout_seconds, 300, "timeout_seconds")
        self.frame_timeout = _seconds(frame_timeout_seconds, 15, "frame_timeout_seconds")
        self.capture_timeout = _seconds(capture_timeout_seconds, 10, "capture_timeout_seconds")
        self.connection = connection
        self.nonce, self.mode, self.capture_phase = nonce, mode, capture_phase
        self.normal_phases = ("PRE_INPUT", "POST_RET") + (() if mode == "recoverable-backpressure" else ("QUIET",))
        self.started = time.monotonic()
        self.deadline = self.started + total
        self.root = Path(capture_root)
        if not self.root.is_absolute() or self.root.name in ("", ".", ".."):
            raise ValueError("capture_root must name a fresh absolute directory")
        self.root.mkdir(mode=0o700)
        self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        self.fds = {}
        try:
            for name in ("rx.bin", "tx.bin", "events.jsonl"):
                self.fds[name] = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                                         0o600, dir_fd=self.root_fd)
            self.connection.setblocking(False)
        except BaseException:
            for fd in self.fds.values():
                os.close(fd)
            os.close(self.root_fd)
            raise
        self.rx_bytes = self.tx_bytes = self.event_bytes = self.rx_discarded = 0
        self.rx_received = self.tx_sent = 0
        self.rx_digest, self.tx_digest = hashlib.sha256(), hashlib.sha256()
        self.buffer = bytearray()
        self.partial_started = None
        self.identity = None
        self.sequence = self.normal_index = self.ack_count = self.callback_count = 0
        self.pending_phase = None
        self.first_failure = self.guest_failure = None
        self.awaiting_guest_failure = False
        self.protocol_failed = self.emergency_seen = self.emergency_confirmed = self.closed = False
        self.last_event = None
        self._event("coordinator-start", timeout_seconds=total,
                    frame_timeout_seconds=self.frame_timeout, capture_timeout_seconds=self.capture_timeout)

    def _write(self, name, data):
        view = memoryview(data)
        while view:
            try:
                count = os.write(self.fds[name], view)
            except InterruptedError:
                continue
            if count <= 0:
                raise OSError("short control artifact write")
            chunk = view[:count]
            if name == "rx.bin":
                self.rx_bytes += count
                self.rx_digest.update(chunk)
            elif name == "tx.bin":
                self.tx_bytes += count
                self.tx_digest.update(chunk)
            else:
                self.event_bytes += count
            view = view[count:]

    def _event(self, kind, **fields):
        row = {"event": kind, "monotonic_ns": time.monotonic_ns(), **fields}
        data = _json(row)
        if self.event_bytes + len(data) > EVENT_LIMIT:
            raise FaultControlError("event-byte-limit")
        self._write("events.jsonl", data)
        self.last_event = row
        return row

    def _failure(self, reason, **detail):
        if self.first_failure is None:
            self.first_failure = {"reason": reason, "monotonic_ns": time.monotonic_ns(), **detail}
            self._event("first-failure", failure=self.first_failure)

    def _reject(self, reason, **detail):
        self.protocol_failed = True
        self._failure(reason, **detail)
        self._event("protocol-rejected", reason=reason, **detail)
        raise FaultControlError(reason)

    def _check_time(self):
        current = time.monotonic()
        if current >= self.deadline:
            self._reject("control-deadline")
        if self.partial_started is not None and current >= self.partial_started + self.frame_timeout:
            self._reject("partial-frame-deadline")
        return current

    def _parse(self, frame):
        match = _REQ.fullmatch(frame)
        kind = "REQ"
        if match is None:
            match, kind = _FAIL.fullmatch(frame), "FAIL"
        if match is None:
            self._reject("malformed-frame")
        row = {name: value.decode("ascii") for name, value in match.groupdict().items()}
        row["kind"] = kind
        for name in ("sequence", "tgid", "tid", "start_ticks"):
            row[name] = int(row[name])
        if kind == "FAIL":
            row["errno"] = int(row["errno"])
            if row["errno"] > 4095:
                self._reject("failure-errno-range")
        if (row["sequence"] > 0xffffffff or row["tgid"] > 0x7fffffff or
                row["tid"] > 0x7fffffff or row["start_ticks"] > 0xffffffffffffffff):
            self._reject("identity-or-sequence-range")
        if row["nonce"] != self.nonce or row["mode"] != self.mode:
            self._reject("nonce-or-mode-mismatch")
        if row["sequence"] != self.sequence + 1:
            self._reject("sequence-mismatch")
        identity = (row["tgid"], row["tid"], row["start_ticks"])
        if self.identity is None:
            if kind != "REQ" or row["phase"] != "PRE_INPUT":
                self._reject("first-frame-must-be-PRE_INPUT")
        elif identity != self.identity:
            self._reject("owned-identity-mismatch")
        if self.emergency_seen:
            self._reject("frame-after-emergency")
        if kind == "REQ":
            if (self.awaiting_guest_failure or self.normal_index >= len(self.normal_phases) or
                    row["phase"] != self.normal_phases[self.normal_index]):
                self._reject("normal-phase-order")
        else:
            if self.normal_index == 0:
                self._reject("failure-before-input-release")
            if self.awaiting_guest_failure:
                allowed = {self.pending_phase}
            elif self.normal_index == 1:
                allowed = {"INPUT", "OBSERVE_RET", "POST_RET"}
                allowed |= ({"OWNER_RECOVERY", "NATURAL_COMPLETION"} if self.mode == "recoverable-backpressure"
                            else {"OWNER_TERMINAL"})
            elif self.normal_index == 2 and len(self.normal_phases) == 3:
                allowed = {"QUIET_INTERVAL", "OWNER_TERMINAL_PLUS_FIVE", "QUIET"}
            else:
                allowed = {"OWNED_CLEANUP", "NEW_ADMISSION"}
                if self.mode == "recoverable-backpressure":
                    allowed.add("NORMAL_COMPLETION")
            if row["phase"] not in allowed:
                self._reject("failure-phase-order")
        if self.identity is None:
            self.identity = identity
        self.sequence = row["sequence"]
        row["ack_phase"] = "EMERGENCY_CAPTURED" if kind == "FAIL" else row["phase"]
        return row

    def _ack(self, request, digest, capture_deadline):
        frame = ("STF1 ACK {nonce} {sequence} {ack_phase} {mode} {tgid} {tid} {start_ticks} "
                 .format(**request) + digest + " CONTINUED\n").encode("ascii")
        if self.tx_bytes + len(frame) > UART_LIMIT:
            self._reject("tx-byte-limit")
        while True:
            self._check_time()
            if time.monotonic() >= capture_deadline:
                self._reject("ack-deadline", bytes_sent=0)
            try:
                queued = self.connection.recv(1, socket.MSG_PEEK)
                break
            except InterruptedError:
                continue  # No queue/EOF observation was obtained yet.
            except BlockingIOError:
                queued = None
                break
        if queued == b"":
            self._reject("control-eof-before-ack")
        if queued:
            extra = self.connection.recv(4096)
            self._retain_rx(extra)
            self.buffer.extend(extra[:UART_LIMIT])
            self._reject("unsolicited-frame-before-ack")
        sent = 0
        while sent < len(frame):
            self._check_time()
            if time.monotonic() >= capture_deadline:
                self._reject("ack-deadline", bytes_sent=sent)
            try:
                count = self.connection.send(frame[sent:])
            except (BlockingIOError, InterruptedError):
                select.select([], [self.connection], [], min(0.02, max(0, capture_deadline - time.monotonic())))
                continue
            except OSError as exc:
                self._reject("ack-channel-error", error=str(exc)[:256], bytes_sent=sent)
            if count <= 0:
                self._reject("ack-channel-closed", bytes_sent=sent)
            self.tx_sent += count
            self._write("tx.bin", frame[sent:sent + count])
            sent += count
        if time.monotonic() >= min(self.deadline, capture_deadline):
            self._reject("late-ack-completion", bytes_sent=sent)
        self.ack_count += 1
        self._event("ack-written", sequence=request["sequence"], phase=request["ack_phase"],
                    bytes_sent=sent, sha256=digest, continued=True)

    def _handle(self, request):
        self.pending_phase = request["phase"]
        if request["kind"] == "FAIL":
            self.emergency_seen = True
            self.guest_failure = dict(request)
            self._failure("guest-collection-failure", request=dict(request))
        self.callback_count += 1
        started = time.monotonic()
        capture_deadline = min(self.deadline, started + self.capture_timeout)
        self._event("capture-call", request=dict(request))
        error = None
        result = None
        retained_result = None
        try:
            result = self.capture_phase(dict(request))
            if type(result) is not dict:
                raise ValueError("capture callback must return a plain dict")
            _bounded_result(result)
            result = json.loads(_json(result))
            retained_result = result
            if (type(result.get("sha256")) is not str or
                    re.fullmatch(r"[0-9a-f]{64}", result["sha256"]) is None or result.get("continued") is not True):
                raise ValueError("capture digest and literal continued True required")
        except Exception as exc:
            error = type(exc).__name__ + ":" + str(exc)[:256]
        finished = time.monotonic()
        if finished >= capture_deadline:
            error = "late-capture-callback"
        if error is not None:
            self._failure("capture-not-confirmed", phase=request["phase"], error=error)
            self.awaiting_guest_failure = request["kind"] == "REQ"
            return self._event("capture-rejected-no-ack", request=dict(request), error=error,
                               callback_result=retained_result,
                               awaiting_guest_failure=self.awaiting_guest_failure)
        self._event("capture-return", request=dict(request), result=result)
        self._ack(request, result["sha256"], capture_deadline)
        if request["kind"] == "FAIL":
            self.emergency_confirmed = True
            self.awaiting_guest_failure = False
        else:
            self.normal_index += 1
        return self._event("phase-collected", request=dict(request),
                           emergency_confirmed=self.emergency_confirmed,
                           normal_phases_complete=self.normal_index == len(self.normal_phases))

    def _retain_rx(self, data):
        self.rx_received += len(data)
        available = UART_LIMIT - self.rx_bytes
        self._write("rx.bin", data[:available])
        if len(data) > available:
            self.rx_discarded += len(data) - available
            self._reject("rx-byte-limit", discarded_bytes=self.rx_discarded)

    def poll(self, wait_seconds=0.1):
        """Handle at most one complete frame; None means no frame yet.

        Normal phase completion does not end polling: cleanup/admission can
        still produce FAIL. Malformed/stale/channel failures raise after raw
        retention; the caller must perform its independent emergency capture.
        """
        try:
            return self._poll(wait_seconds)
        except OSError as exc:
            self.protocol_failed = True
            if self.first_failure is None:
                self.first_failure = {"reason": "local-or-socket-io-error", "error": str(exc)[:256],
                                      "monotonic_ns": time.monotonic_ns()}
            # Storage may itself be failing. Caller retains this exception;
            # never fabricate a successful event write or send another ACK.
            raise FaultControlError("local-or-socket-io-error") from exc

    def _poll(self, wait_seconds):
        wait = _seconds(wait_seconds, 1, "wait_seconds", allow_zero=True)
        if self.closed or self.protocol_failed:
            raise FaultControlError("coordinator-closed-or-protocol-failed")
        current = self._check_time()
        if b"\n" not in self.buffer:
            limit = min(wait, self.deadline - current)
            if self.partial_started is not None:
                limit = min(limit, self.partial_started + self.frame_timeout - current)
            readable, _, _ = select.select([self.connection], [], [], max(0, limit))
            if not readable:
                self._check_time()
                return None
            try:
                data = self.connection.recv(4096)
            except (BlockingIOError, InterruptedError):
                self._check_time()
                return None
            except OSError as exc:
                self._reject("rx-channel-error", error=str(exc)[:256])
            if not data:
                self._reject("unexpected-control-eof")
            self._retain_rx(data)
            if not self.buffer:
                self.partial_started = time.monotonic()
            self.buffer.extend(data)
        self._check_time()
        newline = self.buffer.find(b"\n")
        if newline < 0:
            if len(self.buffer) >= FRAME_LIMIT:
                self._reject("frame-byte-limit")
            return None
        if newline + 1 > FRAME_LIMIT:
            self._reject("frame-byte-limit")
        # This request/ACK protocol permits no second request before ACK. A
        # queued duplicate or even partial next frame cannot qualify this one.
        if newline + 1 != len(self.buffer):
            self._reject("pipelined-or-repeated-frame")
        frame = bytes(self.buffer)
        self.buffer.clear()
        self.partial_started = None
        request = self._parse(frame)
        self._event("request-received", request=dict(request))
        return self._handle(request)

    def report(self):
        return {"schema_version": 1, "scope": "host-UART-capture-coordination-only",
                "nonce": self.nonce, "mode": self.mode, "identity": list(self.identity) if self.identity else None,
                "last_sequence": self.sequence, "normal_acks": self.normal_index, "ack_count": self.ack_count,
                "callback_count": self.callback_count, "normal_phases_complete": self.normal_index == len(self.normal_phases),
                "awaiting_guest_failure": self.awaiting_guest_failure, "protocol_failed": self.protocol_failed,
                "emergency_seen": self.emergency_seen, "emergency_capture_confirmed": self.emergency_confirmed,
                "first_failure": self.first_failure, "guest_failure": self.guest_failure,
                "rx_bytes": self.rx_bytes, "rx_sha256": self.rx_digest.hexdigest(), "rx_discarded_bytes": self.rx_discarded,
                "tx_bytes": self.tx_bytes, "tx_sha256": self.tx_digest.hexdigest(), "pending_frame_bytes": len(self.buffer),
                "socket_bytes_received": self.rx_received, "received_raw_fully_stored": self.rx_received == self.rx_bytes,
                "socket_bytes_sent": self.tx_sent, "sent_raw_fully_stored": self.tx_sent == self.tx_bytes,
                "application_acceptance": False, "transport_acceptance": False,
                "controller_exit_verified": False, "qmp_provenance_verified": False}

    def close(self):
        """Retain final report and close artifacts; connected socket stays owned by caller."""
        if self.closed:
            return
        self.closed = True
        try:
            data = _json(self.report())
            fd = os.open("report.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=self.root_fd)
            try:
                view = memoryview(data)
                while view:
                    count = os.write(fd, view)
                    if count <= 0:
                        raise OSError("short control report write")
                    view = view[count:]
                os.fsync(fd)
            finally:
                os.close(fd)
            for fd in self.fds.values():
                os.fsync(fd)
            os.fsync(self.root_fd)
        finally:
            for fd in self.fds.values():
                os.close(fd)
            os.close(self.root_fd)
