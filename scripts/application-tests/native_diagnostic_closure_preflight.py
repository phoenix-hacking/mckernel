#!/usr/bin/env python3
"""Bounded Linux host diagnostic for retained startup.argv-empty; no guest credit."""
from __future__ import annotations

import argparse
import errno
import hashlib
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
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

REPO = Path(__file__).resolve().parents[2]
COMPILE = REPO / "docs/verification/stability-packet001-compile-20260913-1.json"
COMPILE_SHA256 = "65d12c45da7677f95436a0603e5e471aa22f03de6cee84554c1fdb2d277382f6"
ROOT = Path("/home/holden/mckernel-work/scratch/native-ultra-futex-guest-20260909-2026091302/root")
COMPILE_ROOT = Path("/home/holden/mckernel-work/scratch/stability-packet001-compile-20260913-1")
SOURCE = REPO / "scripts/application-tests/reviewed/packet-001-v3/startup.argv-empty.c"
ORACLE = REPO / "scripts/application-tests/reviewed/packet-001-v3/startup.argv-empty.oracle.json"
EXPECTED_STDOUT = bytes.fromhex("7b2263617365223a22737461727475702e617267762d656d707479222c2261726763223a342c2261726776223a5b22617070222c2241222c22222c2242225d2c227465726d696e61746f725f69735f6e756c6c223a747275657d0a")
ENV = {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"}
STREAM_LIMIT = 65536
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _open_dir(path: Path) -> int:
    """Walk every component without following links; never trust resolve()."""
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be absolute without traversal")
    fd = os.open("/", DIR_FLAGS)
    try:
        def check_ancestor(opened: int) -> None:
            st = os.fstat(opened)
            mode = stat.S_IMODE(st.st_mode)
            if st.st_uid not in (0, os.geteuid()):
                raise ValueError("directory ancestor has foreign owner")
            if mode & 0o022 and st.st_uid == 0 and not (mode & stat.S_ISVTX):
                raise ValueError("root-owned directory ancestor is writable without sticky protection")
        check_ancestor(fd)
        for part in path.parts[1:]:
            child = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
            check_ancestor(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_bound(path: Path, size: int, sha256: str, mode: int) -> tuple[bytes, dict]:
    parent = _open_dir(path.parent)
    try:
        fd = os.open(path.name, FILE_FLAGS, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"not regular: {path}")
            if before.st_size != size or stat.S_IMODE(before.st_mode) != mode:
                raise ValueError(f"input size/mode drift: {path}")
            data = bytearray()
            while len(data) <= size:
                chunk = os.read(fd, min(1024 * 1024, size + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                before.st_ctime_ns, before.st_mode) != (after.st_dev, after.st_ino,
                after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_mode):
                raise ValueError(f"input changed during read: {path}")
            if len(data) != size or _sha(data) != sha256:
                raise ValueError(f"input identity drift: {path}")
            # Detect a pathname swap while the descriptor was being read.
            named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != (after.st_dev, after.st_ino):
                raise ValueError(f"input pathname swapped: {path}")
            return bytes(data), {"path": str(path), "size": size, "mode": mode,
                                 "sha256": sha256, "device": after.st_dev, "inode": after.st_ino}
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _write_all(fd: int, data: bytes, on_write: Callable[[int], None] | None = None) -> None:
    """Persist every byte or fail; report only bytes actually accepted by write."""
    view = memoryview(data)
    while view:
        try:
            count = os.write(fd, view)
        except InterruptedError:
            continue
        if count <= 0 or count > len(view):
            raise OSError(errno.EIO, "write made no progress or returned an invalid count")
        if on_write:
            on_write(count)
        view = view[count:]


def _write_bytes(dir_fd: int, name: str, data: bytes, mode: int = 0o400) -> int:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=dir_fd)
    try:
        _write_all(fd, data)
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(dir_fd)
    return os.open(name, FILE_FLAGS, dir_fd=dir_fd)


def _hash_fd(fd: int, size: int) -> str:
    data = bytearray()
    while len(data) <= size:
        block = os.pread(fd, min(1024 * 1024, size + 1 - len(data)), len(data))
        if not block:
            break
        data.extend(block)
    if len(data) != size:
        raise ValueError("private input size drift")
    return _sha(data)


def _write_json(dir_fd: int, name: str, record: dict) -> None:
    # Only the final name is authoritative. A staging artifact is never a result.
    # Keep it on every failure, including no-replace collisions and sync errors.
    staging = name + ".staging"
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=dir_fd)
    linked = False
    try:
        raw = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()
        _write_all(fd, raw)
        os.fsync(fd)
        # link is an atomic no-replace publication within this pinned directory.
        os.link(staging, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)
        linked = True
        os.fsync(dir_fd)
    except BaseException:
        if linked:
            # Invalidate both links first, so even failed unlink cannot leave a
            # valid-looking PASS at the final name after a publication failure.
            try:
                os.ftruncate(fd, 0)
            finally:
                os.unlink(name, dir_fd=dir_fd)
        raise
    finally:
        os.close(fd)
    # Retain the staging link even on success: removing it would introduce a
    # second directory-sync failure after result publication had committed.


def _check_parent(path: Path, fd: int) -> None:
    named = os.lstat(path)
    opened = os.fstat(fd)
    if not stat.S_ISDIR(named.st_mode) or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
        raise ValueError("output parent replaced or aliased")
    if opened.st_uid != os.geteuid() or stat.S_IMODE(opened.st_mode) != 0o700:
        raise ValueError("output parent must be owned by caller with mode 0700")


def _readelf(path: str, option: str, pass_fds: tuple[int, ...]) -> str:
    return subprocess.run(["/usr/bin/readelf", option, path], text=True, capture_output=True,
                          timeout=5, check=True, pass_fds=pass_fds).stdout


def _version_needs(output: str) -> dict[str, list[str]]:
    if "Version needs section" not in output:
        return {}
    section = output.split("Version needs section", 1)[1]
    needs: dict[str, list[str]] = {}
    provider = None
    for line in section.splitlines():
        match = re.search(r"\bFile:\s*(\S+)\s+Cnt:\s*(\d+)", line)
        if match:
            provider = match[1]
            if provider in needs:
                raise ValueError("duplicate ELF version provider")
            needs[provider] = []
        for version in re.findall(r"\bName:\s*(\S+)", line):
            if provider is None:
                raise ValueError("ELF version need without provider")
            needs[provider].append(version)
    return needs


def inspect_elf(payload_fd: int, libc_fd: int, loader_fd: int) -> dict:
    """Check requested interpreter, dependencies and provider version definitions."""
    fds = (payload_fd, libc_fd, loader_fd)
    payload = f"/proc/self/fd/{payload_fd}"
    program = _readelf(payload, "-lW", fds)
    dynamic = _readelf(payload, "-dW", fds)
    version = _readelf(payload, "-VW", fds)
    interp = re.findall(r"Requesting program interpreter: ([^\]]+)", program)
    needed = re.findall(r"\(NEEDED\).*Shared library: \[([^\]]+)\]", dynamic)
    requested_by_provider = _version_needs(version)
    requested = sorted({v for values in requested_by_provider.values() for v in values})
    if interp != ["/lib64/ld-linux-x86-64.so.2"] or needed != ["libc.so.6"]:
        raise ValueError(f"unexpected ELF closure: interpreter={interp}, needed={needed}")
    providers = {}
    versions = {"payload": version}
    needed_by_object = {"payload": needed}
    for name, fd in (("libc", libc_fd), ("loader", loader_fd)):
        output = _readelf(f"/proc/self/fd/{fd}", "-VW", fds)
        versions[name] = output
        definitions = (output.split("Version definition section", 1)[1].split("Version needs section", 1)[0]
                       if "Version definition section" in output else "")
        providers[name] = sorted(set(re.findall(r"\bName:\s*(\S+)", definitions)))
        provider_dynamic = _readelf(f"/proc/self/fd/{fd}", "-dW", fds)
        needed_by_object[name] = re.findall(r"\(NEEDED\).*Shared library: \[([^\]]+)\]", provider_dynamic)
    if needed_by_object["libc"] != ["ld-linux-x86-64.so.2"] or needed_by_object["loader"]:
        raise ValueError(f"unexpected provider ELF closure: {needed_by_object}")
    names = {"libc.so.6": "libc", "ld-linux-x86-64.so.2": "loader"}
    needs = {name: _version_needs(output) for name, output in versions.items()}
    for consumer, requirements in needs.items():
        for provider, required in requirements.items():
            if provider not in needed_by_object[consumer] or provider not in names:
                raise ValueError(f"unexpected version provider: {consumer}: {provider}")
            absent = sorted(set(required) - set(providers[names[provider]]))
            if absent:
                raise ValueError(f"unprovided GLIBC versions: {consumer} requires {provider}: {absent}")
    return {"interpreter": interp[0], "needed": needed, "requested_versions": requested,
            "provider_versions": providers, "version_needs": needs,
            "readelf_sha256": {"program": _sha(program.encode()), "dynamic": _sha(dynamic.encode()),
                               "version": _sha(version.encode())}}


@dataclass(frozen=True)
class Spec:
    payload: Path
    loader: Path
    libc: Path
    source: Path
    oracle: Path
    expected: dict
    inspect: bool = True


def retained_spec() -> Spec:
    raw, _ = _read_bound(COMPILE, 56667, COMPILE_SHA256, 0o664)
    record = json.loads(raw)
    case = next(c for c in record["cases"] if c["case_id"] == "startup.argv-empty")
    if (case["compile_status"], case["executable"]["path"], case["source"]["path"],
        case["oracle"]["path"], case["interpreter"]) != (
            "PASS", "/work/stability-packet001-compile-20260913-1/startup.argv-empty/payload",
            "/work/stability-packet001-compile-20260913-1/startup.argv-empty/startup.argv-empty.c",
            "/work/stability-packet001-compile-20260913-1/startup.argv-empty/oracle.json",
            "/lib64/ld-linux-x86-64.so.2"):
        raise ValueError("retained compile record path drift")
    libs = {Path(row["captured"]["path"]).name: row["captured"] for row in case["runtime_libraries"]}
    expected = {"payload": {**case["executable"], "mode": 0o755},
                "loader": {**libs["ld-linux-x86-64.so.2"], "mode": 0o755},
                "libc": {**libs["libc.so.6"], "mode": 0o755},
                "source": {**case["source"], "mode": 0o664},
                "oracle": {**case["oracle"], "mode": 0o664}}
    return Spec(COMPILE_ROOT / "startup.argv-empty/payload", ROOT / "lib64/ld-linux-x86-64.so.2",
                ROOT / "lib64/libc.so.6", SOURCE, ORACLE, expected)


def _group_active(pgid: int) -> bool:
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(") ", 1)[1].split()
            if int(fields[2]) == pgid and fields[0] not in ("Z", "X"):
                return True
        except (FileNotFoundError, PermissionError, ValueError, IndexError):
            continue
    return False


def _leader_exited(pid: int) -> bool:
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is not None


def _quiesce(proc: subprocess.Popen) -> bool:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    until = time.monotonic() + 0.25
    while time.monotonic() < until and _group_active(proc.pid):
        time.sleep(0.01)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    until = time.monotonic() + 2.0
    while time.monotonic() < until and _group_active(proc.pid):
        time.sleep(0.01)
    quiet = not _group_active(proc.pid)
    proc.wait(timeout=2)
    return quiet


def _drain(proc: subprocess.Popen, out_fd: int, err_fd: int, timeout: float,
           sizes: dict[str, int]) -> tuple[bool, bool, bool]:
    selector = selectors.DefaultSelector()
    def capture(name: str, target: int, data: bytes) -> None:
        def account(count: int) -> None:
            sizes[name] += count
        _write_all(target, data, account)
    for name, pipe in (("stdout", proc.stdout), ("stderr", proc.stderr)):
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ, (name, out_fd if name == "stdout" else err_fd))
    deadline = time.monotonic() + timeout
    timed_out = overflow = False
    try:
        while True:
            if _leader_exited(proc.pid):
                break
            if time.monotonic() >= deadline:
                timed_out = True
                break
            for key, _ in selector.select(min(0.05, max(0, deadline - time.monotonic()))):
                name, target = key.data
                data = os.read(key.fileobj.fileno(), 16384)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                remaining = STREAM_LIMIT - sizes[name]
                if len(data) > remaining:
                    overflow = True
                    data = data[:remaining]
                if data:
                    capture(name, target, data)
                if overflow:
                    break
            if overflow:
                break
        quiet = _quiesce(proc)
        # Drain bytes already in the kernel pipe after the group is quiescent.
        for key in list(selector.get_map().values()):
            name, target = key.data
            while True:
                data = os.read(key.fileobj.fileno(), min(16384, STREAM_LIMIT - sizes[name] + 1))
                if not data:
                    break
                remaining = STREAM_LIMIT - sizes[name]
                if len(data) > remaining:
                    overflow = True
                    data = data[:remaining]
                if data:
                    capture(name, target, data)
                if overflow:
                    break
        return timed_out, overflow, quiet
    finally:
        selector.close()
        proc.stdout.close(); proc.stderr.close()


def run(output_parent: Path, attempt_name: str, spec: Spec | None = None, timeout: float = 10.0,
        before_spawn: Callable[[], None] | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", attempt_name) or attempt_name in (".", ".."):
        raise ValueError("invalid attempt name")
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0 or timeout > 60):
        raise ValueError("timeout must be finite and in (0, 60]")
    parent_fd = _open_dir(output_parent)
    attempt_fd = -1
    fds: list[int] = []
    proc = None
    record = {"schema": "mckernel.native-diagnostic-closure-run.v2", "scope": "HOST_DIAGNOSTIC_ONLY",
              "started_at": datetime.now(timezone.utc).isoformat(), "timeout_seconds": timeout,
              "status": "ERROR", "returncode": None, "timed_out": False, "stream_overflow": False}
    try:
        _check_parent(output_parent, parent_fd)
        os.mkdir(attempt_name, 0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
        attempt_fd = os.open(attempt_name, DIR_FLAGS, dir_fd=parent_fd)
        try:
            spec = spec or retained_spec()
            contents = {}
            inputs = {}
            for key, expected in spec.expected.items():
                contents[key], inputs[key] = _read_bound(getattr(spec, key), expected["size"],
                                                         expected["sha256"], expected["mode"])
            record["inputs"] = inputs
            oracle = json.loads(contents["oracle"])
            expected_oracle = (oracle["stdout"]["kind"], bytes.fromhex(oracle["stdout"]["hex"]),
                               oracle["stderr"]["kind"], oracle["stderr"]["hex"], oracle["wait_status"])
            if expected_oracle != ("exact-bytes", EXPECTED_STDOUT, "exact-bytes", "",
                                   {"kind": "exited", "code": 0}):
                raise ValueError("independent oracle drift")
            os.mkdir("inputs", 0o700, dir_fd=attempt_fd)
            inputs_fd = os.open("inputs", DIR_FLAGS, dir_fd=attempt_fd); fds.append(inputs_fd)
            os.mkdir("lib64", 0o700, dir_fd=inputs_fd)
            libdir_fd = os.open("lib64", DIR_FLAGS, dir_fd=inputs_fd); fds.append(libdir_fd)
            loader_fd = _write_bytes(libdir_fd, "ld-linux-x86-64.so.2", contents["loader"], 0o500); fds.append(loader_fd)
            libc_fd = _write_bytes(libdir_fd, "libc.so.6", contents["libc"], 0o400); fds.append(libc_fd)
            payload_fd = _write_bytes(inputs_fd, "payload", contents["payload"], 0o500); fds.append(payload_fd)
            source_fd = _write_bytes(inputs_fd, "source.c", contents["source"]); fds.append(source_fd)
            oracle_fd = _write_bytes(inputs_fd, "oracle.json", contents["oracle"]); fds.append(oracle_fd)
            os.fchmod(libdir_fd, 0o500); os.fsync(libdir_fd)
            os.fchmod(inputs_fd, 0o500); os.fsync(inputs_fd)
            record["private_inputs"] = {key: {"sha256": _sha(data), "size": len(data)} for key, data in contents.items()}
            record["elf"] = inspect_elf(payload_fd, libc_fd, loader_fd) if spec.inspect else {"inspection": "synthetic test fixture"}
            os.mkdir("case", 0o700, dir_fd=attempt_fd)
            case_fd = os.open("case", DIR_FLAGS, dir_fd=attempt_fd); fds.append(case_fd)
            os.mkdir("work", 0o700, dir_fd=case_fd)
            work_fd = os.open("work", DIR_FLAGS, dir_fd=case_fd); fds.append(work_fd)
            command = [f"/proc/self/fd/{loader_fd}", "--inhibit-cache", "--library-path",
                       f"/proc/self/fd/{libdir_fd}", "--argv0", "app", f"/proc/self/fd/{payload_fd}", "A", "", "B"]
            record.update({"command": command, "environment": ENV, "cwd": f"/proc/self/fd/{work_fd}",
                           "pass_fds": [loader_fd, libdir_fd, payload_fd, work_fd],
                           "stdout_limit": STREAM_LIMIT, "stderr_limit": STREAM_LIMIT})
            _write_json(attempt_fd, "launch-intent.json", record)
            if before_spawn:
                before_spawn()
            _check_parent(output_parent, parent_fd)
            out_fd = os.open("stdout.bin", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                             dir_fd=attempt_fd); fds.append(out_fd)
            err_fd = os.open("stderr.bin", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                             dir_fd=attempt_fd); fds.append(err_fd)
            proc = subprocess.Popen(command, cwd=f"/proc/self/fd/{work_fd}", env=ENV, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                                    close_fds=True, pass_fds=(loader_fd, libdir_fd, payload_fd, work_fd))
            record["captured_bytes"] = {"stdout": 0, "stderr": 0}
            timed_out, overflow, quiet = _drain(proc, out_fd, err_fd, timeout, record["captured_bytes"])
            record.update({"returncode": proc.returncode, "timed_out": timed_out,
                           "stream_overflow": overflow, "process_group_quiescent": quiet})
            private_fds = {"payload": payload_fd, "loader": loader_fd, "libc": libc_fd,
                           "source": source_fd, "oracle": oracle_fd}
            record["post_run_private_sha256"] = {key: _hash_fd(fd, len(contents[key]))
                                                  for key, fd in private_fds.items()}
            if any(record["post_run_private_sha256"][key] != inputs[key]["sha256"] for key in private_fds):
                raise ValueError("private consumed input drift")
            os.fsync(out_fd); os.fsync(err_fd); os.fsync(attempt_fd)
            for name in ("stdout", "stderr"):
                fd = out_fd if name == "stdout" else err_fd
                os.lseek(fd, 0, os.SEEK_SET)
                # The output descriptors were opened write-only; reopen no-follow under pinned attempt.
                read_fd = os.open(name + ".bin", FILE_FLAGS, dir_fd=attempt_fd)
                try:
                    if (os.fstat(read_fd).st_dev, os.fstat(read_fd).st_ino) != (
                        os.fstat(fd).st_dev, os.fstat(fd).st_ino):
                        raise ValueError("output pathname swapped")
                    data = bytearray()
                    while True:
                        block = os.read(read_fd, 16384)
                        if not block:
                            break
                        data.extend(block)
                    record[name] = {"size": len(data), "sha256": _sha(data)}
                finally:
                    os.close(read_fd)
            _check_parent(output_parent, parent_fd)
            record["status"] = "PASS" if quiet and not timed_out and not overflow and proc.returncode == 0 and (
                record["stdout"]["size"], record["stdout"]["sha256"], record["stderr"]["size"],
                record["stderr"]["sha256"]) == (91, _sha(EXPECTED_STDOUT), 0, _sha(b"")) else "FAIL"
        except BaseException as exc:
            record.setdefault("first_failure", f"{type(exc).__name__}: {exc}")
            record["status"] = "ERROR"
            if proc is not None and proc.returncode is None:
                record["process_group_quiescent"] = _quiesce(proc)
                record["returncode"] = proc.returncode
        finally:
            record["ended_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(attempt_fd, "result.json", record)
    finally:
        for fd in reversed(fds):
            os.close(fd)
        if attempt_fd >= 0:
            os.close(attempt_fd)
        os.close(parent_fd)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-parent", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    result = run(args.output_parent, args.attempt, timeout=args.timeout)
    print(json.dumps({"status": result["status"], "returncode": result["returncode"]}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
