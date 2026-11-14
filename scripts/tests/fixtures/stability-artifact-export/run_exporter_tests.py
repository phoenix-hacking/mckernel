#!/usr/bin/env python3
"""Pinned-container actual C exporter / raw PTY / receiver infrastructure tests.

No McKernel, guest, application payload or production acceptance. Each worker
owns one ordinary exporter child. The reviewed supervisor owns worker cleanup.
All successful and failed fixtures, streams and protocol bytes are retained.
"""
import argparse
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import socket
import stat
import struct
import sys
import termios
import time
import tty

HERE = Path(__file__).resolve().parent
RECEIVER_SHA = "aa9e165044e9567c992a0354dacdc49b884794b31841a3871d977eeae9c8c5d9"
SUPERVISOR_SHA = "8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873"
EXPORTER_SOURCE_SHA = "af85d0c692a1df677c2df7c9cbb5ee85fcf8b7dc31d2b14527675a3dc903fb6c"
CASES = ("binary", "empty", "symlink", "hardlink", "fifo", "entry-limit", "content-limit",
         "ack-magic", "ack-nonce", "ack-count", "ack-status", "ack-short", "disconnect", "ack-missing")
WIRE_LIMIT = 17 * 1024 * 1024 + 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def retain_json(path, value):
    with Path(path).open("x", encoding="ascii") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def read_regular(path, limit=32 * 1024 * 1024):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, "input type/size: " + str(path))
        chunks, size = [], 0
        while True:
            data = os.read(fd, min(65536, limit + 1 - size))
            if not data:
                break
            chunks.append(data)
            size += len(data)
            require(size <= limit, "input grew: " + str(path))
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "input changed")
        return b"".join(chunks)
    finally:
        os.close(fd)


def identity(path):
    data = read_regular(path)
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def import_source(name, path, expected):
    require(identity(path)["sha256"] == expected, "reviewed Python source mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "source import unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class WireLog:
    def __init__(self, path, limit):
        self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        self.limit = limit
        self.count = 0
        self.digest = hashlib.sha256()

    def append(self, data):
        require(self.count + len(data) <= self.limit, "PTY protocol evidence cap")
        view = memoryview(data)
        while view:
            try:
                count = os.write(self.fd, view)
            except InterruptedError:
                continue
            require(count > 0, "short PTY evidence write")
            self.digest.update(view[:count])
            self.count += count
            view = view[count:]

    def close(self):
        if self.fd >= 0:
            os.fsync(self.fd)
            os.close(self.fd)
            self.fd = -1

    def report(self):
        return {"bytes": self.count, "sha256": self.digest.hexdigest()}


class PtyAdapter:
    """Socket-like master endpoint; every artificial ACK fault is explicit.

    MSG_PEEK uses at most one bounded lookahead read, recorded once physically.
    Normal send returns the actual PTY write count. Fault cases intentionally
    alter/drop ACK bytes; receiver ACK success in those cases is only acceptance
    by this injected adapter, never a physical delivery or guest success claim.
    """
    def __init__(self, master, held_slave, child, attempt, case):
        self.master, self.held_slave, self.child = master, held_slave, child
        self.case = case
        self.lookahead = bytearray()
        self.eof = False
        self.disconnected = False
        self.ack_offset = 0
        self.raw = WireLog(attempt / "exporter-to-peer.bin", WIRE_LIMIT)
        self.sent = WireLog(attempt / "peer-to-exporter.bin", 4096)
        self.intended = WireLog(attempt / "peer-intended-ack.bin", 4096)
        os.set_blocking(master, False)

    def setblocking(self, value):
        require(not value, "only nonblocking PTY adapter supported")

    def fileno(self):
        return self.master

    def release_slave(self):
        if self.held_slave >= 0:
            os.close(self.held_slave)
            self.held_slave = -1

    def close_channel(self):
        self.release_slave()
        if self.master >= 0:
            os.close(self.master)
            self.master = -1

    def recv(self, count, flags=0):
        require(flags in (0, socket.MSG_PEEK), "unsupported PTY recv flags")
        if not self.lookahead and not self.eof and self.master >= 0:
            want = min(count, 32768)
            if self.case == "disconnect":
                want = min(want, 4096 - self.raw.count)
                if want <= 0:
                    self.disconnected = True
                    self.close_channel()
                    return b""
            try:
                data = os.read(self.master, want)
            except BlockingIOError:
                # Parent holds the slave only across the fork/open race. An
                # exporter that exits before opening still produces real EOF.
                if self.held_slave >= 0:
                    observed = os.waitid(os.P_PID, self.child, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                    if observed is not None:
                        self.release_slave()
                raise
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
                data = b""  # Linux PTY master EIO after its last slave closes.
            if data:
                self.release_slave()
                self.raw.append(data)
                self.lookahead.extend(data)
            else:
                self.eof = True
        data = bytes(self.lookahead[:count])
        if not flags:
            del self.lookahead[:len(data)]
        return data

    def send(self, data):
        if self.master < 0:
            raise BrokenPipeError(errno.EPIPE, "injected PTY disconnect")
        offset = self.ack_offset
        changed = bytearray(data)
        mutations = {"ack-magic": (0, 1), "ack-nonce": (8, 1), "ack-count": (32, 1), "ack-status": (24, 1)}
        if self.case in mutations:
            position, mask = mutations[self.case]
            if offset <= position < offset + len(changed):
                changed[position - offset] ^= mask
        if self.case == "ack-missing":
            self.intended.append(data)
            self.ack_offset += len(data)
            return len(data)  # Explicit injected drop; zero physical send bytes.
        if self.case == "ack-short" and offset + len(changed) >= 112:
            changed = changed[:max(0, 111 - offset)]
        if changed:
            count = os.write(self.master, changed)
            self.sent.append(changed[:count])
            self.intended.append(data[:count])
            self.ack_offset += count
            if count != len(changed):
                return count
        else:
            count = 0
        if self.case == "ack-short" and self.ack_offset == 111:
            # Retain the omitted byte as intent and close the physical channel.
            omitted = data[count:]
            self.intended.append(omitted)
            self.ack_offset += len(omitted)
            self.disconnected = True
            self.close_channel()
            return len(data)
        return count

    def close(self):
        self.close_channel()
        self.raw.close()
        self.sent.close()
        self.intended.close()


def prepare_tree(attempt, case):
    source = attempt / "source"
    source.mkdir(mode=0o700)
    expected = {}
    directories = []
    if case in ("binary", "ack-magic", "ack-nonce", "ack-count", "ack-status", "ack-short", "ack-missing"):
        directories = ["empty directory", "nested", "nested/deeper"]
        for path in directories:
            (source / path).mkdir(mode=0o700)
        expected = {"empty": b"", "nested/deeper/raw.bin": bytes(range(256)) * 19 + b"\x00\xff\r\nSTAF0001\x00",
                    "space name.txt": b"literal artifact\nsecond line\n"}
    elif case == "disconnect":
        expected = {"large.bin": bytes(range(256)) * 4096}
    elif case == "entry-limit":
        expected = {f"entry-{i:03d}": b"" for i in range(257)}
    elif case == "content-limit":
        with (source / "oversized").open("xb") as stream:
            stream.truncate(16777217)
    elif case in ("symlink", "hardlink"):
        outside = attempt / "outside-sentinel.bin"
        outside.write_bytes(b"OUTSIDE_SELECTED_TREE_MUST_NEVER_BE_READ_319587\n")
        if case == "symlink":
            (source / "unsafe").symlink_to(outside)
        else:
            os.link(outside, source / "unsafe")
    elif case == "fifo":
        os.mkfifo(source / "unsafe", 0o600)
    elif case != "empty":
        raise ValueError("unrecognized source fixture")
    for name, data in expected.items():
        with (source / name).open("xb") as stream:
            stream.write(data)
    retain_json(attempt / "expected-content.json", {"files": {name: {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in expected.items()}, "directories": directories, "case": case})
    return source, expected, directories


def spawn_exporter(exporter, source, slave_name, nonce, attempt):
    stdout = os.open(attempt / "exporter.stdout", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    stderr = os.open(attempt / "exporter.stderr", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    start = time.monotonic_ns()
    child = os.fork()
    if child == 0:
        try:
            os.dup2(stdout, 1)
            os.dup2(stderr, 2)
            fd = os.open("/dev/null", os.O_RDONLY)
            os.dup2(fd, 0)
            for name in os.listdir("/proc/self/fd"):
                number = int(name)
                if number > 2:
                    try:
                        os.close(number)
                    except OSError as exc:
                        if exc.errno != errno.EBADF:
                            raise
            os.execve(exporter, [exporter, str(source), slave_name, nonce],
                      {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"})
        except BaseException:
            os._exit(127)
    os.close(stdout)
    os.close(stderr)
    return child, start


def worker(args):
    attempt = args.attempt_root
    require(attempt.is_dir() and args.case in CASES, "worker requires one fresh parent-owned attempt")
    require(identity(args.exporter)["sha256"] == args.exporter_sha256, "actual exporter ELF changed")
    receiver = import_source("actual_c_artifact_receiver", args.receiver, RECEIVER_SHA)
    source, expected, directories = prepare_tree(attempt, args.case)
    nonce = os.urandom(16).hex()
    master, slave = pty.openpty()
    tty.setraw(slave, when=termios.TCSANOW)
    attrs = termios.tcgetattr(slave)
    slave_name = os.ttyname(slave)
    require(stat.S_ISCHR(os.fstat(slave).st_mode), "PTY slave is not a character device")
    retain_json(attempt / "invocation.json", {"argv": [str(args.exporter), str(source), slave_name, nonce],
                "exporter": identity(args.exporter), "case": args.case, "nonce": nonce, "pty_slave": slave_name,
                "termios": [*attrs[:6], [b.hex() if isinstance(b, bytes) else b for b in attrs[6]]],
                "raw_pty": True, "worker_timeout_seconds": 70, "exporter_deadline_seconds_unchanged": 60,
                "fault": args.case if args.case.startswith("ack-") or args.case == "disconnect" else None,
                "application_acceptance": False, "guest_execution": False})
    child, start = spawn_exporter(str(args.exporter), source, slave_name, nonce, attempt)
    adapter = PtyAdapter(master, slave, child, attempt, args.case)
    raw_wait = None
    killed = False
    observed = None
    error = None
    finished = None
    collection_finished = None
    try:
        observed = receiver.receive(adapter, attempt / "capture", str(source), nonce, timeout_seconds=65)
        retain_json(attempt / "receiver-result.json", observed)
        deadline = start + 70 * 10**9
        while time.monotonic_ns() < deadline:
            # Drain physical bytes after END, including an exporter's framed
            # failure after a deliberately bad ACK, until real child exit/EOF.
            if adapter.master >= 0 and not adapter.eof:
                try:
                    adapter.recv(32768)
                except (BlockingIOError, InterruptedError):
                    pass
            if raw_wait is None:
                got, status = os.waitpid(child, os.WNOHANG)
                if got == child:
                    raw_wait = status
                    finished = time.monotonic_ns()
            if raw_wait is not None and (adapter.eof or adapter.master < 0):
                break
            if adapter.master >= 0 and not adapter.eof:
                select.select([adapter], [], [], 0.02)
            else:
                time.sleep(0.02)
            require((attempt / "exporter.stdout").stat().st_size <= 65536 and
                    (attempt / "exporter.stderr").stat().st_size <= 65536, "exporter stream cap")
        collection_finished = time.monotonic_ns()
        require(raw_wait is not None, "actual exporter exceeded worker deadline")
        require(adapter.eof or adapter.disconnected, "actual PTY EOF not observed")
        require(finished < deadline and collection_finished < deadline,
                "actual exporter wait/EOF collection completed after worker deadline")
        require(read_regular(attempt / "exporter.stdout", 65536) == b"", "exporter unexpected stdout")
        stderr = read_regular(attempt / "exporter.stderr", 65536)
        complete = args.case in ("binary", "empty")
        require(raw_wait == (0 if complete else 256), "actual exporter raw wait differs from literal oracle")
        wire = read_regular(attempt / "capture/wire.bin")
        physical = read_regular(attempt / "exporter-to-peer.bin")
        require(physical.startswith(wire), "receiver bytes are not exact actual-C prefix")
        require(observed["manifest"]["wire_sha256"] == hashlib.sha256(wire).hexdigest(), "actual-C wire SHA mismatch")
        require(observed["manifest"]["nonce"] == nonce, "actual-C nonce mismatch")
        if complete:
            require(observed["ok"], "actual-C positive capture/ACK failed")
            require(physical == wire, "positive exporter emitted unexpected post-END bytes")
            require(adapter.sent.count == 112 and adapter.intended.count == 112, "actual positive ACK width")
            ack = read_regular(attempt / "peer-to-exporter.bin")
            require(ack == read_regular(attempt / "capture/ack.bin"), "actual positive ACK altered")
            line = re.fullmatch(rb"STAF EXPORT_ACK version=1 entries=(\d+) bytes=(\d+) wire_sha256=([0-9a-f]{64}) manifest_sha256=([0-9a-f]{64})\n", stderr)
            require(line is not None, "literal exporter ACK log shape")
            require(int(line[1]) == len(expected) + len(directories) and int(line[2]) == sum(map(len, expected.values())), "literal positive totals")
            require(line[3].decode() == hashlib.sha256(wire).hexdigest() and
                    line[4].decode() == hashlib.sha256(read_regular(attempt / "capture/manifest.json")).hexdigest(), "C ACK digest echo mismatch")
            expected_paths = set(expected) | set(directories)
            require({row["path"] for row in observed["manifest"]["entries"]} == expected_paths, "complete actual entry set differs")
            for name, data in expected.items():
                require(read_regular(attempt / "capture/files" / name) == data, "literal binary content differs: " + name)
            for name in directories:
                require((attempt / "capture/files" / name).is_dir(), "empty source directory missing")
        else:
            line = re.fullmatch(rb"STAF EXPORT_FAIL reason=([a-z-]+) errno=(\d+) entries=(\d+) bytes=(\d+) poweroff_authorized=false\n", stderr)
            require(line is not None and b"STAF EXPORT_ACK" not in stderr, "negative exporter did not fail closed")
            reason, number = line[1].decode(), int(line[2])
            if args.case in ("symlink", "fifo", "hardlink", "entry-limit", "content-limit"):
                reasons = {"symlink": ("unsafe-entry-type", 22), "fifo": ("unsafe-entry-type", 22),
                           "hardlink": ("unsafe-or-changed-file", 116), "entry-limit": ("entry-limit", 27),
                           "content-limit": ("content-limit", 27)}
                require((reason, number) == reasons[args.case], "unsafe/cap rejection differs")
                require(observed["manifest"]["status"] == "FAIL" and "exporter-failure:" + reason in observed["manifest"]["error"], "actual C failure frame missing")
                require(b"OUTSIDE_SELECTED_TREE_MUST_NEVER_BE_READ_319587" not in physical, "exporter read outside selected tree")
            elif args.case == "ack-missing":
                require((reason, number) == ("channel-deadline", 110), "missing ACK did not use original deadline")
                require(finished - start >= 60 * 10**9 and adapter.sent.count == 0 and adapter.intended.count == 112,
                        "missing ACK needs real sixty-second wait and zero physical ACK bytes")
            elif args.case in ("ack-magic", "ack-nonce", "ack-count", "ack-status"):
                require((reason, number) == ("invalid-or-failed-host-ack", 71), "mutated actual ACK was accepted")
                require(adapter.sent.count == 112 and read_regular(attempt / "peer-to-exporter.bin") !=
                        read_regular(attempt / "capture/ack.bin"), "actual ACK mutation missing")
            else:
                require(reason in ("channel-io", "channel-hangup", "channel-poll-error", "channel-eof") and number in (5, 32),
                        "actual PTY disconnect/short ACK failure differs")
                require(adapter.disconnected, "physical disconnect not injected")
                if args.case == "ack-short":
                    require(adapter.sent.count == 111, "truncated actual ACK width differs")
                else:
                    require(adapter.raw.count == 4096 and observed["manifest"]["status"] == "FAIL", "disconnect prefix witness differs")
    except BaseException as exc:
        error = f"{type(exc).__name__}:{exc}"
    finally:
        if raw_wait is None:
            # Direct unreaped child identity cannot be reused; no other waiter.
            killed = True
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
            cleanup_deadline = time.monotonic() + 10
            while time.monotonic() < cleanup_deadline:
                got, status = os.waitpid(child, os.WNOHANG)
                if got == child:
                    raw_wait = status
                    finished = time.monotonic_ns()
                    break
                time.sleep(0.02)
        adapter.close()
        retain_json(attempt / "worker-result.json", {"schema_version": 1, "status": "FAIL" if error else "PASS",
                    "case": args.case, "error": error, "exporter_pid": child, "exporter_raw_wait": raw_wait,
                    "exporter_started_monotonic_ns": start, "exporter_finished_monotonic_ns": finished,
                    "wait_and_eof_collected_monotonic_ns": collection_finished,
                    "owned_child_killed": killed, "owned_child_reaped": raw_wait is not None,
                    "physical_eof": adapter.eof, "injected_disconnect": adapter.disconnected,
                    "actual_exporter_to_peer": adapter.raw.report(), "actual_peer_to_exporter": adapter.sent.report(),
                    "intended_ack": adapter.intended.report(), "ack_fault_explicitly_injected": args.case.startswith("ack-"),
                    "scope": "actual-C-exporter-PTY-infrastructure-only", "application_acceptance": False,
                    "transport_fault_acceptance": False, "guest_execution": False})
    return 1 if error else 0


def suite(args):
    cases = args.cases or list(CASES)
    require(len(cases) == len(set(cases)) and all(case in CASES for case in cases), "unknown/duplicate case")
    require(identity(args.exporter)["sha256"] == args.exporter_sha256, "pinned exporter identity mismatch")
    require(identity(args.receiver)["sha256"] == RECEIVER_SHA, "reviewed receiver mismatch")
    require(identity(args.supervisor)["sha256"] == SUPERVISOR_SHA, "reviewed supervisor mismatch")
    require(identity(args.exporter_source)["sha256"] == EXPORTER_SOURCE_SHA, "reviewed guarded exporter source mismatch")
    args.attempt_root.mkdir(mode=0o700)
    inputs = args.attempt_root / "inputs"
    inputs.mkdir(mode=0o700)
    retained = []
    for name, path in (("driver.py", Path(__file__)), ("receiver.py", args.receiver), ("supervisor.py", args.supervisor),
                       ("exporter.c", args.exporter_source), ("exporter", args.exporter)):
        data = read_regular(path)
        digest = hashlib.sha256(data).hexdigest()
        required_hashes = {"receiver.py": RECEIVER_SHA, "supervisor.py": SUPERVISOR_SHA,
                           "exporter.c": EXPORTER_SOURCE_SHA, "exporter": args.exporter_sha256}
        require(name not in required_hashes or digest == required_hashes[name], "input changed during exact-byte retention")
        target = inputs / name
        with target.open("xb") as stream:
            stream.write(data)
        if name == "exporter":
            target.chmod(0o700)
        retained.append({"original": str(path), "retained": str(target), "bytes": len(data),
                         "sha256": digest})
    invocation = {"schema_version": 1, "argv": sys.argv, "inputs": retained, "cases": cases,
                  "scope": "actual-C-exporter-PTY-infrastructure-only", "application_acceptance": False,
                  "transport_fault_acceptance": False, "guest_execution": False, "suite_timeout_seconds": 300,
                  "case_timeout_seconds": 75, "cleanup_timeout_seconds": 15,
                  "isolation_authority": "external original pinned container wrapper; dockerenv alone is insufficient",
                  "automatic_fixture_deletion": False}
    retain_json(args.attempt_root / "invocation.json", invocation)
    supervisor = import_source("artifact_c_supervisor", inputs / "supervisor.py", SUPERVISOR_SHA)
    results, failure = [], None
    start = time.monotonic()
    for case in cases:
        try:
            require(300 - (time.monotonic() - start) >= 75, "insufficient suite budget for full next case")
            attempt = args.attempt_root / case
            attempt.mkdir(mode=0o700)
            report = supervisor.run_supervised([sys.executable, "-B", str(inputs / "driver.py"), "--worker",
                "--case", case, "--attempt-root", str(attempt), "--exporter", str(inputs / "exporter"),
                "--exporter-sha256", args.exporter_sha256, "--receiver", str(inputs / "receiver.py")],
                cwd=str(attempt), env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
                "PYTHONDONTWRITEBYTECODE": "1"}, attempt_dir=str(attempt / "supervision"), timeout_seconds=75,
                cleanup_timeout_seconds=15, stdout_limit_bytes=1024 * 1024, stderr_limit_bytes=1024 * 1024)
            require(report["status"] == "COMPLETED" and report["raw_wait_status"] == 0 and report["cleanup_complete"],
                    "worker supervisor/raw wait/cleanup failed")
            observed = json.loads(read_regular(attempt / "worker-result.json", 65536))
            require(observed["status"] == "PASS" and observed["owned_child_reaped"] and not observed["owned_child_killed"],
                    "actual exporter protocol/oracle failed")
            results.append({"case": case, "status": "PASS", "worker": identity(attempt / "worker-result.json")})
            print("EXPORTER_PTY_CASE " + case + " PASS", flush=True)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            failure = {"case": case, "error": f"{type(exc).__name__}:{exc}"}
            print("EXPORTER_PTY_FIRST_FAILURE " + json.dumps(failure), flush=True)
            break
    retain_json(args.attempt_root / "result.json", {**invocation, "status": "FAIL" if failure else "PASS",
                "results": results, "first_failure": failure, "elapsed_seconds": time.monotonic() - start})
    return 1 if failure else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exporter", type=Path, required=True)
    parser.add_argument("--exporter-sha256", required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--receiver", type=Path, default=HERE / "receiver.py")
    parser.add_argument("--exporter-source", type=Path, default=HERE / "exporter.c")
    parser.add_argument("--supervisor", type=Path)
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(Path("/.dockerenv").is_file(), "use the authorized pinned container wrapper")
    require(args.exporter.is_absolute() and args.attempt_root.is_absolute() and args.receiver.is_absolute(), "absolute paths required")
    if args.worker:
        require(args.cases is not None and len(args.cases) == 1, "worker requires one case")
        args.case = args.cases[0]
        return worker(args)
    require(args.supervisor is not None and args.supervisor.is_absolute(), "absolute reviewed supervisor required")
    return suite(args)


if __name__ == "__main__":
    raise SystemExit(main())
