"""Host process and QMP adapters for the native diagnostic lifecycle.

This is source-only infrastructure.  In particular, importing this module does
not stage an image or enable native_diagnostic.run_diagnostic.
"""

import math
import os
import signal
import socket
import stat
import subprocess
import time
import errno
from pathlib import Path

from qmp_capture import QmpError, QmpSession

QEMU = "/usr/libexec/qemu-kvm"


def _deadline(timeout):
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("positive finite timeout required")
    deadline = time.monotonic() + timeout
    if not math.isfinite(deadline) or deadline <= time.monotonic():
        raise ValueError("invalid absolute deadline")
    return deadline


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("backend absolute deadline expired")
    return remaining


class ProcessOwner:
    """Own QEMU's new session and bounded file-backed host streams."""

    def __init__(self, child, stdout_path, stderr_path, identities=None):
        self.child = child
        self.pid = child.pid if child is not None else None
        self.stdout_path = Path(stdout_path)
        self.stderr_path = Path(stderr_path)
        self.identities = identities
        self.reaped = False

    def _signal_group(self, signum, *, allow_absent=False):
        # A numeric PGID alone is unsafe after retirement and reuse.  Join it
        # to this still-owned direct child immediately before each signal.
        if self.reaped:
            raise RuntimeError("QEMU child reaped before group retirement")
        try:
            if os.getpgid(self.pid) != self.pid:
                raise RuntimeError("QEMU process group ownership changed")
            os.killpg(self.pid, signum)
        except ProcessLookupError:
            if not allow_absent:
                raise RuntimeError("QEMU group identity disappeared before signal")

    def terminate(self):
        import signal
        self._signal_group(signal.SIGTERM)
        # Kill the entire group before wait() reaps its leader. A descendant
        # may ignore TERM even when QEMU itself exits promptly.
        self._signal_group(signal.SIGKILL, allow_absent=True)

    def kill(self):
        import signal
        self._signal_group(signal.SIGKILL, allow_absent=True)

    def wait(self, timeout):
        result = self.child.wait(timeout=timeout)
        self.reaped = True
        return result

    def communicate(self, timeout):
        _deadline(timeout)
        if not self.reaped:
            raise RuntimeError("QEMU child has not been reaped")
        # Existing files are the primary evidence.  Read only a bounded prefix;
        # the caller checks the overflow byte and keeps both original files.
        def read(path, expected):
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(fd, "rb") as stream:
                item = os.fstat(stream.fileno())
                if (not stat.S_ISREG(item.st_mode) or item.st_uid != os.getuid() or
                        (expected is not None and (item.st_dev, item.st_ino) != expected)):
                    raise RuntimeError("QEMU evidence file identity changed")
                return stream.read(4 * 1024 * 1024 + 1)
        stdout = read(self.stdout_path, self.identities[0] if self.identities else None)
        stderr = read(self.stderr_path, self.identities[1] if self.identities else None)
        return stdout, stderr


def _private_directory(path):
    parent = os.stat(path, follow_symlinks=False)
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or
            parent.st_mode & 0o077 or os.path.realpath(path) != path):
        raise ValueError("private canonical owned attempt cwd required")
    return parent.st_dev, parent.st_ino


def _retire_untransferred(child, failure):
    """Retire a returned Popen whose ownership never reached the caller.

    WNOWAIT keeps the leader's PID reserved until the whole group is killed.
    An outstanding lifecycle alarm must not interrupt this recovery, nor may
    cleanup replace the original exception. Each cleanup action is independent.
    """
    errors = []
    def attempt(label, action):
        try:
            return action()
        except BaseException as exc:
            errors.append(label + ": " + repr(exc))

    mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
    try:
        signal.setitimer(signal.ITIMER_REAL, 0)
        pid = child.pid
        def group(signum):
            try:
                if os.getpgid(pid) != pid:
                    raise RuntimeError("untransferred child process group ownership changed")
                os.killpg(pid, signum)
            except ProcessLookupError:
                pass
        attempt("group TERM", lambda: group(signal.SIGTERM))
        def observe_exit():
            end = time.monotonic() + 0.2
            while time.monotonic() < end:
                if os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None:
                    return
                time.sleep(0.01)
        attempt("wait without reaping", observe_exit)
        attempt("group KILL", lambda: group(signal.SIGKILL))
        attempt("reap", lambda: child.wait(timeout=2))
    finally:
        # Consume any alarm that became pending before cancellation. Restoring
        # the mask must not replace the first failure with a second timeout.
        signal.sigtimedwait({signal.SIGALRM}, 0)
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
    for error in errors:
        failure.add_note("spawn cleanup " + error)


def _close_fds(fds, *, failure=None):
    """Close every retained descriptor, preserving the first observed error."""
    first = failure
    for fd, identity in fds:
        try:
            entry = os.fstat(fd)
            if identity is not None and (entry.st_dev, entry.st_ino) != identity:
                raise RuntimeError("owned descriptor identity changed")
            os.close(fd)
        except BaseException as exc:
            if first is None:
                first = exc
            elif exc is not first:
                first.add_note("descriptor close: " + repr(exc))
            # A signal can interrupt before close, or immediately after it.
            # Retry only if this descriptor still denotes our own file.
            try:
                entry = os.fstat(fd)
                if identity is None or (entry.st_dev, entry.st_ino) == identity:
                    os.close(fd)
            except OSError as retry:
                if retry.errno != errno.EBADF:
                    first.add_note("descriptor close retry: " + repr(retry))
            except BaseException as retry:
                first.add_note("descriptor close retry: " + repr(retry))
    fds.clear()
    if failure is None and first is not None:
        raise first


def process_factory(argv, cwd, *, popen_factory=subprocess.Popen):
    """Return a lifecycle factory for a reviewed direct-QEMU command.

    The caller must supply the already bound build_command argv and attempt
    directory.  No ambient environment, inherited descriptor, shell, or
    standard-input stream is passed to the child.
    """
    if (type(argv) not in (tuple, list) or not argv or
            any(type(arg) is not str or "\0" in arg for arg in argv) or
            argv[0] != QEMU):
        raise ValueError("exact direct-QEMU argv required")
    cwd = os.fspath(cwd)
    if not os.path.isabs(cwd):
        raise ValueError("absolute attempt cwd required")
    parent_identity = _private_directory(cwd)
    command = tuple(argv)
    qmp_path = os.path.join(cwd, "qmp.sock")
    if (command.count("-qmp") != 1 or command.index("-qmp") + 1 == len(command) or
            command[command.index("-qmp") + 1] != "unix:" + qmp_path + ",server=on,wait=off"):
        raise ValueError("QMP must use the private attempt socket")

    def spawn(*, timeout):
        deadline = _deadline(timeout)
        if _private_directory(cwd) != parent_identity:
            raise ValueError("attempt directory identity changed")
        if os.path.lexists(qmp_path):
            raise ValueError("QMP socket path exists before spawn")
        out_path = Path(cwd) / "qemu.stdout"
        err_path = Path(cwd) / "qemu.stderr"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        fds = []
        child = None
        try:
            out_fd = os.open(out_path, flags, 0o600)
            fds.append((out_fd, None))
            entry = os.fstat(out_fd)
            fds[-1] = (out_fd, (entry.st_dev, entry.st_ino))
            err_fd = os.open(err_path, flags, 0o600)
            fds.append((err_fd, None))
            entry = os.fstat(err_fd)
            fds[-1] = (err_fd, (entry.st_dev, entry.st_ino))
            # Construct all owner metadata before Popen can create a child.
            owner = ProcessOwner(None, out_path, err_path, tuple(item[1] for item in fds))
            _remaining(deadline)
            if _private_directory(cwd) != parent_identity or os.path.lexists(qmp_path):
                raise ValueError("attempt/QMP identity changed before spawn")
            child = popen_factory(command, stdin=subprocess.DEVNULL,
                                  stdout=out_fd, stderr=err_fd,
                                  shell=False, cwd=cwd, env={"LC_ALL": "C"},
                                  close_fds=True, pass_fds=(), start_new_session=True)
            owner.child = child
            owner.pid = child.pid
            _close_fds(fds)
            fds.clear()
            _remaining(deadline)
            return owner
        except BaseException as failure:
            if child is not None:
                try:
                    _retire_untransferred(child, failure)
                except BaseException as cleanup_failure:
                    failure.add_note("spawn retirement failed: " + repr(cleanup_failure))
            _close_fds(fds, failure=failure)
            raise

    return spawn


class QmpBackend:
    """Deadline-bound QMP methods expected by exercise_lifecycle."""

    def __init__(self, path, *, socket_factory=socket.socket, stat_factory=os.lstat):
        self.path = os.fspath(path)
        if not os.path.isabs(self.path):
            raise ValueError("absolute QMP socket path required")
        self.socket_factory = socket_factory
        self.stat_factory = stat_factory
        self.session = None
        self.negotiated = False
        self.parent_identity = _private_directory(os.path.dirname(self.path))

    def _socket_identity(self):
        if _private_directory(os.path.dirname(self.path)) != self.parent_identity:
            raise QmpError("QMP parent identity changed")
        entry = self.stat_factory(self.path)
        if not stat.S_ISSOCK(entry.st_mode) or entry.st_uid != os.getuid():
            raise QmpError("QMP path is not an owned socket")
        return (entry.st_dev, entry.st_ino)

    def _execute(self, command, deadline):
        if not self.negotiated or self.session is None:
            raise QmpError("QMP capabilities not negotiated")
        self.session.timeout = min(30.0, _remaining(deadline))
        result = self.session.execute(command)
        _remaining(deadline)
        return result

    def negotiate(self, timeout):
        deadline = _deadline(timeout)
        if self.session is not None:
            raise QmpError("QMP session already opened")
        owned_identity = None
        while True:
            _remaining(deadline)
            try:
                identity = self._socket_identity()
            except FileNotFoundError:
                if owned_identity is not None:
                    raise QmpError("QMP socket identity disappeared")
                time.sleep(min(0.05, _remaining(deadline)))
                continue
            if owned_identity is None:
                owned_identity = identity
            elif owned_identity != identity:
                raise QmpError("QMP socket identity changed during readiness")
            connection = self.socket_factory(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                connection.settimeout(min(30.0, _remaining(deadline)))
                connection.connect(self.path)
            except BaseException as error:
                try:
                    connection.close()
                except BaseException:
                    pass
                if not isinstance(error, OSError) or error.errno != errno.ECONNREFUSED:
                    raise
                if self._socket_identity() != owned_identity:
                    raise QmpError("QMP socket identity changed during refusal") from error
                time.sleep(min(0.05, _remaining(deadline)))
                continue
            try:
                _remaining(deadline)
                if self._socket_identity() != identity:
                    raise QmpError("QMP socket identity changed during connect")
                self.session = QmpSession(connection, timeout_seconds=min(30.0, _remaining(deadline)))
                greeting = self.session._receive(deadline)
                if "QMP" not in greeting:
                    raise QmpError("missing QMP greeting")
                self.session.timeout = min(30.0, _remaining(deadline))
                self.session.execute("qmp_capabilities")
                _remaining(deadline)
                self.negotiated = True
                return
            except BaseException:
                # Session remains owned for independently reported close. If
                # identity failed before session assignment, close the socket
                # while retaining the original failure.
                if self.session is None:
                    try:
                        connection.close()
                    except BaseException:
                        pass
                raise

    def resume(self, timeout):
        return self._execute("cont", _deadline(timeout))

    def wait_shutdown(self, timeout):
        deadline = _deadline(timeout)
        while True:
            state = self._execute("query-status", deadline)
            if type(state) is not dict or type(state.get("status")) is not str or type(state.get("running")) is not bool:
                raise QmpError("malformed QMP status")
            if state["status"] == "shutdown" and state["running"] is False:
                return {"status": "shutdown"}
            if state["status"] != "running" or state["running"] is not True:
                raise QmpError("unexpected QMP status")
            time.sleep(min(0.05, _remaining(deadline)))

    def terminate(self, timeout):
        deadline = _deadline(timeout)
        if self.session is None or not self.negotiated:
            return None
        return self._execute("quit", deadline)

    def close(self, timeout):
        deadline = _deadline(timeout)
        if self.session is None:
            return None
        result = self.session.close()
        _remaining(deadline)
        return result


def qmp_factory(path, *, socket_factory=socket.socket, stat_factory=os.lstat):
    """Return a lifecycle factory; opening the socket occurs at negotiate."""
    def open_backend(*, timeout):
        _deadline(timeout)
        return QmpBackend(path, socket_factory=socket_factory, stat_factory=stat_factory)
    return open_backend
