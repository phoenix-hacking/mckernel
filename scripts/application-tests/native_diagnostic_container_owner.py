#!/usr/bin/env python3
"""Own one diagnostic container. Protocol success is never OS acceptance.

Only the CLI is an execution entry point. Independent execution release is
still required. On uncertain removal it retains the lock and retries bounded
cleanup; it never returns an uncertain lease to the caller.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time
import uuid

IMAGE = "sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94"
REPO = "/home/holden/mckernel"
SCRATCH = "/home/holden/mckernel-work/scratch"
IMAGE_RECORD = "/home/holden/mckernel-work/logs/image-native.json"
IMAGE_RECORD_SHA256 = "c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a"
MANIFEST = SCRATCH + "/native-diagnostic-manifest-20260928-3/manifest.json"
MANIFEST_SHA256 = "ab2905811ae10eda6ba6d4ca7d023b0cc50fdaa7520968e45c2b41c733a1ecc6"
RUNNER = REPO + "/scripts/application-tests/native_diagnostic_runner.py"
SELF = REPO + "/scripts/application-tests/native_diagnostic_container_owner.py"
LOCK = "/run/lock/mckernel-development.lock"
QEMU = "/usr/libexec/qemu-kvm"
QEMU_SHA256 = "5c1985041a27c64829d9ca18dd54c6ede039eafdef00c3abcd70479b03aca7d0"
# Bind the observer to the complete output of the pinned QEMU binary.  The
# distribution build suffix is part of the identity: accepting only the first
# line or a prefix could authorize a different emulator build.
QEMU_VERSION_STDOUT = (
    b"QEMU emulator version 10.1.0 (qemu-kvm-10.1.0-16.el10_2.5)\n"
    b"Copyright (c) 2003-2025 Fabrice Bellard and the QEMU Project developers\n"
)
SOURCE_HASHES = {
    RUNNER: "25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499",
    REPO + "/scripts/application-tests/native_diagnostic.py": "b92e6f92084accdaf6e459ee6cf2674b02ad31a7d377a69fe15d5549804823c5",
    REPO + "/scripts/application-tests/native_diagnostic_backend.py": "ffdde01883c77171d1512769e0c88f2539dda8f7da4bd22ae4e71f69f080a16b",
    REPO + "/scripts/application-tests/qmp_capture.py": "5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741",
}
CGROUP = {
    "/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us": "100000",
    "/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us": "400000",
    "/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes": "12884901888",
    "/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy": "1",
    "/sys/fs/cgroup/pids/mckernel-dev/pids.max": "512",
}
HEX = re.compile(r"[0-9a-f]{64}\Z")
LIMIT = 4 * 1024 * 1024
PREFIX = ["/usr/bin/sudo", "-A", "/usr/bin/docker"]


class OwnerError(RuntimeError):
    pass


class OwnerSignal(OwnerError):
    pass


OWNER_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def need(ok, message):
    if not ok:
        raise OwnerError(message)


def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def safe_error(exc):
    """Primitive type metadata only: never execute exception/user hooks."""
    try:
        cls = type(exc)
        if type(cls) is type:
            name = type.__getattribute__(cls, "__name__")
            if type(name) is str:
                return name[:128]
    except BaseException:
        pass
    return "BaseException"


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise OwnerError("nonfinite JSON")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def directory(path):
    raw = os.fspath(path)
    value = Path(raw)
    need(value.is_absolute() and str(value.resolve(strict=True)) == raw, "canonical directory")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in value.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def regular(path, maximum=LIMIT):
    path = Path(path)
    parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "regular bounded input")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        identity = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                    "st_size", "st_mtime_ns", "st_ctime_ns")
        # Reading may legitimately update atime; it is not content identity.
        need(all(getattr(before, key) == getattr(after, key) for key in identity) and
             len(raw) == before.st_size, "input changed while reading")
        return raw


def _digest(path):
    return hashlib.sha256(regular(path, 256 * 1024 * 1024)).hexdigest()


def _proc_starttime(pid):
    """Return the kernel start-time field from /proc/PID/stat.

    The comm field may contain spaces and closing parentheses, so splitting
    on whitespace alone is not an identity check.  A malformed record is a
    hard failure; an absent /proc record is reported by the caller as
    unavailable.
    """
    # procfs stat metadata is inherently volatile (notably ctime/size), so
    # use a bounded descriptor read rather than regular()'s disk-file
    # identity check.  The record itself is validated below.
    path = "/proc/%d/stat" % pid
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            raw = os.read(fd, 4097)
        finally:
            os.close(fd)
    except OSError:
        raise
    need(len(raw) <= 4096, "malformed owner /proc stat")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise OwnerError("malformed owner /proc stat") from exc
    close = text.rfind(")")
    need(close > 0 and text.startswith(str(pid) + " ("), "malformed owner /proc stat")
    fields = text[close + 2:].split()
    # The suffix starts at field 3; field 22 (starttime) is offset 19.
    need(len(fields) > 19 and fields[19].isdigit(), "malformed owner /proc stat")
    return int(fields[19])


def _outer_identity():
    pid = os.getpid()
    need(type(pid) is int and pid > 0, "invalid owner pid")
    identity = {"pid": pid, "pgid": os.getpgid(pid), "sid": os.getsid(pid)}
    for key in ("pgid", "sid"):
        need(type(identity[key]) is int and identity[key] > 0, "invalid owner process identity")
    try:
        identity["proc_starttime"] = _proc_starttime(pid)
    except OSError:
        # Some constrained environments do not expose /proc.  Retain the
        # process-group identity and make the absence explicit.
        identity["proc_starttime"] = None
    return identity


def private_parent(path):
    fd = directory(path)
    try:
        info = os.fstat(fd)
        need(info.st_uid == 1000 and info.st_gid == 1000 and stat.S_IMODE(info.st_mode) == 0o700,
             "attempt parent must be uid/gid1000 mode0700")
        need(Path(SCRATCH) in Path(path).parents, "attempt parent must be nested under scratch")
        return (info.st_dev, info.st_ino)
    finally:
        os.close(fd)


def write_exclusive(path, raw):
    path = Path(path)
    parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent)
        try:
            view = memoryview(raw)
            while view:
                count = os.write(fd, view)
                need(count > 0, "short evidence write")
                view = view[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(parent)
    finally:
        os.close(parent)


def one(raw):
    rows = strict_json(raw)
    need(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict, "one inspect row")
    return rows[0]


class CommandError(OwnerError):
    def __init__(self, message, stdout=b"", stderr=b""):
        super().__init__(message)
        self.stdout, self.stderr = stdout, stderr


class CommandChild:
    """Explicit spawn/reap ownership, with cancellation masked at transitions."""
    def __init__(self):
        self.pid = None
        self.reaped = False
        self.returncode = None
        self.stdout = None
        self.stderr = None
        self.write_fds = []

    def acquire(self, argv, env, child_mask):
        # Called with OWNER_SIGNALS blocked in the parent. POSIX spawn restores
        # the pre-acquisition mask in the child without Python preexec hooks.
        outputs = []
        try:
            for name in ("stdout", "stderr"):
                read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
                self.write_fds.append(write_fd)
                try:
                    stream = os.fdopen(read_fd, "rb", buffering=0)
                except BaseException:
                    os.close(read_fd)
                    raise
                setattr(self, name, stream)
                outputs.append(write_fd)
            actions = [(os.POSIX_SPAWN_OPEN, 0, "/dev/null", os.O_RDONLY, 0),
                       (os.POSIX_SPAWN_DUP2, outputs[0], 1),
                       (os.POSIX_SPAWN_DUP2, outputs[1], 2)]
            # Equivalent to close_fds=True, including externally inherited
            # descriptors. The owner is single-threaded during real execution.
            for value in os.listdir("/proc/self/fd"):
                fd = int(value)
                if fd > 2:
                    try:
                        fcntl.fcntl(fd, fcntl.F_GETFD)
                    except OSError:
                        continue
                    actions.append((os.POSIX_SPAWN_CLOSE, fd))
            # POSIX_SPAWN_SETPGROUP with zero creates a group led by the child
            # without requiring the setsid extension missing from host Python.
            self.pid = os.posix_spawn(argv[0], argv, dict(os.environ) if env is None else env,
                                      file_actions=actions, setpgroup=0, setsigmask=child_mask,
                                      setsigdef=OWNER_SIGNALS + (signal.SIGPIPE, signal.SIGXFSZ))
        finally:
            for fd in self.write_fds:
                os.close(fd)
            self.write_fds.clear()

    def wait(self, timeout):
        end = time.monotonic() + timeout
        while not self.reaped:
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, OWNER_SIGNALS)
            try:
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid:
                    # Cancellation stays deferred through exact reap ownership.
                    self.reaped = True
                    self.returncode = os.waitstatus_to_exitcode(status)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            if not self.reaped:
                need(time.monotonic() < end, "command wait timeout")
                time.sleep(min(0.01, max(0, end - time.monotonic())))
        return self.returncode

    def retire(self, timeout=1):
        if self.pid is not None and not self.reaped:
            # Only an unreaped direct child reserves this numeric group ID.
            failure = None
            try:
                os.killpg(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except BaseException as exc:
                failure = exc
            try:
                self.wait(timeout)
            except BaseException as exc:
                if failure is not None:
                    raise exc from failure
                raise
            if failure is not None:
                raise failure


class CommandLedger:
    """Keep direct-child ownership until exact waitpid completion."""
    def __init__(self):
        self.pending = set()
        self.errors = []

    def retire(self, child, timeout=1):
        try:
            child.retire(timeout)
        except BaseException as exc:
            self.errors.append(exc)
            cause = BaseException.__getattribute__(exc, "__cause__")
            if cause is not None:
                self.errors.append(cause)
        finally:
            if child.pid is None or child.reaped:
                self.pending.discard(child)

    def retire_pending(self, timeout=1):
        for child in tuple(self.pending):
            self.retire(child, timeout)
        need(not self.pending, "local Docker client retirement unresolved")


COMMAND_LEDGER = CommandLedger()


def bounded_command(argv, timeout, *, env=None, ledger=None):
    """Drain bounded pipes without communicate()'s unbounded memory capture."""
    need(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0, "command deadline")
    end = time.monotonic() + timeout
    output = [bytearray(), bytearray()]
    child = CommandChild()
    ledger = COMMAND_LEDGER if ledger is None else ledger
    need(not ledger.pending, "previous command child retirement unresolved")
    failure = None
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, OWNER_SIGNALS)
    try:
        ledger.pending.add(child)
        try:
            child.acquire(argv, env, mask)
        finally:
            # Ownership is already installed in the outer try/finally when a
            # signal pending during spawn is delivered by this restoration.
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((child.stdout, child.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map():
                remaining = end - time.monotonic()
                need(remaining > 0, "command timeout")
                for key, _ in selector.select(min(remaining, 0.1)):
                    block = os.read(key.fd, 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        output[key.data].extend(block[:LIMIT + 1 - len(output[key.data])])
                        need(len(output[key.data]) <= LIMIT, "command output limit")
            code = child.wait(timeout=max(0.001, end - time.monotonic()))
        return subprocess.CompletedProcess(argv, code, bytes(output[0]), bytes(output[1]))
    except BaseException as exc:
        failure = exc
        if type(exc) is OwnerSignal:
            raise
        raise CommandError(safe_error(exc), bytes(output[0]), bytes(output[1])) from exc
    finally:
        cleanup_mask = signal.pthread_sigmask(signal.SIG_BLOCK, OWNER_SIGNALS)
        try:
            if failure is not None:
                ledger.retire(child)
            elif child.reaped:
                ledger.pending.discard(child)
            for stream in (child.stdout, child.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except BaseException:
                        if failure is None:
                            raise
        finally:
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK, cleanup_mask)
            except BaseException:
                if failure is None:
                    raise


class DockerBackend:
    def __init__(self):
        self.children = CommandLedger()

    def call(self, argv, *, timeout):
        need(argv[:3] == PREFIX, "exact sudo Docker argv")
        need(os.getuid() == os.geteuid() == 0, "outer Docker owner must be root for command retirement")
        env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
        if "SUDO_ASKPASS" in os.environ:
            env["SUDO_ASKPASS"] = os.environ["SUDO_ASKPASS"]
        return bounded_command(argv, timeout, env=env, ledger=self.children)


def bound_manifest(path=MANIFEST):
    need(path == MANIFEST and _digest(path) == MANIFEST_SHA256, "manifest identity drift")
    for source, expected in SOURCE_HASHES.items():
        need(_digest(source) == expected, "source identity drift: " + source)
    source = REPO + "/scripts/application-tests/native_diagnostic.py"
    spec = importlib.util.spec_from_file_location("owner_bound_diagnostic", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # This strict loader binds kernel, modules, image, payload, collector,
    # derived initramfs and the complete staging final-map joins.
    return module, module.load_manifest(path)


def env_values(items):
    need(type(items) is list, "environment list")
    result = {}
    for item in items:
        need(type(item) is str and "=" in item and "\0" not in item, "environment entry")
        key, value = item.split("=", 1)
        need(key and key not in result and not key.startswith(("LD_", "PYTHONPATH", "PYTHONHOME")), "environment key")
        result[key] = value
    return result


class DiagnosticOwner:
    def __init__(self, attempt_parent, *, backend=None, nonce=None, clock=time.monotonic):
        need(type(attempt_parent) is str and str(Path(attempt_parent)) == attempt_parent, "canonical attempt parent spelling")
        self.parent = Path(attempt_parent)  # never silently canonicalize input
        self.backend = backend or DockerBackend()
        self.nonce = nonce or uuid.uuid4().hex
        need(type(self.nonce) is str and re.fullmatch(r"[0-9a-f]{32}", self.nonce), "owner nonce")
        self.name = "mckernel-native-diagnostic-" + self.nonce
        self.label = "mckernel.native-diagnostic.owner=" + self.nonce
        self.clock = clock
        self.container = None
        self.lock = None
        self.evidence = self.parent.with_name(self.parent.name + ".owner-" + self.nonce)
        self.attempt = self.parent / ("attempt-" + self.nonce)
        self.sequence = 0
        self.failure = None
        self.secondary = []
        self.secondary_omitted = 0
        self.may_exist = False
        self.create_issued = False
        self.create_completed = False
        self.sleep = time.sleep
        self.absent = False
        self.cleaning = False
        self.command_deadline = None
        self.pending_evidence = []
        self.pending_bytes = 0
        self.flushing = False
        self.signal_number = None
        self.outer_identity = None
        self.lock_identity = None
        self.cgroup_profile = None
        self.owner_queued = False
        self.owner_sha = _digest(SELF)

    def _remember(self, exc):
        if self.failure is None:
            self.failure = exc
        else:
            self._secondary(exc)

    def _secondary(self, exc):
        if len(self.secondary) < 256:
            self.secondary.append(safe_error(exc))
        else:
            self.secondary_omitted += 1

    def _write_exclusive(self, path, raw):
        write_exclusive(path, raw)

    def _queue(self, path, raw):
        need(type(raw) is bytes and self.pending_bytes + len(raw) <= 128 * 1024 * 1024 and
             len(self.pending_evidence) < 4096, "bounded evidence buffer exhausted")
        self.pending_evidence.append((path, raw))
        self.pending_bytes += len(raw)

    def _save(self, name, value):
        self._queue(self.evidence / name, (_json(value) + "\n").encode())

    def _queue_owner(self):
        if self.owner_queued:
            return
        need(self.outer_identity is not None, "owner identity unavailable")
        self._save("owner.json", {
            "owner_sha256": self.owner_sha, "name": self.name, "nonce": self.nonce,
            "attempt": str(self.attempt), "application_acceptance": False,
            "outer": self.outer_identity, "lock": self.lock_identity,
            "cgroup_profile": self.cgroup_profile,
        })
        self.owner_queued = True

    def _flush(self):
        """Only retired owners may enter a potentially blocking filesystem."""
        need(self.absent and self.lock is None and not self.flushing, "evidence flush before retirement or reentrant flush")
        self.flushing = True
        try:
            pending, self.pending_evidence = self.pending_evidence, []
            self.pending_bytes = 0
            for path, raw in pending:
                try:
                    self._write_exclusive(path, raw)
                except BaseException as exc:
                    self._remember(exc)
            # Publish status only after all earlier evidence writers finish.
            report = {"status": "FAIL" if self.failure is not None else "PROTOCOL_PASS",
                      "application_acceptance": False, "container": self.container,
                      "absence_verified": True, "lease_retained": False,
                      "signal_number": self.signal_number,
                      "failure": safe_error(self.failure) if self.failure is not None else None,
                      "secondary": self.secondary, "secondary_omitted": self.secondary_omitted}
            try:
                self._write_exclusive(self.evidence / "result.json", (_json(report) + "\n").encode())
            except BaseException as exc:
                self._remember(exc)
        finally:
            self.flushing = False

    def _call(self, argv, timeout=10, allow_failure=False):
        if self.command_deadline is not None:
            timeout = min(timeout, self.command_deadline - self.clock())
        need(timeout > 0, "command deadline exhausted")
        self.sequence += 1
        prefix = "%03d-%s" % (self.sequence, argv[0])
        command = PREFIX + argv
        result = None
        failure = None
        try:
            result = self.backend.call(command, timeout=timeout)
            need(type(result.returncode) is int and type(result.stdout) is bytes and type(result.stderr) is bytes,
                 "typed command result")
            need(len(result.stdout) <= LIMIT and len(result.stderr) <= LIMIT, "command output limit")
            if result.returncode and not allow_failure:
                raise OwnerError("docker command failed: " + argv[0])
        except BaseException as exc:
            failure = exc
        # Only bounded primitive bytes are queued while ownership is live.
        # No writer, fsync, exception formatting, or user callback runs here.
        command_failure = failure
        for suffix, raw in (("stdout", result.stdout if result is not None else failure.stdout if type(failure) is CommandError else b""),
                            ("stderr", result.stderr if result is not None else failure.stderr if type(failure) is CommandError else b"")):
            try:
                self._queue(self.evidence / (prefix + "." + suffix), raw)
            except BaseException as exc:
                if failure is None:
                    failure = exc
                else:
                    self._secondary(exc)
        try:
            self._save(prefix + ".json", {"argv": command, "timeout": timeout,
                       "returncode": result.returncode if result is not None else None,
                       "failure": safe_error(failure) if failure is not None else None})
        except BaseException as exc:
            if failure is None:
                failure = exc
            else:
                self._secondary(exc)
        if failure is not None:
            if self.cleaning and command_failure is None:
                self._remember(failure)
                return result
            raise failure
        return result

    def _lookup(self):
        filters = ["name=^/" + self.name + "$", "label=" + self.label]
        if self.container:
            filters.append("id=" + self.container)
        found = []
        for value in filters:
            result = self._call(["ps", "-aq", "--no-trunc", "--filter", value])
            ids = result.stdout.decode("ascii").splitlines()
            need(len(ids) <= 1 and all(HEX.fullmatch(item) for item in ids), "full unique container ID")
            found.append(ids)
        need(all(ids == found[0] for ids in found), "owner lookup ambiguity")
        if not found[0]:
            return None
        cid = found[0][0]
        need(self.container in (None, cid), "container ID changed")
        row = one(self._call(["inspect", cid]).stdout)
        self._owned(row, cid)
        return row

    def _owned(self, row, cid):
        need(HEX.fullmatch(cid) and row.get("Id") == cid and row.get("Name") == "/" + self.name,
             "container name/CID changed")
        need(row.get("Image") == IMAGE and row.get("Config", {}).get("Labels", {}).get(
             "mckernel.native-diagnostic.owner") == self.nonce, "container image/label changed")

    def _inside_args(self):
        return ["-B", SELF, "--inside", "--owner-sha256", self.owner_sha,
                "--attempt-parent", str(self.parent), "--nonce", self.nonce]

    def _create_argv(self):
        return ["create", "--pull=never", "--attach=stdout", "--attach=stderr", "--init", "--name", self.name, "--label", self.label,
                "--cpus=4", "--cpuset-cpus=2-5", "--cgroup-parent=/mckernel-dev",
                "--memory=12g", "--memory-swap=12g", "--pids-limit=512", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--read-only", "--network=none",
                "--user=1000:1000", "--ulimit", "core=0", "--ulimit", "nofile=4096:4096",
                "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m",
                "--mount", "type=bind,src=" + REPO + ",dst=" + REPO + ",readonly",
                "--mount", "type=bind,src=" + SCRATCH + ",dst=" + SCRATCH + ",readonly",
                "--mount", "type=bind,src=" + str(self.parent) + ",dst=" + str(self.parent),
                "--env", "HOME=/tmp", "--env", "TMPDIR=/tmp", "--env", "PYTHONDONTWRITEBYTECODE=1",
                "--workdir=" + str(self.parent), "--entrypoint=/usr/bin/python3", IMAGE, *self._inside_args()]

    def _profile(self, row, image):
        self._owned(row, self.container)
        need(row.get("Path") == "/usr/bin/python3" and same(row.get("Args"), self._inside_args()), "actual entrypoint")
        c, h = row.get("Config"), row.get("HostConfig")
        need(type(c) is dict and type(h) is dict, "complete container config")
        inherited = image["Config"]
        labels = dict(inherited.get("Labels") or {})
        labels["mckernel.native-diagnostic.owner"] = self.nonce
        expected = {"Hostname": self.container[:12], "Domainname": "", "User": "1000:1000",
                    "Image": IMAGE, "WorkingDir": str(self.parent), "Entrypoint": ["/usr/bin/python3"],
                    "Cmd": self._inside_args(), "Labels": labels, "Tty": False, "OpenStdin": False,
                    "StdinOnce": False, "AttachStdin": False, "AttachStdout": True, "AttachStderr": True}
        for key, value in expected.items():
            need(same(c.get(key), value), "Config." + key)
        allowed = set(expected) | {"Env", "Volumes", "ExposedPorts", "Healthcheck", "OnBuild", "StopSignal",
                                   "StopTimeout", "Shell", "ArgsEscaped", "NetworkDisabled", "MacAddress"}
        need(set(c) <= allowed, "unreviewed Config field")
        for key in ("Volumes", "ExposedPorts", "Healthcheck"):
            need(c.get(key) in (None, {}), "hidden Config." + key)
        need(c.get("OnBuild") in (None, []) and c.get("StopSignal") in (None, "", "SIGTERM") and
             c.get("StopTimeout") in (None, 10) and c.get("Shell") in (None, inherited.get("Shell")) and
             c.get("ArgsEscaped", False) is False and c.get("NetworkDisabled", False) is False and
             c.get("MacAddress", "") == "", "inherited Config defaults")
        env = env_values(inherited.get("Env") or [])
        env.update(HOME="/tmp", TMPDIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
        need(env_values(c.get("Env")) == env, "exact environment")
        expected_host = {"NetworkMode": "none", "Privileged": False, "ReadonlyRootfs": True,
            "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"], "Memory": 12884901888,
            "MemorySwap": 12884901888, "NanoCpus": 4000000000, "CpusetCpus": "2-5", "PidsLimit": 512,
            "CgroupParent": "/mckernel-dev", "Init": True, "PidMode": "", "UTSMode": "", "UsernsMode": "",
            "IpcMode": "private", "Runtime": "runc", "AutoRemove": False, "PublishAllPorts": False,
            "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
            "Tmpfs": {"/tmp": "rw,nodev,nosuid,size=256m"}, "ShmSize": 67108864, "OomScoreAdj": 0}
        for key, value in expected_host.items():
            need(same(h.get(key), value), "HostConfig." + key)
        empty = {"Binds", "ContainerIDFile", "Links", "PortBindings", "VolumesFrom", "CapAdd", "GroupAdd",
                 "Dns", "DnsOptions", "DnsSearch", "ExtraHosts", "Devices", "DeviceCgroupRules", "DeviceRequests",
                 "Sysctls", "StorageOpt", "Annotations", "VolumeDriver", "ConsoleSize", "LxcConf", "Cgroup",
                 "CpusetMems", "Isolation", "BlkioDeviceReadBps", "BlkioDeviceWriteBps", "BlkioDeviceReadIOps",
                 "BlkioDeviceWriteIOps", "BlkioWeightDevice"}
        zero = {"CpuShares", "CpuPeriod", "CpuQuota", "CpuRealtimePeriod", "CpuRealtimeRuntime",
                "MemoryReservation", "KernelMemory", "KernelMemoryTCP", "BlkioWeight", "CpuCount", "CpuPercent",
                "IOMaximumIOps", "IOMaximumBandwidth"}
        extras = {"Mounts", "Ulimits", "MaskedPaths", "ReadonlyPaths", "CgroupnsMode", "OomKillDisable",
                  "MemorySwappiness", "LogConfig"}
        need(set(h) <= set(expected_host) | empty | zero | extras, "unreviewed HostConfig field")
        for key in empty:
            allowed = (None, [0, 0]) if key == "ConsoleSize" else (None, "", [], {})
            need(key not in h or any(same(h[key], value) for value in allowed), "HostConfig." + key)
        for key in zero:
            need(key not in h or same(h[key], 0), "HostConfig." + key)
        need(h.get("CgroupnsMode") in ("host", "private", "") and
             any(same(h.get("OomKillDisable"), x) for x in (None, False)) and
             any(same(h.get("MemorySwappiness"), x) for x in (None, -1)), "namespace/OOM defaults")
        need(h.get("LogConfig") in ({"Type": "json-file", "Config": {}}, {"Type": "local", "Config": {}}), "local log sink")
        need(same(sorted(h.get("Ulimits", []), key=lambda x: x["Name"]),
             [{"Hard": 0, "Name": "core", "Soft": 0}, {"Hard": 4096, "Name": "nofile", "Soft": 4096}]), "ulimits")
        for key, minimum in (("MaskedPaths", {"/proc/kcore", "/proc/keys", "/proc/latency_stats", "/proc/timer_list", "/proc/scsi", "/sys/firmware"}),
                             ("ReadonlyPaths", {"/proc/bus", "/proc/fs", "/proc/irq", "/proc/sys", "/proc/sysrq-trigger"})):
            paths = h.get(key)
            need(type(paths) is list and all(type(p) is str and p.startswith(("/proc/", "/sys/")) and
                 ".." not in p.split("/") for p in paths) and len(paths) == len(set(paths)) and minimum <= set(paths), "protection paths")
        requested, actual = [], []
        for mount in h.get("Mounts", []):
            need(set(mount) <= {"Type", "Source", "Target", "ReadOnly", "Consistency", "BindOptions"} and
                 mount.get("Type") == "bind" and mount.get("Consistency", "") == "" and
                 mount.get("BindOptions") in (None, {}, {"Propagation": "rprivate"}) and
                 type(mount.get("ReadOnly", False)) is bool, "requested mount options")
            requested.append((mount.get("Source"), mount.get("Target"), mount.get("ReadOnly", False)))
        expected_mounts = [(REPO, REPO, True), (SCRATCH, SCRATCH, True), (str(self.parent), str(self.parent), False)]
        need(sorted(requested) == sorted(expected_mounts), "requested mount identities")
        tmpfs = 0
        for mount in row.get("Mounts", []):
            if mount.get("Type") == "tmpfs":
                need(mount.get("Destination") == "/tmp" and mount.get("RW") is True and mount.get("Source", "") == "", "tmpfs identity")
                tmpfs += 1
                continue
            need(set(mount) <= {"Type", "Source", "Destination", "Driver", "Mode", "RW", "Propagation", "Name"} and
                 mount.get("Type") == "bind" and type(mount.get("RW")) is bool and
                 mount.get("Propagation") == "rprivate" and mount.get("Driver", "") == "" and
                 mount.get("Name", "") == "", "actual mount options")
            actual.append((mount.get("Source"), mount.get("Destination"), not mount["RW"]))
        need(sorted(actual) == sorted(expected_mounts) and tmpfs <= 1, "actual mount identities")
        networks = row.get("NetworkSettings", {}).get("Networks")
        need(type(networks) is dict and set(networks) == {"none"}, "none network")
        need(all(networks["none"].get(key, "") == "" for key in
             ("IPAddress", "GlobalIPv6Address", "Gateway", "IPv6Gateway", "MacAddress")) and
             row["NetworkSettings"].get("Ports") in (None, {}), "no network endpoint")

    def _preflight(self, manifest):
        self.parent_identity = private_parent(str(self.parent))
        need(not os.path.lexists(self.attempt), "inner attempt already exists")
        self.diagnostic, self.manifest = bound_manifest(manifest)
        need(_digest(IMAGE_RECORD) == IMAGE_RECORD_SHA256, "image record identity")
        retained = one(regular(IMAGE_RECORD))
        profile = {}
        for path, value in CGROUP.items():
            # cgroup pseudo-files advertise st_size=0 despite readable content.
            with open(path, "rb") as stream:
                raw = stream.read(4097)
            need(len(raw) <= 4096 and raw.decode().strip() == value, "cgroup profile drift")
            profile[path] = value
        self.cgroup_profile = profile
        return retained

    def _acquire(self):
        self.lock = os.open(LOCK, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            info = os.fstat(self.lock)
            need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1, "root regular development lock")
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_identity = {"dev": info.st_dev, "ino": info.st_ino,
                                  "mode": stat.S_IMODE(info.st_mode), "nlink": info.st_nlink,
                                  "uid": info.st_uid, "gid": info.st_gid}
        except BaseException:
            os.close(self.lock)
            self.lock = None
            raise

    def _release(self):
        need(self.absent and not self.backend.children.pending and
             (not self.create_issued or self.create_completed), "cannot release uncertain container lease")
        if self.lock is not None:
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, OWNER_SIGNALS)
            try:
                fcntl.flock(self.lock, fcntl.LOCK_UN)
                os.close(self.lock)
                self.lock = None
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)

    def _cleanup(self):
        """One 15-second cleanup attempt; retain the lock on uncertainty."""
        self.absent = False
        end = self.clock() + 15
        self.cleaning, self.command_deadline = True, end
        try:
            self.backend.children.retire_pending(timeout=min(1, end - self.clock()))
            row = self._lookup()
            if row is not None:
                self.container = row["Id"]
                # Authentication of the exact name, label and ID resolves an
                # issued create even when its client response was lost.
                self.create_completed = True
                removed = False
                for args, allowance in ((["stop", "--time=2"], 4), (["kill"], 2),
                                        (["wait"], 1), (["logs", "--timestamps"], 1),
                                        (["inspect"], 1), (["rm", "--force"], 4)):
                    try:
                        need(self.clock() < end, "cleanup deadline")
                        result = self._call(args + [self.container], timeout=min(allowance, end - self.clock()), allow_failure=True)
                        # stop/kill return nonzero for an already stopped container;
                        # rm and final absence remain authoritative.
                        if args[0] == "rm":
                            need(result.returncode == 0, "container removal failed")
                            removed = True
                    except BaseException as exc:
                        self._remember(exc)
                need(removed, "authenticated container removal incomplete")
            need(self.clock() < end, "cleanup deadline")
            empty = self._lookup() is None
            need(empty and self.clock() <= end, "container remains after cleanup")
            need(not self.create_issued or self.create_completed,
                 "issued create remains unresolved despite empty lookup")
            need(not self.backend.children.pending, "local Docker client retirement unresolved")
            self.absent = True
        except BaseException as exc:
            self.absent = False
            self._remember(exc)
        finally:
            errors, self.backend.children.errors = self.backend.children.errors, []
            for exc in errors:
                self._remember(exc)
            self.cleaning, self.command_deadline = False, None
        return self.absent

    def _inner_result(self, started):
        expected = _json({"attempt": self.attempt.name, "case_id": self.manifest["case_id"], "status": "PROTOCOL_PASS"}) + "\n"
        need(started.stdout == expected.encode() and started.stderr == b"", "inner result mismatch")
        raw = regular(self.attempt / "result.json")
        self._queue(self.evidence / "inner-result.json", raw)
        result = strict_json(raw)
        need(result.get("status") == "PROTOCOL_PASS" and result.get("application_acceptance") is False and
             result.get("mckernel_application_executed") is False and result.get("case_id") == self.manifest["case_id"] and
             same(result.get("cleanup"), {"reaped": True, "errors": []}) and same(result.get("capture_errors"), []), "inner cleanup/result failure")
        captures = {}
        texts = {}
        for name in ("serial.log", "debugcon.log", "qemu.stdout", "qemu.stderr", "qmp.transcript.json"):
            data = regular(self.attempt / name, 24 * 1024 * 1024 if name == "qmp.transcript.json" else LIMIT)
            self._queue(self.evidence / name, data)
            captures[name] = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            if name in ("serial.log", "debugcon.log"):
                texts[name[:-4]] = data.decode("utf-8")
            if name == "qmp.transcript.json":
                need(type(strict_json(data)) is list, "QMP transcript shape")
        observation = result.get("observation", {})
        need(observation.get("serial") == texts["serial"] and observation.get("debugcon") == texts["debugcon"] and
             observation.get("teardown") is True, "capture observation join")
        replay = self.diagnostic.evaluate(self.manifest, observation)
        need(same(replay, {k: v for k, v in result.items() if k not in ("cleanup", "capture_errors")}), "inner oracle replay")
        need(not os.path.lexists(self.attempt / "first-failure.jsonl"), "inner failure journal exists")
        self._save("capture-bindings.json", captures)

    def run(self, *, manifest=MANIFEST, deadline=360):
        need(type(deadline) in (int, float) and math.isfinite(deadline) and 330 <= deadline <= 600, "outer deadline must exceed inner cleanup")
        retained = self._preflight(manifest)
        self.outer_identity = _outer_identity()
        # The evidence sibling is outside the only writable bind mount.
        self.evidence.mkdir(mode=0o700)
        info = self.evidence.stat()
        need(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
             "exclusive owner evidence identity")
        started = None
        try:
            # Until the lookup completes, a previous exact owner may exist.
            self.may_exist = True
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, OWNER_SIGNALS)
            try:
                self._acquire()
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            # Queue the complete ownership record only after the root lock is
            # held.  This remains memory-only until verified retirement.
            self._queue_owner()
            existing = self._lookup()
            if existing is not None:
                self.container = existing["Id"]
                raise OwnerError("preexisting owner container")
            image = one(self._call(["image", "inspect", IMAGE]).stdout)
            need(image.get("Id") == IMAGE and image.get("Architecture") == "amd64" and image.get("Os") == "linux" and
                 same(image.get("Config"), retained.get("Config")) and same(image.get("RootFS"), retained.get("RootFS")), "image Config/RootFS drift")
            need(private_parent(str(self.parent)) == self.parent_identity and not os.path.lexists(self.attempt), "attempt changed before create")
            self.may_exist, self.absent = True, False
            self.create_issued = True
            created = self._call(self._create_argv())
            cid = created.stdout.decode("ascii").strip()
            need(HEX.fullmatch(cid) and created.stdout == (cid + "\n").encode(), "create requires full container ID")
            self.container = cid
            self.create_completed = True
            row = self._lookup()
            need(row is not None, "created container missing")
            self._profile(row, image)
            need(row.get("State", {}).get("Status") == "created" and row["State"].get("Running") is False, "container started before verification")
            started = self._call(["start", "--attach", self.container], timeout=deadline)
            waited = self._call(["wait", self.container], timeout=5)
            need(waited.stdout == b"0\n" and waited.stderr == b"", "container wait status")
            final = self._lookup()
            need(final is not None, "final container missing")
            self._profile(final, image)
            state = final.get("State", {})
            self._save("state.json", state)
            need(state.get("Status") == "exited" and all(state.get(k) is False for k in
                 ("Running", "Paused", "Restarting", "OOMKilled", "Dead")) and state.get("Error", "") == "" and
                 same(state.get("ExitCode"), 0), "container state failed")
        except BaseException as exc:
            self._remember(exc)
        finally:
            if self.may_exist and self.lock is not None:
                # Capture is attempted even after timeout, start or inspect failure.
                if self.container is not None:
                    for args in (["wait", self.container], ["logs", "--timestamps", self.container], ["inspect", self.container]):
                        try:
                            self._call(args, timeout=3)
                        except BaseException as exc:
                            self._remember(exc)
                self._cleanup()
            else:
                # Acquisition failed; we have no authority to assert absence.
                self.absent = False
            if not self.owner_queued:
                try:
                    # Preserve process/cgroup identity even when lock
                    # acquisition itself failed; no lock claim is recorded.
                    self._queue_owner()
                except BaseException as exc:
                    self._remember(exc)
            if self.absent:
                try:
                    self._release()
                except BaseException as exc:
                    self._remember(exc)
            if self.absent and self.lock is None:
                if started is not None:
                    try:
                        self._inner_result(started)
                    except BaseException as exc:
                        self._remember(exc)
                self._flush()
        if self.failure is not None:
            raise self.failure
        return {"status": "PROTOCOL_PASS", "container": self.container, "application_acceptance": False}


def _inside(parent, nonce, owner_sha):
    need(os.getuid() == os.geteuid() == 1000, "inside uid1000 required")
    need(HEX.fullmatch(owner_sha) and _digest(SELF) == owner_sha, "inside owner hash drift")
    need(re.fullmatch(r"[0-9a-f]{32}", nonce), "inside nonce")
    private_parent(parent)
    need(not os.path.lexists(Path(parent) / ("attempt-" + nonce)), "inside attempt exists")
    bound_manifest()
    need(_digest(QEMU) == QEMU_SHA256, "inside QEMU hash drift")
    version = bounded_command([QEMU, "--version"], 5)
    need(version.returncode == 0 and version.stderr == b"" and version.stdout == QEMU_VERSION_STDOUT,
         "inside QEMU version drift")
    os.execve("/usr/bin/python3", ["/usr/bin/python3", "-B", RUNNER, "--manifest", MANIFEST,
              "--attempt-parent", parent, "--attempt-name", "attempt-" + nonce, "--timeout", "300"],
              {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"})


def execute_owner(owner):
    """Install signal ownership before any acquisition, lookup or create."""
    previous = {number: signal.getsignal(number) for number in OWNER_SIGNALS}
    def interrupted(number, frame):
        # The first signal becomes the primary error; subsequent signals cannot
        # interrupt retirement, recovery, or post-retirement evidence flushing.
        for item in OWNER_SIGNALS:
            signal.signal(item, signal.SIG_IGN)
        owner.signal_number = number
        raise OwnerSignal("outer owner interrupted")
    for number in OWNER_SIGNALS:
        signal.signal(number, interrupted)
    try:
        owner.run()
    except BaseException as exc:
        owner._remember(exc)
    finally:
        # Keep the same lock and exact owner identity while Docker is unavailable.
        # Each retry has a fresh bounded 15-second cleanup allowance.
        delay = 1
        recoveries = 0
        for signum in OWNER_SIGNALS:
            signal.signal(signum, signal.SIG_IGN)
        while owner.lock is not None and not owner.absent:
            time.sleep(delay)
            owner._cleanup()
            recoveries += 1
            if owner.absent:
                try:
                    owner._release()
                except BaseException as exc:
                    owner._remember(exc)
            delay = min(60, delay * 2)
        if recoveries:
            try:
                owner._save("recovery-result.json", {"status": "FAIL", "application_acceptance": False,
                    "absence_verified": owner.absent, "lease_retained": owner.lock is not None,
                    "recovery_attempts": recoveries, "failure": safe_error(owner.failure)})
            except BaseException as exc:
                owner._remember(exc)
            if owner.absent and owner.lock is None:
                owner._flush()
        for number, handler in previous.items():
            signal.signal(number, handler)
    if owner.failure is not None:
        raise owner.failure
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--attempt-parent", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--owner-sha256", required=True)
    args = parser.parse_args(argv)
    need(HEX.fullmatch(args.owner_sha256) and _digest(SELF) == args.owner_sha256, "reviewed owner identity")
    if args.inside:
        _inside(args.attempt_parent, args.nonce, args.owner_sha256)
        return 0
    need(os.getuid() == os.geteuid() == 0, "root outer owner required")
    execute_owner(DiagnosticOwner(args.attempt_parent, nonce=args.nonce))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
