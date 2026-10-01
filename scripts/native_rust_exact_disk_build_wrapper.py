#!/usr/bin/env python3
"""Admission wrapper for one exact disk-backed native Rust build.

This policy boundary serializes admission with shared and per-attempt locks.
It delegates container ownership exactly once to the authenticated BuildOwner,
preserving that owner's lease and evidence protocol. The shared build/image/
guest source contract is enabled; each operation still needs its own reviewed
execution release and exact input bindings.
"""
import argparse
from decimal import Decimal, InvalidOperation
import importlib.util
import json
import os
from pathlib import Path
import types
import hashlib
import stat
import shutil
import subprocess
import re
import selectors
import time


LAUNCHER_AGGREGATE_GIB = "16.2158"
# Decimal GiB is converted by truncation to the greatest admissible integer
# byte budget.  This is deterministic across Python versions and rejects even
# one byte over it.
LAUNCHER_AGGREGATE_BYTES = int(Decimal(LAUNCHER_AGGREGATE_GIB) * (2 ** 30))
EXPECTED_LIMITS = {
    "NanoCpus": 4000000000,
    "CpusetCpus": "2-5",
    "Memory": 12 * 2 ** 30,
    "MemorySwap": 12 * 2 ** 30,
    "PidsLimit": 512,
    "NetworkMode": "none",
}
# The original path is a retained immutable tombstone.  Fresh attempts must
# use the reviewed replacement so a stale exclusion can never be mistaken for
# the current build's lease.
RETIRED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-76ae20b5.json"
# The failed -2, -3, closurefix-4, runtimeclosure-5, offline-cwd-6, and
# memory-map-7, relocated-memory-map-8, mapping-binding-9,
# lifecycle-binding-10, objtool-binding-11, runtime-blob-12, and self-digest-13
# attempts are retained evidence, never reusable leases. Fresh requests are
# bound to exportset-16; exportsets 14 and 15 are retained by prior attempts.
REVIEWED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-76ae20b5-2.json"
SUPERSEDED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-97fb67a7-3.json"
CLOSUREFIX_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-closurefix-4.json"
RUNTIMECLOSURE_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-runtimeclosure-5.json"
OFFLINECWD_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-offlinecwd-6.json"
MEMORYMAP_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-memorymap-7.json"
MEMORYMAP_RELOCATED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-memorymap-relocated-8.json"
MAPPINGBINDING_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-mappingbinding-9.json"
LIFECYCLEBINDING_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-lifecyclebinding-10.json"
OBJTOOLBINDING_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-objtoolbinding-11.json"
RUNTIMEBLOB_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-runtimeblob-12.json"
SELFDIGEST_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-selfdigest-13.json"
CONSUMED_EXPORTSET16_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-exportset-16.json"
# Fresh scratch18 lease.  Scratch17, scratch16 and every earlier exportset remain
# immutable historical records and must never be reused as an active lock.
RETIRED_SCRATCH16_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch16.json"
RETIRED_SCRATCH17_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch17.json"
OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18.json"
DISPATCHER_SCRATCH_ROOT = "/home/holden/mckernel-work/scratch"
DISPATCHER_EMERGENCY_BYTES = 512 * 2 ** 20
SHARED_HEAVY_LOCK_PATH = DISPATCHER_SCRATCH_ROOT + '/mckernel-heavy-operation.lock'
# Independently reviewed common source contract, enabled with the guest switch.
# This is not a build, image or guest execution release.
HEAVY_ENTRY_CONTRACT_RELEASED = True
HISTORICAL_OBSERVER_SHA256 = 'fad2dd08fdc098c1dcda1d2fa8eaf9fc885f64d4054c9ca85ad71f7a5000fed0'
HEAVY_EXECUTABLES = frozenset(('qemu-system-x86_64', 'qemu-system-aarch64',
    'qemu-kvm', 'mcexec', 'firecracker', 'rustc', 'cargo', 'make', 'ninja', 'buildah'))
HEAVY_SCRIPTS = frozenset(('native_rust_exact_build_container_owner.py',
    'native_rust_exact_disk_build_wrapper.py', 'native_rust_exact_build_offline.py'))
MAX_PROC_ENTRIES = 4096
MAX_CMDLINE_BYTES = 1 << 20
MAX_ARG_COUNT = 256
MAX_ARG_BYTES = 4096
MAX_REPORT_BYTES = 1 << 20
MAX_HEAVY_ROWS = 256

# Identical parser source is used by the local and privileged classifiers.
# Unknown options are an unverifiable identity, never evidence of an idle host.
PYTHON_SCRIPT_PARSER_SOURCE = r'''def python_script(argv):
    if not isinstance(argv, list) or not argv or len(argv) > MAX_ARG_COUNT:
        raise ValueError("Python argument count invalid")
    if any(not isinstance(arg, str) or len(arg) > MAX_ARG_BYTES or "\0" in arg for arg in argv):
        raise ValueError("Python argument invalid")
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--": return argv[i + 1] if i + 1 < len(argv) else None
        if arg == "-": return None
        if not arg.startswith("-"): return arg
        if arg in ("--help", "--version", "--help-env", "--help-xoptions", "--help-all"):
            return None
        if arg == "--check-hash-based-pycs":
            if i + 1 >= len(argv): raise ValueError("Python option operand missing")
            i += 2
            continue
        if arg.startswith("--check-hash-based-pycs="):
            if not arg.split("=", 1)[1]: raise ValueError("Python option operand missing")
            i += 1
            continue
        if arg.startswith("--"): raise ValueError("unknown Python long option")
        j = 1
        while j < len(arg):
            option = arg[j]
            if option in "cm": return None
            if option in "h?V": return None
            if option in "WX":
                if j + 1 == len(arg):
                    if i + 1 >= len(argv): raise ValueError("Python option operand missing")
                    i += 1
                break
            if option not in "bBdEiqIOsSuvxRt":
                raise ValueError("unknown Python short option")
            j += 1
        i += 1
    return None
'''
_PYTHON_PARSER_NAMESPACE = {'MAX_ARG_COUNT': MAX_ARG_COUNT, 'MAX_ARG_BYTES': MAX_ARG_BYTES}
exec(PYTHON_SCRIPT_PARSER_SOURCE, _PYTHON_PARSER_NAMESPACE)

# This observer is deliberately self-contained: it receives no arguments and
# emits only authenticated heavy rows.  Its source is hashed before sudo is
# invoked, so a path/PATH replacement cannot change the privileged code.
PRIVILEGED_PROCESS_OBSERVER_SOURCE = PYTHON_SCRIPT_PARSER_SOURCE + r'''import json, os, re
from pathlib import Path
HEAVY = frozenset(("qemu-system-x86_64", "qemu-system-aarch64", "qemu-kvm", "mcexec", "firecracker", "rustc", "cargo", "make", "ninja", "buildah"))
SCRIPTS = frozenset(("native_rust_exact_build_container_owner.py", "native_rust_exact_disk_build_wrapper.py", "native_rust_exact_build_offline.py"))
MAX_PROC_ENTRIES = 4096
MAX_CMDLINE_BYTES = 1 << 20
MAX_ARG_COUNT = 256
MAX_ARG_BYTES = 4096
MAX_HEAVY_ROWS = 256
MAX_REPORT_BYTES = 1 << 20
def st(pid):
    return Path("/proc").joinpath(str(pid), "stat").read_text().rsplit(")", 1)[1].split()[19]
def cmdline(pid):
    with (Path("/proc") / str(pid) / "cmdline").open("rb") as stream:
        raw = stream.read(MAX_CMDLINE_BYTES + 1)
    if len(raw) > MAX_CMDLINE_BYTES: raise RuntimeError("command line exceeds bound")
    argv = [x.decode("utf-8", "strict") for x in raw.split(b"\0") if x]
    if len(argv) > MAX_ARG_COUNT or any(len(x) > MAX_ARG_BYTES for x in argv): raise RuntimeError("argument exceeds bound")
    return argv
def retired_or_kernel(pid, first):
    fields = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    return fields[19] != first or fields[0] in ("Z", "X", "x") or bool(int(fields[6]) & 0x200000)
def heavy(exe, argv):
    name = Path(exe.removesuffix(" (deleted)") if hasattr(str, "removesuffix") else exe.split(" (deleted)")[0]).name
    if name in HEAVY or name.startswith("qemu-system-"): return True
    if name in ("docker", "podman"): return any(a in ("build", "run", "start") for a in argv[1:])
    if re.fullmatch(r"python(?:[23](?:\.\d+)?)?", name):
        script = python_script(argv)
        return script is not None and Path(script).name in SCRIPTS
    return name in SCRIPTS
def caller():
    seen = set(); pid = os.getppid()
    while pid > 1 and pid not in seen:
        seen.add(pid)
        try:
            first = st(pid); argv = cmdline(pid)
            exe = os.readlink(str(Path("/proc") / str(pid) / "exe")); second = st(pid)
        except FileNotFoundError: pid = 0; continue
        if first != second: raise RuntimeError("caller identity changed")
        if re.fullmatch(r"python(?:3(?:\.\d+)?)?", Path(exe.removesuffix(" (deleted)") if hasattr(str, "removesuffix") else exe.split(" (deleted)")[0]).name) and python_script(argv) is not None and Path(python_script(argv)).name == "native_rust_exact_disk_build_wrapper.py":
            return pid, first
        try: pid = int(Path("/proc").joinpath(str(pid), "status").read_text().split("\nPPid:\t", 1)[1].split()[0])
        except (FileNotFoundError, IndexError, ValueError): pid = 0
    raise RuntimeError("calling wrapper identity unavailable")
def observe():
    if os.geteuid() != 0: raise RuntimeError("privileged observer required")
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    skip_pid, skip_start = caller(); rows = []
    entries = list(Path("/proc").iterdir())
    if len(entries) > MAX_PROC_ENTRIES: raise RuntimeError("process entry bound exceeded")
    for entry in entries:
        if not entry.name.isdigit(): continue
        pid = int(entry.name)
        first = None
        try:
            first = st(pid); argv = cmdline(pid)
            if not argv:
                if retired_or_kernel(pid, first): continue
                raise RuntimeError("live process command line unavailable")
            exe = os.readlink(str(entry / "exe")); second = st(pid)
            if first != second: raise RuntimeError("process identity changed")
        except FileNotFoundError:
            try:
                current = st(pid)
                if first is None or current == first: raise RuntimeError("process executable disappeared")
            except FileNotFoundError: pass
            continue
        if pid == skip_pid and first == skip_start: continue
        if heavy(exe, argv):
            if len(rows) >= MAX_HEAVY_ROWS: raise RuntimeError("heavy row bound exceeded")
            rows.append({"pid": pid, "starttime": first, "executable": exe})
    output = json.dumps({"schema":"mckernel.heavy-process-observation.v1", "status":"PASS_READ_ONLY", "boot_id":boot, "processes":rows}, sort_keys=True)
    if len(output.encode()) > MAX_REPORT_BYTES: raise RuntimeError("observer report exceeds bound")
    print(output)
if __name__ == "__main__": observe()
'''
PRIVILEGED_PROCESS_OBSERVER_SHA256 = '5f261e9ed481a8f7750e298f48c56293ee33d99df92e18595b562bc19b446612'


class AdmissionError(ValueError):
    pass


def _request_hash(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _starttime(pid):
    return Path("/proc") .joinpath(str(pid), "stat").read_text().rsplit(")", 1)[1].split()[19]


def _acquire_exclusion(request):
    path = Path(request.get("operational_exclusion_path", ""))
    if str(path) != OPERATIONAL_EXCLUSION_PATH:
        raise AdmissionError("operational exclusion path is not the reviewed exact path")
    return _acquire_lock(path, request, 'build')


def _acquire_lock(path, request, kind):
    record = {"schema": "mckernel.heavy-operation.v1", "kind": kind,
              "pid": os.getpid(), "starttime": _starttime(os.getpid()),
              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
              "request_sha256": _request_hash(request)}
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise AdmissionError("operational exclusion already exists; reconciliation required")
    try:
        record.update({"device": os.fstat(fd).st_dev, "inode": os.fstat(fd).st_ino})
        data = json.dumps(record, sort_keys=True).encode()
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if not isinstance(written, int) or written <= 0:
                raise AdmissionError("operational exclusion record write made no progress")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    parent_fd = os.open(str(path.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try: os.fsync(parent_fd)
    finally: os.close(parent_fd)
    return path, record


def acquire_heavy_operation(request, kind):
    """Common entry contract; caller retains token until positive retirement.

    Build, image and guest entrypoints must all call this before observing
    resources or constructing an owner. This source API is not a release.
    """
    if kind not in ('build', 'image', 'guest'):
        raise AdmissionError('unknown heavy operation kind')
    if not HEAVY_ENTRY_CONTRACT_RELEASED:
        raise AdmissionError('shared build/image/guest entry contract not released')
    return _acquire_lock(Path(SHARED_HEAVY_LOCK_PATH), request, kind)


def _release_exclusion(lock, record, result):
    if not (isinstance(result, dict) and result.get("status") == "PASS" and
            result.get("retired") is True and result.get("cleanup_separately_required") is False and
            result.get("terminal_container_info") is None and
            result.get("terminal_container_info_current") is True):
        return False
    try:
        parent_fd = os.open(str(lock.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            fd = os.open(lock.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
            try:
                current = json.loads(os.read(fd, 1 << 20).decode())
                identity = os.fstat(fd)
                if current != record or identity.st_dev != record["device"] or identity.st_ino != record["inode"]:
                    return False
                os.unlink(lock.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)
        return True
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _proc_starttime(pid):
    raw = Path('/proc').joinpath(str(pid), 'stat').read_text()
    return raw.rsplit(')', 1)[1].split()[19]


def _dispatcher_processes():
    rows = []
    proc = Path('/proc')
    try:
        entries = list(proc.iterdir())
    except PermissionError:
        return _privileged_process_observation()
    except OSError as exc:
        raise AdmissionError('process census unavailable') from exc
    if len(entries) > MAX_PROC_ENTRIES:
        raise AdmissionError('process census exceeds bound')
    for entry in entries:
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        start = None
        try:
            start = _proc_starttime(int(entry.name))
            with (entry / 'cmdline').open('rb') as stream:
                raw = stream.read(MAX_CMDLINE_BYTES + 1)
            if len(raw) > MAX_CMDLINE_BYTES:
                raise AdmissionError('process command line exceeds bound')
            argv = raw.split(b'\0')
            argv = [item.decode('utf-8', 'strict') for item in argv if item]
            if len(argv) > MAX_ARG_COUNT or any(len(item) > MAX_ARG_BYTES for item in argv):
                raise AdmissionError('process argument exceeds bound')
            if not argv:
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                if (fields[19] != start or fields[0] in ('Z', 'X', 'x') or
                    int(fields[6]) & 0x200000):
                    continue
                raise AdmissionError('live process command line unavailable')
            exe = os.readlink(str(entry / 'exe'))
            if _proc_starttime(int(entry.name)) != start:
                raise AdmissionError('process identity changed during census')
        except FileNotFoundError:
            try:
                current = _proc_starttime(int(entry.name))
            except FileNotFoundError:
                continue
            except PermissionError:
                return _privileged_process_observation()
            except OSError as exc:
                raise AdmissionError('process identity unverifiable') from exc
            if start is None or current == start:
                raise AdmissionError('live process executable or command line disappeared')
            continue
        except PermissionError:
            return _privileged_process_observation()
        except (OSError, UnicodeDecodeError, IndexError, ValueError) as exc:
            if isinstance(exc, AdmissionError):
                raise
            raise AdmissionError('process identity unverifiable') from exc
        if _heavy_identity(exe, argv):
            if len(rows) >= MAX_HEAVY_ROWS:
                raise AdmissionError('heavy process row bound exceeded')
            rows.append({'pid': int(entry.name), 'starttime': start, 'executable': exe})
    return rows


def _run_bounded_observer(command, source, env, timeout=15):
    """Bound both pipes while draining them; never include stderr in errors."""
    deadline = time.monotonic() + timeout
    result = None
    with selectors.DefaultSelector() as selector:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=env)
        try:
            for stream, event, label in ((process.stdin, selectors.EVENT_WRITE, 'input'),
                                          (process.stdout, selectors.EVENT_READ, 'stdout'),
                                          (process.stderr, selectors.EVENT_READ, 'stderr')):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, event, label)
            offset = 0
            output = bytearray()
            error_bytes = 0
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AdmissionError('privileged process observer timed out')
                events = selector.select(remaining)
                for key, _ in events:
                    if key.data == 'input':
                        try:
                            offset += os.write(key.fd, source[offset:offset + 4096])
                        except BrokenPipeError:
                            offset = len(source)
                        if offset == len(source):
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                    else:
                        limit = MAX_REPORT_BYTES if key.data == 'stdout' else 65536
                        used = len(output) if key.data == 'stdout' else error_bytes
                        chunk = os.read(key.fd, min(65536, limit - used + 1))
                        if not chunk:
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                        elif used + len(chunk) > limit:
                            raise AdmissionError('privileged process report exceeds bound')
                        elif key.data == 'stdout':
                            output.extend(chunk)
                        else:
                            error_bytes += len(chunk)
            result = types.SimpleNamespace(
                returncode=process.wait(timeout=max(0.001, deadline - time.monotonic())),
                stdout=bytes(output))
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
    return result


def _privileged_process_observation():
    source = PRIVILEGED_PROCESS_OBSERVER_SOURCE.encode()
    if hashlib.sha256(source).hexdigest() != PRIVILEGED_PROCESS_OBSERVER_SHA256:
        raise AdmissionError('privileged process observer source hash mismatch')
    try:
        result = _run_bounded_observer(
            ['/usr/bin/sudo', '-A', '/usr/bin/python3', '-I', '-B', '-'],
            source, _sudo_environment())
    except AdmissionError:
        raise
    except Exception as exc:
        raise AdmissionError('privileged process observer unavailable') from exc
    if result.returncode:
        raise AdmissionError('privileged process observer unavailable')
    if len(result.stdout) > MAX_REPORT_BYTES:
        raise AdmissionError('privileged process report exceeds bound')
    report = _strict_json(result.stdout)
    try:
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError as exc:
        raise AdmissionError('process observer boot identity unavailable') from exc
    if (not isinstance(report, dict) or
        set(report) != {'schema', 'status', 'boot_id', 'processes'} or
        report['schema'] != 'mckernel.heavy-process-observation.v1' or
        report['status'] != 'PASS_READ_ONLY' or report['boot_id'] != boot or
        not isinstance(report['processes'], list)):
        raise AdmissionError('privileged process report malformed')
    rows = []
    identities = set()
    if len(report['processes']) > MAX_HEAVY_ROWS:
        raise AdmissionError('privileged process row bound exceeded')
    for row in report['processes']:
        if (not isinstance(row, dict) or set(row) != {'pid', 'starttime', 'executable'} or
            type(row['pid']) is not int or row['pid'] <= 0 or
            not isinstance(row['starttime'], str) or not re.fullmatch(r'[0-9]+', row['starttime']) or
            not isinstance(row['executable'], str) or not row['executable'].startswith('/') or
            '\x00' in row['executable']):
            raise AdmissionError('privileged process row malformed')
        identity = (row['pid'], row['starttime'])
        if identity in identities or row['pid'] in {item[0] for item in identities}:
            raise AdmissionError('privileged process row duplicated')
        identities.add(identity)
        rows.append(row)
    return rows


def _heavy_identity(executable, argv):
    name = Path(executable.removesuffix(' (deleted)') if hasattr(str, 'removesuffix')
                else executable.split(' (deleted)')[0]).name
    if name in HEAVY_EXECUTABLES or name.startswith('qemu-system-'):
        return True
    if name in ('docker', 'podman'):
        return any(arg in ('build', 'run', 'start') for arg in argv[1:])
    if re.fullmatch(r'python(?:[23](?:\.\d+)?)?', name):
        script = _python_script_operand(argv)
        return script is not None and Path(script).name in HEAVY_SCRIPTS
    return name in HEAVY_SCRIPTS


def _python_script_operand(argv):
    """Return the actual Python script operand; never inspect -c/-m payloads."""
    try:
        return _PYTHON_PARSER_NAMESPACE['python_script'](argv)
    except ValueError as exc:
        raise AdmissionError('Python process identity unverifiable') from exc


def _sudo_environment():
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C', 'LC_ALL': 'C'}
    if 'SUDO_ASKPASS' in os.environ:
        env['SUDO_ASKPASS'] = os.environ['SUDO_ASKPASS']
    return env


def _strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise AdmissionError('duplicate JSON key')
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AdmissionError('invalid census JSON') from exc


def _dispatcher_containers():
    env = _sudo_environment()
    command = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock',
               'ps', '--no-trunc', '--format', '{{json .}}']
    try:
        result = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=15)
    except Exception as exc:
        raise AdmissionError('container census unavailable') from exc
    if result.returncode:
        raise AdmissionError('container census unavailable')
    rows = []
    for line in result.stdout.splitlines():
        row = _strict_json(line)
        if (not isinstance(row, dict) or
            any(not isinstance(row.get(key), str) or not row[key]
                for key in ('ID', 'Image', 'Names', 'State', 'Status')) or
            not re.fullmatch('[0-9a-f]{64}', row['ID']) or
            row['State'] not in ('running', 'paused', 'restarting')):
            raise AdmissionError('container identity unverifiable')
        # No implicit name-based exemptions. A separate reviewed concurrent
        # light-container profile is needed before introducing any exemption.
        rows.append(row)
    if rows:
        raise AdmissionError('live heavy container present')
    return rows


def _dispatcher_leases(request):
    root = Path(DISPATCHER_SCRATCH_ROOT)
    rows = []
    try:
        paths = sorted(root.glob('native-exact-build-lease-*.json'))
    except OSError as exc:
        raise AdmissionError('lease census unavailable') from exc
    authenticated = None
    for path in paths:
        try:
            if path.is_symlink() or not path.is_file():
                raise AdmissionError('lease identity unverifiable')
            try:
                data = json.loads(path.read_text())
            except PermissionError:
                if authenticated is None:
                    authenticated = _historical_lease_observation()
                row = authenticated.get(str(path))
                if row is None: raise AdmissionError('unknown historical lease')
                meta = path.lstat()
                if (meta.st_dev, meta.st_ino, meta.st_size) != (row['device'], row['inode'], row['size']):
                    raise AdmissionError('historical lease replaced after observation')
                rows.append(row)
                continue
        except AdmissionError:
            raise
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise AdmissionError('lease identity unverifiable') from exc
        # A tombstone is explicit and immutable; every other readable lease
        # is an active/ambiguous owner and blocks a new heavy dispatch.
        tombstone = data.get('tombstone') is True or (
            data.get('retired') is True and data.get('status') in ('PASS', 'FAIL'))
        if not tombstone:
            raise AdmissionError('non-tombstone lease present')
        pid, start = data.get('pid'), data.get('starttime')
        if isinstance(pid, int) and isinstance(start, str):
            try:
                if _proc_starttime(pid) == start:
                    raise AdmissionError('tombstone owner identity still live')
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise AdmissionError('lease owner identity unverifiable') from exc
        # Readable self-declared tombstones are not authenticated retirement.
        raise AdmissionError('unknown or unauthenticated historical lease')
    return rows


def _historical_lease_observation():
    observer_path = Path(__file__).resolve().parent / 'native_exact_historical_lease_observer.py'
    data = _stable_file_bytes(observer_path.parent, observer_path,
                             HISTORICAL_OBSERVER_SHA256, 'historical observer')
    # Execute authenticated bytes, avoiding a path replacement between hash
    # verification and privileged import. Only sudo receives the askpass value.
    result = subprocess.run(['/usr/bin/sudo', '-A', '/usr/bin/python3', '-I', '-B', '-'],
                            input=data, env=_sudo_environment(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30)
    if result.returncode: raise AdmissionError('historical lease observer unavailable')
    report = _strict_json(result.stdout)
    if (not isinstance(report, dict) or report.get('status') != 'PASS_READ_ONLY' or
        report.get('schema') != 'mckernel.historical-lease-observation.v1' or
        report.get('boot_id') != Path('/proc/sys/kernel/random/boot_id').read_text().strip() or
        not isinstance(report.get('leases'), list) or len(report['leases']) != 7):
        raise AdmissionError('historical lease report malformed')
    rows = {}
    for row in report['leases']:
        if (not isinstance(row, dict) or not isinstance(row.get('path'), str) or
            row['path'] in rows or
            any(type(row.get(key)) is not int for key in ('device', 'inode', 'size', 'pid')) or
            any(not isinstance(row.get(key), str) for key in ('sha256', 'starttime', 'evidence_sha256'))):
            raise AdmissionError('historical lease row malformed')
        rows[row['path']] = row
    return rows


def _dispatcher_resources(request):
    try:
        host_free = shutil.disk_usage('/').free
        scratch_free = shutil.disk_usage(DISPATCHER_SCRATCH_ROOT).free
        available = 0
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                available = int(line.split()[1]) * 1024
                break
        cpus = sorted(os.sched_getaffinity(0))
    except (OSError, ValueError, AttributeError) as exc:
        raise AdmissionError('resource observation unavailable') from exc
    required_host = int(request.get('host_floor', 0)) + DISPATCHER_EMERGENCY_BYTES
    required_scratch = int(request.get('scratch_floor', 0)) + DISPATCHER_EMERGENCY_BYTES
    if host_free < required_host or scratch_free < required_scratch or available < EXPECTED_LIMITS['Memory']:
        raise AdmissionError('fresh resource floors unavailable')
    if not set(range(2, 6)).issubset(cpus):
        raise AdmissionError('required build CPUs unavailable')
    return {'host_free': host_free, 'scratch_free': scratch_free,
            'memory_available': available, 'cpus': cpus}


def _dispatcher_reconcile(request):
    if request.get('operational_exclusion_path') != OPERATIONAL_EXCLUSION_PATH:
        raise AdmissionError('dispatcher exclusion binding mismatch')
    processes = _dispatcher_processes()
    if not isinstance(processes, list) or processes:
        raise AdmissionError('live or unresolved heavy process present')
    return {'processes': processes,
            'containers': _dispatcher_containers(),
            'leases': _dispatcher_leases(request),
            'resources': _dispatcher_resources(request)}


def _owner_path(request, source_root):
    raw = request.get("owner_path")
    path = Path(raw) if raw is not None else source_root / "scripts" / "native_rust_exact_build_container_owner.py"
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise AdmissionError("owner_path is not a regular file")
    try:
        path.resolve(strict=True).relative_to(source_root.resolve(strict=True))
    except ValueError:
        raise AdmissionError("owner_path escapes source_root")
    return path


def _stable_file_bytes(root, path, expected, label):
    """Read authenticated bytes through a descriptor-relative no-follow walk."""
    root = Path(root); path = Path(path)
    try:
        rel = path.relative_to(root)
    except ValueError:
        raise AdmissionError("%s escapes source_root" % label)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fds = []
    try:
        fd = os.open(str(root), flags)
        fds.append(fd)
        for component in rel.parts[:-1]:
            if component in ("", ".", ".."):
                raise AdmissionError("invalid component in %s" % label)
            nxt = os.open(component, flags, dir_fd=fd)
            fds.append(nxt); fd = nxt
        if not rel.parts or rel.parts[-1] in ("", ".", ".."):
            raise AdmissionError("invalid file path for %s" % label)
        leaf = os.open(rel.parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd)
        fds.append(leaf)
        opened = os.fstat(leaf)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise AdmissionError("%s is not a unique regular file" % label)
        chunks = []
        while True:
            block = os.read(leaf, 1 << 20)
            if not block: break
            chunks.append(block)
        data = b"".join(chunks)
        after = os.fstat(leaf)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mode) != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mode):
            raise AdmissionError("%s identity changed during read" % label)
    except AdmissionError:
        raise
    except OSError as exc:
        raise AdmissionError("cannot read %s: %s" % (label, exc))
    finally:
        for item in reversed(fds):
            try: os.close(item)
            except OSError: pass
    if not isinstance(expected, str) or hashlib.sha256(data).hexdigest() != expected:
        raise AdmissionError("%s hash mismatch" % label)
    return data


def _load_owner(request):
    source_root = Path(request.get("source_root", ""))
    if not source_root.is_absolute() or not source_root.is_dir() or source_root.is_symlink():
        raise AdmissionError("source_root is not a regular directory")
    source_root = source_root.resolve(strict=True)
    path = _owner_path(request, source_root)
    try:
        path.relative_to(source_root)
    except ValueError:
        raise AdmissionError("owner_path escapes source_root")
    owner_hash = request.get("owner_path_sha256")
    if owner_hash is None:
        raise AdmissionError("owner_path_sha256 is required before import")
    owner_bytes = _stable_file_bytes(source_root, path, owner_hash, "owner_path")
    # Both modules are loaded under a private candidate package.  The owner
    # uses a relative provenance import; this prevents a preloaded generic
    # ``native_rust_exact_build_offline`` module from contaminating admission.
    import sys
    package = "_mckernel_exact_candidate_%d_%x" % (os.getpid(), id(request))
    package_module = types.ModuleType(package)
    package_module.__path__ = [str(path.parent)]
    package_module.__package__ = package
    sys.modules[package] = package_module
    loaded = []
    try:
        provenance_name = package + ".native_rust_exact_build_offline"
        provenance_path = path.parent / "native_rust_exact_build_offline.py"
        try:
            provenance_path.relative_to(source_root)
        except ValueError:
            raise AdmissionError("provenance path escapes source_root")
        provenance_hash = request.get("provenance_path_sha256")
        if provenance_hash is None:
            raise AdmissionError("provenance_path_sha256 is required before import")
        provenance_bytes = _stable_file_bytes(source_root, provenance_path, provenance_hash, "provenance_path")
        driver_path = Path(request.get("driver_path", ""))
        if driver_path != provenance_path:
            raise AdmissionError("driver_path must equal authenticated provenance_path")
        if request.get("driver_path_sha256") != provenance_hash:
            raise AdmissionError("driver_path hash must equal provenance hash")
        provenance = types.ModuleType(provenance_name)
        provenance.__file__ = str(provenance_path)
        provenance.__package__ = package
        sys.modules[provenance_name] = provenance
        loaded.append(provenance_name)
        exec(compile(provenance_bytes, str(provenance_path), "exec"), provenance.__dict__)
        name = package + ".native_rust_exact_build_container_owner"
        module = types.ModuleType(name)
        module.__file__ = str(path)
        module.__package__ = package
        sys.modules[name] = module
        loaded.append(name)
        exec(compile(owner_bytes, str(path), "exec"), module.__dict__)
        if module.provenance.__file__ != str(provenance_path):
            raise AdmissionError("loaded provenance path differs from source_root")
        return module
    finally:
        for name in loaded + [package]:
            sys.modules.pop(name, None)


def _aggregate_argument(raw):
    if raw is None:
        raw = LAUNCHER_AGGREGATE_GIB
    if not isinstance(raw, str) or raw != LAUNCHER_AGGREGATE_GIB:
        raise AdmissionError("launcher aggregate must be exactly 16.2158 GiB")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise AdmissionError("invalid launcher aggregate")
    if value != Decimal(LAUNCHER_AGGREGATE_GIB):
        raise AdmissionError("launcher aggregate is not exact")
    return LAUNCHER_AGGREGATE_BYTES


def _require_profile(owner, request):
    if dict(getattr(owner, "LIMITS", {})) != EXPECTED_LIMITS:
        raise AdmissionError("owner LIMITS differ from reviewed pinned profile")
    requested = request.get("limits")
    if requested is not None and dict(requested) != EXPECTED_LIMITS:
        raise AdmissionError("request limits differ from reviewed pinned profile")
    if request.get("memory_backed_bytes", 0) not in (0, None):
        raise AdmissionError("request declares memory-backed source bytes")
    roots = request.get("memory_allocation_roots", [])
    if not isinstance(roots, list) or not roots:
        raise AdmissionError("memory allocation roots are required")
    # This is a lexical admission check; BuildOwner.validate performs the
    # authoritative filesystem binding and accounting check.
    if any("tmpfs" in str(root).lower() for root in roots):
        raise AdmissionError("tmpfs source roots are forbidden")


def _check_measurement(measurement, budget):
    if not isinstance(measurement, dict):
        raise AdmissionError("owner did not publish a measurement")
    backed = measurement.get("memory_allocation_memory_backed_bytes")
    if backed is None:
        backed = measurement.get("candidate_memory_effect", {}).get("bytes")
    if not isinstance(backed, int) or isinstance(backed, bool) or backed != 0:
        raise AdmissionError("owner measurement has nonzero memory-backed bytes")
    rows = measurement.get("memory_allocation_roots", [])
    if not isinstance(rows, list) or not rows:
        raise AdmissionError("owner allocation measurement is missing")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("filesystem"), str):
            raise AdmissionError("owner allocation measurement row is malformed")
        if row["filesystem"] not in ("ext4", "xfs"):
            raise AdmissionError("owner measurement includes unsupported filesystem")
        effect = row.get("memory_effect_bytes")
        if not isinstance(effect, int) or isinstance(effect, bool) or effect != 0:
            raise AdmissionError("owner allocation row has nonzero memory effect")
        allocated = row.get("allocated_bytes")
        if not isinstance(allocated, int) or isinstance(allocated, bool) or allocated < 0:
            raise AdmissionError("owner allocation row total is malformed")
        total = locals().get("row_total", 0) + allocated
        row_total = total
    aggregate = measurement.get("aggregate_memory_required")
    if not isinstance(aggregate, int) or isinstance(aggregate, bool):
        raise AdmissionError("owner aggregate measurement is missing")
    total_field = measurement.get("memory_allocation_total_bytes")
    if not isinstance(total_field, int) or isinstance(total_field, bool):
        raise AdmissionError("owner allocation total is missing")
    if total_field != row_total:
        raise AdmissionError("owner allocation total is inconsistent")
    tmpfs_total = measurement.get("memory_allocation_tmpfs_bytes")
    if not isinstance(tmpfs_total, int) or isinstance(tmpfs_total, bool) or tmpfs_total != 0:
        raise AdmissionError("owner tmpfs total is nonzero or missing")
    effect = measurement.get("candidate_memory_effect")
    if not isinstance(effect, dict) or effect.get("classification") != "none":
        raise AdmissionError("candidate memory effect classification is not none")
    effect_bytes = effect.get("bytes")
    if not isinstance(effect_bytes, int) or isinstance(effect_bytes, bool) or effect_bytes != 0:
        raise AdmissionError("candidate memory effect is nonzero")
    expected_aggregate = EXPECTED_LIMITS["Memory"] + effect_bytes
    if aggregate != expected_aggregate:
        raise AdmissionError("owner aggregate measurement is inconsistent")
    if aggregate < EXPECTED_LIMITS["Memory"]:
        raise AdmissionError("owner aggregate measurement is below pinned container memory")
    if aggregate > budget:
        raise AdmissionError("owner aggregate exceeds launcher budget")


def run_request(request, aggregate_gib=LAUNCHER_AGGREGATE_GIB):
    """Validate admission and invoke BuildOwner.run exactly once."""
    budget = _aggregate_argument(aggregate_gib)
    if "launcher_aggregate_memory_gib" in request:
        _aggregate_argument(request["launcher_aggregate_memory_gib"])
    if request.get('operational_exclusion_path') != OPERATIONAL_EXCLUSION_PATH:
        raise AdmissionError('operational exclusion path is not the reviewed exact path')
    shared_lock, shared_record = acquire_heavy_operation(request, 'build')
    try:
        lock, lock_record = _acquire_exclusion(request)
        # Reconcile every live heavy identity and resource floor while the
        # O_EXCL serialization lock is already held. Any unverifiable
        # observation retains that lock for explicit quarantine/reconciliation.
        _dispatcher_reconcile(request)
        owner = _load_owner(request)
        _require_profile(owner, request)
        # The offline provenance runner consumes this environment.  Set the
        # reviewed value before owner validation and retain all other owner values.
        owner.provenance.ENV["GIT_OPTIONAL_LOCKS"] = "0"
        with owner.CliSignals() as signals:
            checked = owner.BuildOwner(request, signals=signals)
            original_validate = checked.validate

            def guarded_validate():
                result = original_validate()
                _check_measurement(getattr(checked, "measurement", None), budget)
                return result

            # BuildOwner.run() calls self.validate() again immediately before
            # lease acquisition.  Guard that call too: a changed second measure
            # must never reach Docker or a lease.
            checked.validate = guarded_validate
            guarded_validate()
            result = checked.run()
        if _release_exclusion(lock, lock_record, result):
            _release_exclusion(shared_lock, shared_record, result)
        return result
    except BaseException:
        # Retain the exclusion on every exception: cleanup/lease state is not
        # positively proven, so a later run must explicitly quarantine it.
        raise


def validate_request(request, aggregate_gib=LAUNCHER_AGGREGATE_GIB):
    """Validate actual downstream compatibility without leases or execution.

    This calls the authenticated owner's read-only validation, including its
    provenance verifier. It performs no live admission and grants no release.
    The caller must invoke this before publishing a derived request; run_request
    repeats validation under shared ownership immediately before execution.
    """
    budget = _aggregate_argument(aggregate_gib)
    if 'launcher_aggregate_memory_gib' in request:
        _aggregate_argument(request['launcher_aggregate_memory_gib'])
    owner = _load_owner(request)
    _require_profile(owner, request)
    owner.provenance.ENV['GIT_OPTIONAL_LOCKS'] = '0'
    checked = owner.BuildOwner(request)
    checked.validate()
    _check_measurement(getattr(checked, 'measurement', None), budget)
    return {'status': 'PASS_COMPATIBILITY_ONLY', 'execution_released': False,
            'request_sha256': _request_hash(request)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--launcher-aggregate-gib", default=LAUNCHER_AGGREGATE_GIB)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text())
    result = (validate_request if args.validate_only else run_request)(request, args.launcher_aggregate_gib)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") in ('PASS', 'PASS_COMPATIBILITY_ONLY') else 1


if __name__ == "__main__":
    raise SystemExit(main())
