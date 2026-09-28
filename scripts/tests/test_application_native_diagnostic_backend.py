"""Host-only tests: fake QEMU/QMP plus one bounded Python ownership microtest."""

import importlib.util
import errno
import json
import math
import os
from pathlib import Path
import socket
import stat
import subprocess
import signal
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "scripts/application-tests"
sys.path.insert(0, str(APP))
import native_diagnostic_backend as backend

spec = importlib.util.spec_from_file_location("native_diagnostic_backend_lifecycle", APP / "native_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class FakeProcess:
    def __init__(self, *, wait_fails=False):
        self.calls = []
        self.wait_fails = wait_fails
        self.pid = 12345
        self.returncode = None

    def poll(self): return self.returncode

    def terminate(self): self.calls.append("terminate")
    def kill(self): self.calls.append("kill")
    def wait(self, timeout):
        self.calls.append("wait")
        if self.wait_fails and "kill" not in self.calls:
            raise subprocess.TimeoutExpired("fake", timeout)
        self.returncode = 0
        return 0
    def communicate(self, timeout):
        self.calls.append("communicate")
        return b"host stdout", b"host stderr"


class FakeSocket:
    def __init__(self, statuses=None, *, bad_reply=False, reject_quit=False,
                 close_fails=False, bad_greeting=False):
        self.statuses = list(statuses or [{"status": "shutdown", "running": False}])
        self.bad_reply = bad_reply
        self.reject_quit = reject_quit
        self.close_fails = close_fails
        self.bad_greeting = bad_greeting
        self.sent = []
        self.pending = [b'{"other":{}}\n' if bad_greeting else b'{"QMP":{"version":{}}}\n']
        self.timeout = None
        self.connected = None
        self.closed = False

    def settimeout(self, timeout): self.timeout = timeout
    def connect(self, path): self.connected = path
    def recv(self, size):
        if not self.pending:
            raise TimeoutError("fake socket exhausted")
        return self.pending.pop(0)
    def sendall(self, raw):
        request = json.loads(raw)
        self.sent.append(request)
        if self.bad_reply:
            self.pending.append(b'{"return":{},"id":99}\n')
        elif request["execute"] == "query-status":
            value = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            self.pending.append(json.dumps({"return": value, "id": request["id"]}).encode() + b"\n")
        elif request["execute"] == "quit" and self.reject_quit:
            self.pending.append(json.dumps({"error": {"class": "GenericError"}, "id": request["id"]}).encode() + b"\n")
        else:
            self.pending.append(json.dumps({"return": {}, "id": request["id"]}).encode() + b"\n")
    def close(self):
        self.closed = True
        if self.close_fails:
            raise OSError("socket close failed")


class HostileCleanupError(OSError):
    def __repr__(self):
        raise RuntimeError("repr trap")

    def __str__(self):
        raise RuntimeError("str trap")

    def __getattribute__(self, name):
        if name in ("args", "errno", "add_note", "_mckernel_secondary_errors"):
            raise RuntimeError("attribute trap")
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        raise RuntimeError("setattr trap")


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.sockpath = str(Path(self.temp.name) / "qmp.sock")
        self.socket_stat = os.stat_result((stat.S_IFSOCK | 0o600, 123, 456, 1,
                                           os.getuid(), os.getgid(), 0, 0, 0, 0))
        # Most backend tests use a non-running fake Popen result; identity
        # capture itself is covered by the focused identity tests.
        self._identity_patch = mock.patch.object(
            backend, "_capture_process_identity",
            return_value=(12345, 12345, 12345, 1))
        self._identity_patch.start()
        self.addCleanup(self._identity_patch.stop)

    def qmp(self, sock):
        return backend.QmpBackend(self.sockpath, socket_factory=lambda *args: sock,
                                  stat_factory=lambda path: self.socket_stat)

    def test_process_stat_parser_rejects_malformed_and_keeps_comm_parentheses(self):
        good = b"42 (name with ) paren) S " + b" ".join(str(n).encode() for n in range(1, 19)) + b" 98765 23\n"
        with mock.patch.object(backend.Path, "read_bytes", return_value=good):
            self.assertEqual(backend._proc_starttime_ticks(42), 98765)
        for raw in (b"bad", b"42 (x) S 1 2\n", b"42 (x) S " + b" ".join([b"1"] * 18) + b" nope\n"):
            with self.subTest(raw=raw), mock.patch.object(backend.Path, "read_bytes", return_value=raw):
                with self.assertRaises(ValueError):
                    backend._proc_starttime_ticks(42)

    def test_direct_popen_exact_arguments_and_no_inherited_environment(self):
        calls = []
        process = FakeProcess()
        def popen(*args, **kwargs):
            calls.append((args, kwargs))
            return process
        argv = ["/usr/libexec/qemu-kvm", "-nic", "none", "-qmp", "unix:" + self.sockpath + ",server=on,wait=off"]
        factory = backend.process_factory(argv, self.temp.name, popen_factory=popen)
        argv[1] = "changed"
        self.assertIs(factory(timeout=1).child, process)
        self.assertEqual(calls[0][0], (("/usr/libexec/qemu-kvm", "-nic", "none", "-qmp", "unix:" + self.sockpath + ",server=on,wait=off"),))
        kwargs = calls[0][1]
        self.assertEqual({key: value for key, value in kwargs.items() if key not in ("stdout", "stderr")},
                         dict(stdin=subprocess.DEVNULL, shell=False, cwd=self.temp.name,
                              env={"LC_ALL": "C"}, close_fds=True, pass_fds=(), start_new_session=True))
        self.assertIs(type(kwargs["stdout"]), int)
        self.assertIs(type(kwargs["stderr"]), int)
        self.assertEqual((Path(self.temp.name) / "qemu.stdout").stat().st_mode & 0o777, 0o600)
        self.assertEqual((Path(self.temp.name) / "qemu.stderr").stat().st_mode & 0o777, 0o600)
        for invalid in (0, -1, math.nan, math.inf, True):
            with self.assertRaises(ValueError): factory(timeout=invalid)
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, "exact direct-QEMU"):
            backend.process_factory(["/bin/true"], self.temp.name, popen_factory=popen)

    def test_qmp_order_ids_delayed_terminal_and_quit(self):
        sock = FakeSocket([{"status": "running", "running": True},
                           {"status": "running", "running": True},
                           {"status": "shutdown", "running": False}])
        seen = []
        def socket_factory(family, kind):
            seen.append((family, kind))
            return sock
        qmp = backend.qmp_factory(self.sockpath, socket_factory=socket_factory,
                                  stat_factory=lambda path: self.socket_stat)(timeout=1)
        qmp.negotiate(1)
        qmp.resume(1)
        self.assertEqual(qmp.wait_shutdown(1), {"status": "shutdown"})
        qmp.terminate(1)
        qmp.close(1)
        self.assertEqual(seen, [(socket.AF_UNIX, socket.SOCK_STREAM)])
        self.assertEqual(sock.connected, self.sockpath)
        self.assertEqual([(x["execute"], x["id"]) for x in sock.sent],
                         [("qmp_capabilities", 1), ("cont", 2),
                          ("query-status", 3), ("query-status", 4), ("query-status", 5), ("quit", 6)])
        self.assertTrue(sock.closed)

    def test_socket_readiness_retry_timeout_stale_and_wrong_owner(self):
        sock = FakeSocket()
        probes = []
        def delayed(path):
            probes.append(path)
            if len(probes) < 3:
                raise FileNotFoundError(path)
            return self.socket_stat
        qmp = backend.QmpBackend(self.sockpath, socket_factory=lambda *args: sock, stat_factory=delayed)
        qmp.negotiate(1)
        self.assertEqual(len(probes), 4)
        qmp.close(1)

        missing = backend.QmpBackend(self.sockpath, stat_factory=lambda path: (_ for _ in ()).throw(FileNotFoundError(path)))
        with self.assertRaises(TimeoutError): missing.negotiate(0.01)

        class Refused(FakeSocket):
            def connect(self, path): raise ConnectionRefusedError(errno.ECONNREFUSED, "refused")
        stale = backend.QmpBackend(self.sockpath, socket_factory=lambda *args: Refused(),
                                   stat_factory=lambda path: self.socket_stat)
        with self.assertRaises(TimeoutError): stale.negotiate(0.12)

        class Denied(FakeSocket):
            def connect(self, path): raise PermissionError(errno.EACCES, "denied")
        denied = backend.QmpBackend(self.sockpath, socket_factory=lambda *args: Denied(),
                                    stat_factory=lambda path: self.socket_stat)
        with self.assertRaises(PermissionError): denied.negotiate(1)

        changed = []
        new_identity = os.stat_result((stat.S_IFSOCK | 0o600, 124, 456, 1,
                                       os.getuid(), os.getgid(), 0, 0, 0, 0))
        def changed_stat(path):
            changed.append(path)
            return self.socket_stat if len(changed) == 1 else new_identity
        swapped = backend.QmpBackend(self.sockpath, socket_factory=lambda *args: FakeSocket(),
                                     stat_factory=changed_stat)
        with self.assertRaisesRegex(backend.QmpError, "identity changed"): swapped.negotiate(1)

        for mode, uid in ((stat.S_IFREG | 0o600, os.getuid()),
                          (stat.S_IFSOCK | 0o600, os.getuid() + 1)):
            entry = os.stat_result((mode, 123, 456, 1, uid, os.getgid(), 0, 0, 0, 0))
            wrong = backend.QmpBackend(self.sockpath, socket_factory=lambda *args: FakeSocket(),
                                       stat_factory=lambda path: entry)
            with self.assertRaisesRegex(backend.QmpError, "owned socket"): wrong.negotiate(1)

    def test_same_socket_may_refuse_repeatedly_until_listening(self):
        attempts = []
        class Starting(FakeSocket):
            def connect(self, path):
                attempts.append(self)
                if len(attempts) <= 3:
                    raise ConnectionRefusedError(errno.ECONNREFUSED, "starting")
                super().connect(path)
        qmp = backend.QmpBackend(self.sockpath, socket_factory=lambda *args: Starting(),
                                 stat_factory=lambda path: self.socket_stat)
        qmp.negotiate(1)
        self.assertEqual(len(attempts), 4)
        self.assertTrue(all(sock.closed for sock in attempts[:3]))
        qmp.close(1)

    def test_socket_swap_during_refusal_is_rejected(self):
        class Starting(FakeSocket):
            def connect(self, path): raise ConnectionRefusedError(errno.ECONNREFUSED, "starting")
        for changed in (os.stat_result((stat.S_IFSOCK | 0o600, 124, 456, 1,
                                       os.getuid(), os.getgid(), 0, 0, 0, 0)),
                        os.stat_result((stat.S_IFREG | 0o600, 123, 456, 1,
                                       os.getuid(), os.getgid(), 0, 0, 0, 0)),
                        os.stat_result((stat.S_IFSOCK | 0o600, 123, 456, 1,
                                       os.getuid() + 1, os.getgid(), 0, 0, 0, 0)),
                        FileNotFoundError("removed")):
            with self.subTest(changed=changed):
                qmp = backend.QmpBackend(self.sockpath, socket_factory=lambda *args: Starting(),
                                         stat_factory=mock.Mock(side_effect=[self.socket_stat, changed]))
                with self.assertRaises((backend.QmpError, FileNotFoundError)):
                    qmp.negotiate(1)

    def _factory(self, popen):
        return backend.process_factory([backend.QEMU, "-qmp", "unix:" + self.sockpath +
                                        ",server=on,wait=off"], self.temp.name, popen_factory=popen)

    def test_spawn_rejects_preexisting_qmp_and_changed_attempt(self):
        popen = mock.Mock()
        factory = self._factory(popen)
        Path(self.sockpath).symlink_to("missing")
        with self.assertRaisesRegex(ValueError, "exists before spawn"): factory(timeout=1)
        popen.assert_not_called()
        Path(self.sockpath).unlink()
        moved = self.temp.name + "-old"
        os.rename(self.temp.name, moved)
        try:
            os.mkdir(self.temp.name, 0o700)
            with self.assertRaisesRegex(ValueError, "directory identity changed"): factory(timeout=1)
            popen.assert_not_called()
        finally:
            os.rmdir(self.temp.name)
            os.rename(moved, self.temp.name)

    def test_owner_construction_failure_precedes_spawn(self):
        popen = mock.Mock()
        factory = self._factory(popen)
        failure = RuntimeError("owner construction")
        before = set(os.listdir("/proc/self/fd"))
        with mock.patch.object(backend, "ProcessOwner", side_effect=failure):
            with self.assertRaises(RuntimeError) as raised: factory(timeout=1)
        self.assertIs(raised.exception, failure)
        popen.assert_not_called()
        self.assertEqual(set(os.listdir("/proc/self/fd")), before)

    def test_post_popen_identity_failure_retains_primitive_retirement_evidence(self):
        child = FakeProcess()
        original = RuntimeError("identity capture failed")
        factory = self._factory(lambda *args, **kwargs: child)
        with mock.patch.object(backend, "_capture_process_identity", side_effect=original), \
             mock.patch.object(backend, "_retire_untransferred",
                               return_value={"reaped": True, "returncode": -signal.SIGKILL}):
            with self.assertRaises(backend.ProcessAcquisitionFailure) as raised:
                factory(timeout=1)
        self.assertIs(raised.exception.__cause__, original)
        evidence = raised.exception._mckernel_qemu_acquisition_evidence
        self.assertEqual(evidence["argv"], [backend.QEMU, "-qmp", "unix:" + self.sockpath + ",server=on,wait=off"])
        self.assertEqual(evidence["pid"], child.pid)
        self.assertEqual({key: evidence[key] for key in ("pgid", "sid", "starttime_ticks")},
                         {"pgid": None, "sid": None, "starttime_ticks": None})
        self.assertFalse(evidence["identity_complete"])
        self.assertEqual((evidence["reaped"], evidence["returncode"]), (True, -signal.SIGKILL))

    def test_secondary_recording_supports_python39_and_closes_all_fds(self):
        class LegacyFailure(Exception):
            add_note = None

        failure = LegacyFailure("original")
        original_args = failure.args
        close_calls = []
        close_errors = {
            101: OSError("close 101"),
            102: OSError("close 102"),
            103: OSError("close 103"),
        }
        entry = os.stat_result((stat.S_IFREG, 7, 8, 1, os.getuid(), os.getgid(), 0, 0, 0, 0))

        def close(fd):
            close_calls.append(fd)
            raise close_errors[fd]

        with mock.patch.object(backend.os, "fstat", return_value=entry), \
             mock.patch.object(backend.os, "close", side_effect=close):
            backend._close_fds([(101, (8, 7)), (102, (8, 7)), (103, (8, 7))],
                               failure=failure)
        self.assertEqual(close_calls, [101, 101, 102, 102, 103, 103])
        self.assertEqual(str(failure), "original")
        self.assertEqual(failure.args, original_args)
        self.assertGreaterEqual(len(failure._mckernel_secondary_errors), 4)
        self.assertTrue(any("close 102" in item for item in failure._mckernel_secondary_errors))
        self.assertTrue(any("close 103" in item for item in failure._mckernel_secondary_errors))

    def test_spawn_recovery_records_retirement_and_post_spawn_cleanup(self):
        class LegacyFailure(Exception):
            add_note = None

        failure = LegacyFailure("spawn original")
        child = mock.Mock(pid=4321)
        with mock.patch.object(backend.signal, "pthread_sigmask", side_effect=OSError("mask")), \
             mock.patch.object(backend.signal, "setitimer", side_effect=OSError("timer")), \
             mock.patch.object(backend.signal, "sigtimedwait", side_effect=OSError("wait alarm")), \
             mock.patch.object(backend.os, "fstat", return_value=os.stat_result(
                 (stat.S_IFREG, 7, 8, 1, os.getuid(), os.getgid(), 0, 0, 0, 0))), \
             mock.patch.object(backend.os, "close", side_effect=OSError("close")):
            backend._retire_untransferred(child, failure)
            backend._close_fds([(101, None), (102, None), (103, None)], failure=failure)
        self.assertEqual(str(failure), "spawn original")
        details = failure._mckernel_secondary_errors
        self.assertTrue(any("block alarm" in item for item in details))
        self.assertTrue(any("cancel alarm" in item for item in details))
        self.assertTrue(any("descriptor close" in item for item in details))
        self.assertGreaterEqual(sum("descriptor close" in item for item in details), 6)

    def test_hostile_repr_does_not_stop_all_descriptor_cleanup(self):
        class BadRepr(OSError):
            def __repr__(self):
                raise RuntimeError("repr failed")

        failure = RuntimeError("original")
        close_calls = []
        entry = os.stat_result((stat.S_IFREG, 7, 8, 1, os.getuid(), os.getgid(), 0, 0, 0, 0))

        def close(fd):
            close_calls.append(fd)
            raise BadRepr("close failed")

        with mock.patch.object(backend.os, "fstat", return_value=entry), \
             mock.patch.object(backend.os, "close", side_effect=close):
            backend._close_fds([(101, (8, 7)), (102, (8, 7)), (103, (8, 7))],
                               failure=failure)
        self.assertEqual(close_calls, [101, 101, 102, 102, 103, 103])
        self.assertEqual(str(failure), "original")
        details = getattr(failure, "_mckernel_secondary_errors", [])
        details += getattr(failure, "__notes__", [])
        self.assertTrue(any("unrepresentable" in item for item in details))

    def test_hostile_repr_does_not_stop_retirement_sequence(self):
        class BadRepr(OSError):
            def __repr__(self):
                raise RuntimeError("repr failed")

        failure = RuntimeError("original")
        child = mock.Mock(pid=4321)
        getpgid_calls = []
        with mock.patch.object(backend.os, "getpgid", side_effect=lambda pid:
                               getpgid_calls.append(pid) or (_ for _ in ()).throw(BadRepr("group"))), \
             mock.patch.object(backend.os, "waitid", return_value=object()), \
             mock.patch.object(backend.signal, "pthread_sigmask", return_value={}), \
             mock.patch.object(backend.signal, "setitimer"), \
             mock.patch.object(backend.signal, "sigtimedwait"), \
             mock.patch.object(backend.os, "killpg"):
            backend._retire_untransferred(child, failure)
        child.wait.assert_called_once_with(timeout=2)
        self.assertEqual(getpgid_calls, [4321, 4321])
        self.assertEqual(str(failure), "original")
        details = getattr(failure, "_mckernel_secondary_errors", [])
        details += getattr(failure, "__notes__", [])
        self.assertTrue(any("unrepresentable" in item for item in details))

    def test_hostile_block_alarm_error_still_retires_child(self):
        # Regression: the block-alarm handler formerly formatted repr outside
        # the recorder and aborted before TERM/observe/KILL/reap.
        class BadRepr(OSError):
            def __repr__(self):
                raise RuntimeError("repr failed")

        failure = RuntimeError("original")
        events = []
        child = mock.Mock(pid=4321)
        child.wait.side_effect = lambda **kwargs: events.append("reap")
        with mock.patch.object(backend.signal, "pthread_sigmask", side_effect=BadRepr("mask")), \
             mock.patch.object(backend.signal, "setitimer", side_effect=lambda *args: events.append("cancel")), \
             mock.patch.object(backend.signal, "sigtimedwait", side_effect=lambda *args: events.append("consume")), \
             mock.patch.object(backend.os, "getpgid", return_value=4321), \
             mock.patch.object(backend.os, "killpg", side_effect=lambda pid, sig: events.append(sig)), \
             mock.patch.object(backend.os, "waitid", side_effect=lambda *args: events.append("observe") or object()):
            backend._retire_untransferred(child, failure)
        self.assertEqual(events, ["cancel", signal.SIGTERM, "observe", signal.SIGKILL, "reap", "consume"])
        self.assertEqual(type(failure), RuntimeError)
        self.assertEqual(failure.args, ("original",))

    def test_recorder_failures_are_nonthrowing_and_fallback_is_fixed_text(self):
        class BrokenAppend:
            def append(self, item):
                raise HostileCleanupError("append")

        class BrokenNote(Exception):
            def add_note(self, message):
                raise HostileCleanupError("note")

        class BrokenSetattr(Exception):
            add_note = None
            def __setattr__(self, name, value):
                raise HostileCleanupError("setattr")

        class BrokenDetails(Exception):
            add_note = None
            _mckernel_secondary_errors = BrokenAppend()

        for kind in (HostileCleanupError, BrokenNote, BrokenSetattr, BrokenDetails):
            for broken_fallback in (False, True):
                with self.subTest(kind=kind.__name__, broken_fallback=broken_fallback):
                    first = kind("first")
                    fallback = BrokenAppend() if broken_fallback else backend.deque(maxlen=256)
                    with mock.patch.object(backend, "_SECONDARY_ERROR_FALLBACK", fallback):
                        backend._record_secondary_error(first, "cleanup", HostileCleanupError("secondary"))
                    self.assertIs(type(first), kind)
                    self.assertEqual(BaseException.args.__get__(first), ("first",))
                    if not broken_fallback:
                        self.assertTrue(all(type(item) is str and item == "cleanup diagnostic unavailable"
                                            for item in fallback))
        fallback = backend.deque(maxlen=256)
        with mock.patch.object(backend, "_secondary_message", side_effect=HostileCleanupError("formatter")), \
             mock.patch.object(backend, "_SECONDARY_ERROR_FALLBACK", fallback):
            backend._record_secondary_error(RuntimeError("first"), "cleanup", ValueError("secondary"))
        self.assertEqual(list(fallback), ["cleanup diagnostic unavailable"])
        with mock.patch.object(backend, "_SECONDARY_ERROR_FALLBACK", fallback):
            for _ in range(300):
                backend._record_secondary_error(HostileCleanupError("first"), "cleanup", ValueError("secondary"))
        self.assertEqual(list(fallback), ["cleanup diagnostic unavailable"] * 256)

    def test_secondary_formatter_never_reads_exception_class_name(self):
        class HostileType(type):
            def __getattribute__(cls, name):
                if name == "__name__":
                    raise HostileCleanupError("class name")
                return super().__getattribute__(name)

        class Hostile(HostileCleanupError, metaclass=HostileType):
            pass

        self.assertEqual(backend._secondary_message("action", Hostile("secondary")),
                         "action: <unrepresentable cleanup exception>")
        self.assertEqual(backend._secondary_message(Hostile("label"), Hostile("secondary")),
                         "cleanup failure")
        self.assertLessEqual(len(backend._secondary_message("x" * 1000, ValueError("y" * 10000))), 1154)

    def test_all_retirement_failures_and_broken_recording_preserve_action_order(self):
        class BrokenFallback:
            def append(self, item):
                raise HostileCleanupError("fallback")

        for block_fails in (False, True):
            with self.subTest(block_fails=block_fails):
                events = []
                first = HostileCleanupError("first")
                def fail(label):
                    events.append(label)
                    raise HostileCleanupError(label)
                def mask(how, signals):
                    if how == signal.SIG_BLOCK:
                        events.append("block")
                        if block_fails:
                            raise HostileCleanupError("block")
                        return set()
                    fail("restore")
                child = mock.Mock(pid=4321)
                child.wait.side_effect = lambda **kwargs: fail("reap")
                with mock.patch.object(backend, "_SECONDARY_ERROR_FALLBACK", BrokenFallback()), \
                     mock.patch.object(backend.signal, "pthread_sigmask", side_effect=mask), \
                     mock.patch.object(backend.signal, "setitimer", side_effect=lambda *args: fail("cancel")), \
                     mock.patch.object(backend.signal, "sigtimedwait", side_effect=lambda *args: fail("consume")), \
                     mock.patch.object(backend.os, "getpgid", side_effect=lambda pid: events.append("identity") or pid), \
                     mock.patch.object(backend.os, "killpg", side_effect=lambda pid, sig: fail(sig)), \
                     mock.patch.object(backend.os, "waitid", side_effect=lambda *args: fail("observe")):
                    backend._retire_untransferred(child, first)
                self.assertEqual(events, ["block", "cancel", "identity", signal.SIGTERM, "observe",
                                          "identity", signal.SIGKILL, "reap", "consume"] +
                                 ([] if block_fails else ["restore"]))
                self.assertIs(type(first), HostileCleanupError)
                self.assertEqual(BaseException.args.__get__(first), ("first",))

    def test_descriptor_cleanup_preserves_hostile_first_and_retries_every_fd(self):
        entry = os.stat_result((stat.S_IFREG, 7, 8, 1, os.getuid(), os.getgid(), 0, 0, 0, 0))
        for fail_action in ("identity", "close"):
            for supplied in (False, True):
                with self.subTest(fail_action=fail_action, supplied=supplied):
                    first = HostileCleanupError("first")
                    events = []
                    def action(kind, fd):
                        events.append((kind, fd))
                        if kind == fail_action:
                            raise first if fd == 101 else HostileCleanupError("later")
                        return entry
                    fds = [(fd, (8, 7)) for fd in (101, 102, 103)]
                    with mock.patch.object(backend.os, "fstat", side_effect=lambda fd: action("identity", fd)), \
                         mock.patch.object(backend.os, "close", side_effect=lambda fd: action("close", fd)):
                        if supplied:
                            backend._close_fds(fds, failure=first)
                        else:
                            try:
                                backend._close_fds(fds)
                            except BaseException as caught:
                                self.assertIs(caught, first)
                            else:
                                self.fail("first error was not raised")
                    per_fd = ["identity", "identity"] if fail_action == "identity" else ["identity", "close"] * 2
                    self.assertEqual(events, [(kind, fd) for fd in (101, 102, 103) for kind in per_fd])
                    self.assertEqual(fds, [])
                    self.assertEqual(BaseException.args.__get__(first), ("first",))

    def test_changed_fd_identity_is_never_closed_and_next_fd_is_processed(self):
        changed = os.stat_result((stat.S_IFREG, 99, 8, 1, os.getuid(), os.getgid(), 0, 0, 0, 0))
        owned = os.stat_result((stat.S_IFREG, 7, 8, 1, os.getuid(), os.getgid(), 0, 0, 0, 0))
        with mock.patch.object(backend.os, "fstat", side_effect=[changed, changed, owned]) as identities, \
             mock.patch.object(backend.os, "close") as close:
            with self.assertRaisesRegex(RuntimeError, "identity changed"):
                backend._close_fds([(101, (8, 7)), (102, (8, 7))])
        self.assertEqual(identities.call_args_list, [mock.call(101), mock.call(101), mock.call(102)])
        close.assert_called_once_with(102)

    def test_qmp_recovery_keeps_first_error_with_hostile_errno_and_close(self):
        first = HostileCleanupError("connect")
        class BrokenSocket(FakeSocket):
            def connect(self, path):
                raise first
            def close(self):
                self.closed = True
                raise HostileCleanupError("close")
        sock = BrokenSocket()
        try:
            self.qmp(sock).negotiate(1)
        except BaseException as caught:
            self.assertIs(caught, first)
        else:
            self.fail("connect failure was not raised")
        self.assertTrue(sock.closed)
        self.assertEqual(BaseException.args.__get__(first), ("connect",))

    def test_owner_term_failure_does_not_skip_kill_or_replace_first(self):
        first = HostileCleanupError("TERM")
        owner = backend.ProcessOwner(FakeProcess(), "stdout", "stderr")
        with mock.patch.object(owner, "_signal_group", side_effect=[first, HostileCleanupError("KILL")]) as group:
            try:
                owner.terminate()
            except BaseException as caught:
                self.assertIs(caught, first)
            else:
                self.fail("TERM failure was not raised")
        self.assertEqual(group.call_args_list,
                         [mock.call(signal.SIGTERM), mock.call(signal.SIGKILL, allow_absent=True)])
        self.assertEqual(BaseException.args.__get__(first), ("TERM",))

    def test_spawn_preserves_hostile_first_through_retirement_and_descriptor_failures(self):
        first = HostileCleanupError("ownership transfer")
        child = FakeProcess()
        events = []
        base_owner = backend.ProcessOwner
        class BrokenOwner(base_owner):
            def __setattr__(self, name, value):
                if name == "child" and value is child:
                    raise first
                super().__setattr__(name, value)
        # Opened descriptors are real; the first close attempt fails and the
        # identity-checked retry really closes each one.
        original_close = os.close
        close_calls = {}
        def close(fd):
            events.append(("close", fd))
            close_calls[fd] = close_calls.get(fd, 0) + 1
            if close_calls[fd] == 1:
                raise HostileCleanupError("close")
            original_close(fd)
        child.wait = lambda **kwargs: events.append("reap")
        before = set(os.listdir("/proc/self/fd"))
        factory = self._factory(lambda *args, **kwargs: child)
        with mock.patch.object(backend, "ProcessOwner", BrokenOwner), \
             mock.patch.object(backend.os, "close", side_effect=close), \
             mock.patch.object(backend.os, "getpgid", return_value=child.pid), \
             mock.patch.object(backend.os, "killpg", side_effect=lambda pid, sig: events.append(sig)), \
             mock.patch.object(backend.os, "waitid", side_effect=lambda *args: events.append("observe") or object()):
            try:
                factory(timeout=1)
            except BaseException as caught:
                self.assertIs(type(caught), backend.ProcessAcquisitionFailure)
                self.assertIs(caught.__cause__, first)
            else:
                self.fail("transfer failure was not raised")
        self.assertEqual(events[:4], [signal.SIGTERM, "observe", signal.SIGKILL, "reap"])
        self.assertEqual(len(close_calls), 2)
        self.assertEqual(list(close_calls.values()), [2, 2])
        self.assertEqual(set(os.listdir("/proc/self/fd")), before)
        self.assertEqual(BaseException.args.__get__(first), ("ownership transfer",))

    def test_unreadable_child_pid_does_not_skip_reap_or_alarm_cleanup(self):
        events = []
        class BrokenPid:
            @property
            def pid(self):
                events.append("pid")
                raise HostileCleanupError("pid")
            def wait(self, timeout):
                events.append("reap")
        first = RuntimeError("first")
        with mock.patch.object(backend.signal, "pthread_sigmask", side_effect=lambda *args: events.append("mask") or set()), \
             mock.patch.object(backend.signal, "setitimer", side_effect=lambda *args: events.append("cancel")), \
             mock.patch.object(backend.signal, "sigtimedwait", side_effect=lambda *args: events.append("consume")), \
             mock.patch.object(backend.os, "killpg") as kill:
            backend._retire_untransferred(BrokenPid(), first)
        kill.assert_not_called()
        self.assertEqual(events, ["mask", "cancel", "pid", "pid", "pid", "reap", "consume", "mask"])
        self.assertEqual(first.args, ("first",))

    def test_post_spawn_transfer_faults_retire_and_close(self):
        # No real child is launched: ordered waitid/killpg/wait observations
        # independently check retirement without running a guest or helper.
        for point in ("owner-child", "owner-pid", "stdout-close", "stderr-close",
                      "stdout-close-after", "stderr-close-after", "deadline", "alarm"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                path = str(Path(directory) / "qmp.sock")
                child = FakeProcess()
                events = []
                failure = RuntimeError(point)
                base_owner = backend.ProcessOwner
                class FaultOwner(base_owner):
                    def __setattr__(self, name, value):
                        if ((point == "owner-child" and name == "child" and value is child) or
                                (point == "owner-pid" and name == "pid" and value == child.pid)):
                            raise failure
                        super().__setattr__(name, value)
                original_close = os.close
                descriptors = []
                close_count = 0
                def close(fd):
                    nonlocal close_count
                    close_count += 1
                    if (point == "stdout-close" and close_count == 1 or
                            point == "stderr-close" and close_count == 2):
                        raise failure
                    if point == "alarm" and close_count == 1:
                        time.sleep(0.05)
                    original_close(fd)
                    if (point == "stdout-close-after" and close_count == 1 or
                            point == "stderr-close-after" and close_count == 2):
                        raise failure
                def popen(*args, **kwargs):
                    descriptors.extend([kwargs["stdout"], kwargs["stderr"]])
                    if point == "deadline":
                        time.sleep(0.025)
                    return child
                factory = backend.process_factory([backend.QEMU, "-qmp", "unix:" + path +
                                                    ",server=on,wait=off"], directory, popen_factory=popen)
                original_wait = child.wait
                def wait(timeout):
                    events.append("reap")
                    return original_wait(timeout)
                child.wait = wait
                with mock.patch.object(backend, "ProcessOwner", FaultOwner), \
                     mock.patch.object(backend.os, "close", side_effect=close), \
                     mock.patch.object(backend.os, "getpgid", return_value=child.pid), \
                     mock.patch.object(backend.os, "killpg", side_effect=lambda pid, sig: events.append(sig)), \
                     mock.patch.object(backend.os, "waitid", side_effect=lambda *args: events.append("observe") or object()):
                    if point == "alarm":
                        with self.assertRaises(backend.ProcessAcquisitionFailure) as raised, diagnostic._alarm(time.monotonic() + 0.01):
                            factory(timeout=1)
                    else:
                        with self.assertRaises(backend.ProcessAcquisitionFailure) as raised:
                            factory(timeout=0.01 if point == "deadline" else 1)
                    if point not in ("deadline", "alarm"):
                        self.assertIs(raised.exception.__cause__, failure)
                self.assertEqual(events, [signal.SIGTERM, "observe", signal.SIGKILL, "reap"])
                self.assertEqual(child.returncode, 0)
                for fd in descriptors:
                    with self.assertRaises(OSError) as raised: os.fstat(fd)
                    self.assertEqual(raised.exception.errno, errno.EBADF)

    def test_real_python_child_is_reaped_after_transfer_failure(self):
        # Released host-only microtest: one current-interpreter child, private
        # output, no network, fresh session, under a five-second alarm.
        children = []
        original_close = os.close
        first = RuntimeError("transfer failed after real Popen")
        def popen(argv, **kwargs):
            child = subprocess.Popen([sys.executable, "-c",
                "import os, signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "os.write(1, b'READY\\n'); time.sleep(4)"], **kwargs)
            children.append(child)
            try:
                end = time.monotonic() + 1
                while time.monotonic() < end:
                    if (Path(self.temp.name) / "qemu.stdout").read_bytes() == b"READY\n":
                        return child
                    time.sleep(0.005)
                raise TimeoutError("host test child did not become ready")
            except BaseException:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=1)
                raise
        def close(fd):
            if children and not getattr(close, "failed", False):
                close.failed = True
                raise first
            original_close(fd)
        before = set(os.listdir("/proc/self/fd"))
        factory = self._factory(popen)
        with diagnostic._alarm(time.monotonic() + 5):
            with mock.patch.object(backend.os, "close", side_effect=close):
                with self.assertRaises(backend.ProcessAcquisitionFailure) as raised:
                    factory(timeout=2)
        self.assertIs(raised.exception.__cause__, first)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].returncode, -signal.SIGKILL)
        with self.assertRaises(ProcessLookupError): os.kill(children[0].pid, 0)
        with self.assertRaises(ChildProcessError): os.waitpid(children[0].pid, os.WNOHANG)
        self.assertEqual(set(os.listdir("/proc/self/fd")), before)

    def test_group_signals_use_live_direct_child_identity(self):
        child = FakeProcess()
        out = Path(self.temp.name) / "qemu.stdout"
        err = Path(self.temp.name) / "qemu.stderr"
        out.write_bytes(b"")
        err.write_bytes(b"")
        owner = backend.ProcessOwner(child, out, err)
        with mock.patch.object(backend.os, "getpgid", return_value=child.pid) as getpgid, \
             mock.patch.object(backend.os, "killpg") as killpg:
            owner.terminate()
            owner.kill()
            self.assertEqual(killpg.call_count, 3)
            self.assertEqual([call.args[0] for call in killpg.call_args_list], [child.pid] * 3)
            self.assertEqual(getpgid.call_count, 3)
        self.assertEqual(owner.wait(1), 0)
        with self.assertRaisesRegex(RuntimeError, "reaped before group retirement"): owner.kill()
        owner.reaped = False
        with mock.patch.object(backend.os, "getpgid", return_value=child.pid + 1), \
             mock.patch.object(backend.os, "killpg") as killpg:
            with self.assertRaisesRegex(RuntimeError, "ownership changed"): owner.terminate()
            killpg.assert_not_called()
        with mock.patch.object(backend.os, "getpgid", return_value=child.pid), \
             mock.patch.object(backend.os, "killpg", side_effect=ProcessLookupError):
            with self.assertRaisesRegex(RuntimeError, "disappeared"): owner._signal_group(15)

    def test_qemu_evidence_is_fail_closed_and_retains_signal_status(self):
        child = FakeProcess()
        out = Path(self.temp.name) / "qemu.stdout"
        err = Path(self.temp.name) / "qemu.stderr"
        owner = backend.ProcessOwner(child, out, err,
                                     process_identity=(child.pid, child.pid, child.pid, 77),
                                     command=(backend.QEMU, "-qmp", "unix:test"))
        with self.assertRaisesRegex(RuntimeError, "not exactly reaped"):
            owner.qemu_evidence()
        child.wait = lambda timeout: setattr(child, "returncode", -signal.SIGKILL) or -signal.SIGKILL
        self.assertEqual(owner.wait(1), -signal.SIGKILL)
        self.assertEqual(owner.qemu_evidence(), {
            "argv": [backend.QEMU, "-qmp", "unix:test"], "pid": child.pid,
            "pgid": child.pid, "sid": child.pid, "starttime_ticks": 77,
            "returncode": -signal.SIGKILL})
        missing = backend.ProcessOwner(child, out, err)
        missing.reaped = True; missing.returncode = 0
        with self.assertRaisesRegex(RuntimeError, "command unavailable"):
            missing.qemu_evidence()

    def test_host_output_limit_is_recorded_after_reap_without_losing_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            (attempt / "serial.log").write_bytes(b"")
            (attempt / "debugcon.log").write_bytes(b"")
            out = attempt / "qemu.stdout"
            err = attempt / "qemu.stderr"
            out.write_bytes(b"x" * (diagnostic.MAX_JSON + 1))
            err.write_bytes(b"tail")
            child = FakeProcess()
            owner = backend.ProcessOwner(child, out, err,
                                         process_identity=(child.pid, child.pid, child.pid, 1),
                                         command=(backend.QEMU, "-qmp", "unix:test"))
            sock = FakeSocket()
            qmp = self.qmp(sock)
            with mock.patch.object(backend.os, "getpgid", return_value=child.pid), \
                 mock.patch.object(backend.os, "killpg"):
                with self.assertRaisesRegex(diagnostic.DiagnosticError, "host capture limit"):
                    diagnostic.exercise_lifecycle({}, attempt, lambda **kw: owner,
                                                  lambda **kw: qmp, timeout=1)
            result = json.loads((attempt / "result.json").read_text())
            self.assertTrue(result["cleanup"]["reaped"])
            self.assertEqual(out.stat().st_size, diagnostic.MAX_JSON + 1)
            self.assertEqual(err.read_bytes(), b"tail")
            self.assertTrue(json.loads((attempt / "qmp.transcript.json").read_text()))

    def test_qmp_status_timeout_malformed_reply_and_deadline_inputs(self):
        for statuses, error in (([{"status": "running", "running": True}], TimeoutError),
                                ([{"status": "shutdown", "running": True}], backend.QmpError),
                                ([{"status": "shutdown"}], backend.QmpError)):
            with self.subTest(statuses=statuses):
                qmp = self.qmp(FakeSocket(statuses))
                qmp.negotiate(1)
                qmp.resume(1)
                with self.assertRaises(error): qmp.wait_shutdown(0.01)
                qmp.close(1)
        bad = self.qmp(FakeSocket(bad_reply=True))
        with self.assertRaisesRegex(backend.QmpError, "identity mismatch"): bad.negotiate(1)
        bad.close(1)
        malformed = FakeSocket()
        malformed.pending = [b'{"QMP":{}}\n']
        def malformed_send(raw):
            malformed.sent.append(json.loads(raw))
            malformed.pending.append(b'{"return":{},"id":1,"id":1}\n')
        malformed.sendall = malformed_send
        qmp = self.qmp(malformed)
        with self.assertRaisesRegex(backend.QmpError, "duplicate QMP JSON key"): qmp.negotiate(1)
        qmp.close(1)
        for invalid in (0, -1, math.nan, math.inf, True):
            for action in ("negotiate", "resume", "wait_shutdown", "terminate", "close"):
                with self.subTest(invalid=invalid, action=action), self.assertRaises(ValueError):
                    getattr(self.qmp(FakeSocket()), action)(invalid)

    def test_negotiate_bad_greeting_and_cleanup_errors_do_not_hide_reaping(self):
        bad = self.qmp(FakeSocket(bad_greeting=True))
        with self.assertRaisesRegex(backend.QmpError, "greeting"): bad.negotiate(1)
        bad.close(1)

        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            (attempt / "serial.log").write_bytes(b"")
            (attempt / "debugcon.log").write_bytes(b"")
            process = FakeProcess(wait_fails=True)
            sock = FakeSocket(bad_reply=True, reject_quit=True, close_fails=True)
            qmp = self.qmp(sock)
            with self.assertRaisesRegex(diagnostic.DiagnosticError, "identity mismatch"):
                diagnostic.exercise_lifecycle({}, attempt, lambda **kw: process,
                                              lambda **kw: qmp, timeout=1)
            result = json.loads((attempt / "result.json").read_text())
            self.assertTrue(result["cleanup"]["reaped"])
            self.assertEqual(process.calls, ["terminate", "wait", "kill", "wait", "communicate"])
            self.assertEqual(result["failure"]["phase"], "lifecycle")
            self.assertIn("identity mismatch", result["failure"]["error"])
            self.assertTrue(any(x["phase"] == "qmp-close" for x in result["cleanup"]["errors"]))
            transcript = json.loads((attempt / "qmp.transcript.json").read_text())
            self.assertTrue(any(row["direction"] == "sent" for row in transcript))
            self.assertEqual((attempt / "qemu.stdout").read_bytes(), b"host stdout")
            self.assertTrue(sock.closed)

    def test_quit_failure_is_retained_with_reaped_process(self):
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            (attempt / "serial.log").write_bytes(b"")
            (attempt / "debugcon.log").write_bytes(b"")
            process = FakeProcess()
            sock = FakeSocket(reject_quit=True)
            qmp = self.qmp(sock)
            with self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.exercise_lifecycle({}, attempt, lambda **kw: process,
                                              lambda **kw: qmp, timeout=1)
            result = json.loads((attempt / "result.json").read_text())
            self.assertTrue(result["cleanup"]["reaped"])
            self.assertTrue(any(x["phase"] == "qmp-quit" for x in result["cleanup"]["errors"]))
            self.assertEqual(process.calls[:2], ["terminate", "wait"])
            self.assertTrue(sock.closed)


if __name__ == "__main__":
    unittest.main()
