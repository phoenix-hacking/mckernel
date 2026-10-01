#!/usr/bin/env python3
"""One-shot, root-lock-holding release for the prepared scratch21 build."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
from pathlib import Path

REPO = Path("/home/holden/mckernel")
ROOT = Path("/home/holden/mckernel-work/scratch")
REF = "refs/remotes/origin/codex/local-native-staging-repair"
SELF = "docs/verification/evidence/native-exact-scratch21-heavy-build-execution-release-v2-20261001.py"
TEST = "scripts/tests/test_native_exact_scratch21_heavy_build_execution_release_v2_20261001.py"
PROPOSAL = "docs/verification/evidence/native-exact-scratch21-heavy-build-execution-proposal-v2-20261001.json"
PREP = ROOT / "native-exact-delta-request-scratch-21.json"
EXECUTION = ROOT / "native-exact-build-request-scratch-21.execution.json"
CANDIDATE = ROOT / "mckernel-exact-candidate-scratch-21"
WRAPPER = CANDIDATE / "scripts/native_rust_exact_disk_build_wrapper.py"
OUTPUT = ROOT / "mckernel-exact-candidate-scratch-21-output"
EVIDENCE = ROOT / "mckernel-exact-candidate-scratch-21-evidence"
LEASE = ROOT / "native-exact-build-lease-scratch-21.json"
EXCLUSION = ROOT / "native-exact-candidate-operational-exclusion-scratch18.json"
SHARED = ROOT / "mckernel-heavy-operation.lock"
LOCK = Path("/run/lock/mckernel-development.lock")
STDOUT = ROOT / "native-exact-scratch21-heavy-build-v2.stdout"
STDERR = ROOT / "native-exact-scratch21-heavy-build-v2.stderr"
TERMINAL = ROOT / "native-exact-scratch21-heavy-build-v2.terminal.json"
QUARANTINE = ROOT / "native-exact-scratch21-heavy-build-v2.root-lock-quarantine.json"

PREP_SHA256 = "04a7b363d94af5da8276397f6c2e0baec058eabdcc10471b8e2c8d0f9b554f2c"
DERIVED_SHA256 = "35efb73b2b5356507bd4b740b8925a3bd325135257ffaf39bffcefa9930c45b6"
WRAPPER_SHA256 = "3b910b0c968d85390ca7d00e6953ddb13dc91714180c51fd476853dac529739c"
CANDIDATE_HEAD = "28a905bfc177627e338a3fd91f69329ac2e74046"
CANDIDATE_TREE = "1d7bfce8a37ab5dd1bdd8197c4531a157ffdfd0f"
LOCK_ID = (27, 4, 0, 0, 0o644, 1)
MAX_CAPTURE = 16 << 20


class Refusal(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode() + b"\n"


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def stable_regular(path, expected=None, maximum=MAX_CAPTURE):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    fd = os.open(str(path), flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise Refusal("invalid regular file: " + str(path))
        data = bytearray()
        while len(data) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(fd)
        live = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_uid,
                              s.st_gid, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or identity(before) != identity(live) or len(data) != before.st_size:
            raise Refusal("file changed during read: " + str(path))
        raw = bytes(data)
        if expected is not None and sha(raw) != expected:
            raise Refusal("hash mismatch: " + str(path))
        return raw
    finally:
        os.close(fd)


def git(args, cwd=REPO):
    env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_NO_REPLACE_OBJECTS": "1",
           "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-C", str(cwd), *args],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode:
        raise Refusal("git binding failed")
    return result.stdout


def bind_release(commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit or ""):
        raise Refusal("invalid release commit")
    if git(["rev-parse", "--verify", REF + "^{commit}"]).decode().strip() != commit:
        raise Refusal("release commit is not fetched ref")
    for rel in (SELF, TEST, PROPOSAL):
        if git(["show", commit + ":" + rel]) != stable_regular(REPO / rel):
            raise Refusal("release blob mismatch: " + rel)


def acquire_development_lock():
    fd = os.open(str(LOCK), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    meta = os.fstat(fd)
    actual = (meta.st_dev, meta.st_ino, meta.st_uid, meta.st_gid,
              stat.S_IMODE(meta.st_mode), meta.st_nlink)
    if actual != LOCK_ID or not stat.S_ISREG(meta.st_mode):
        os.close(fd)
        raise Refusal("development lock identity mismatch")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def derive(prepared):
    required = {"preparation_only": True, "executable": False,
                "execution_released": False, "release_required": True}
    if any(prepared.get(key) is not value for key, value in required.items()):
        raise Refusal("prepared flags mismatch")
    result = dict(prepared)
    result.update(preparation_only=False, executable=True,
                  execution_released=True, release_required=False)
    raw = canonical(result)
    if sha(raw) != DERIVED_SHA256:
        raise Refusal("derived request mismatch")
    return result, raw


def empty_directory(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        meta = os.fstat(fd)
        if stat.S_IMODE(meta.st_mode) != 0o700 or os.listdir(fd):
            raise Refusal("output directory is not fresh: " + str(path))
    finally:
        os.close(fd)


def preflight():
    prepared_raw = stable_regular(PREP, PREP_SHA256, 1 << 20)
    prepared = strict(prepared_raw)
    derived, derived_raw = derive(prepared)
    stable_regular(WRAPPER, WRAPPER_SHA256, 1 << 20)
    if git(["rev-parse", "HEAD"], CANDIDATE).decode().strip() != CANDIDATE_HEAD:
        raise Refusal("candidate HEAD mismatch")
    if git(["rev-parse", "HEAD^{tree}"], CANDIDATE).decode().strip() != CANDIDATE_TREE:
        raise Refusal("candidate tree mismatch")
    empty_directory(OUTPUT)
    empty_directory(EVIDENCE)
    for path in (EXECUTION, LEASE, EXCLUSION, SHARED, STDOUT, STDERR, TERMINAL):
        if os.path.lexists(path):
            raise Refusal("fresh path occupied: " + str(path))
    return derived, derived_raw


def run_checked(command, stdout_path, stderr_path, lockfd):
    outfd = os.open(str(stdout_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    errfd = os.open(str(stderr_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=outfd, stderr=errfd,
                                close_fds=True, pass_fds=(lockfd,),
                                env={"PATH": "/usr/bin:/bin", "HOME": "/home/holden",
                                     "LANG": "C", "LC_ALL": "C",
                                     "SUDO_ASKPASS": os.environ.get("SUDO_ASKPASS", "")})
        os.fsync(outfd); os.fsync(errfd)
        return result.returncode
    finally:
        os.close(outfd); os.close(errfd)


def publish(path, raw, expected_sha256=None):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            if count <= 0:
                raise Refusal("short request publication")
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if stable_regular(path, expected_sha256 or sha(raw), 1 << 20) != raw:
        raise Refusal("published request changed")


def retirement_proven(result):
    """Only a current, positively retired terminal owner permits lock release."""
    return (isinstance(result, dict) and result.get("retired") is True and
            result.get("client_retirement_unproven") is not True and
            result.get("cleanup_separately_required") is True and
            result.get("terminal_container_retained") is True and
            result.get("terminal_container_info") is not None and
            result.get("terminal_container_info_current") is True)


def quarantine_root_lock(lockfd, reason):
    """Retain the live root lock until separately reviewed cleanup.

    This intentionally does not return.  Signals are already deferred, so an
    uncertain container/client cannot become concurrent with another guest.
    """
    record = {"schema": "mckernel.native-exact-scratch21-root-lock-quarantine.v1",
              "status": "QUARANTINED", "pid": os.getpid(),
              "starttime": Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19],
              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
              "lock_device_inode": "%d:%d" % LOCK_ID[:2], "reason": reason}
    if not os.path.lexists(QUARANTINE):
        publish(QUARANTINE, canonical(record))
    while True:
        signal.pause()


def execute(release_commit):
    bind_release(release_commit)
    requested = []
    old_handlers = {}
    def defer(signum, _frame):
        if not requested:
            requested.append(signum)
    for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        old_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, defer)
    lockfd = acquire_development_lock()
    build_started = False
    safe_to_release = True
    try:
        request, raw = preflight()
        # Read-only checks occur under the root lock before the request is consumed.
        validate = subprocess.run(["/usr/bin/python3", "-B", str(WRAPPER), str(PREP),
                                   "--launcher-aggregate-gib", "16.2158", "--validate-only"],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=600)
        if validate.returncode or b"PASS_COMPATIBILITY_ONLY" not in validate.stdout:
            raise Refusal("compatibility validation refused")
        census = subprocess.run(["/usr/bin/python3", "-B", str(WRAPPER), str(PREP),
                                 "--launcher-aggregate-gib", "16.2158", "--census-only",
                                 "--request-sha256", PREP_SHA256], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if census.returncode or b'"status":"PASS_READ_ONLY"' not in census.stdout.replace(b" ", b""):
            raise Refusal("read-only census refused")
        if requested:
            raise Refusal("signal received before request publication")
        # Recheck all mutation-sensitive inputs immediately before O_EXCL publication.
        request2, raw2 = preflight()
        if request2 != request or raw2 != raw:
            raise Refusal("preflight changed")
        publish(EXECUTION, raw, DERIVED_SHA256)
        build_started = True
        safe_to_release = False
        code = run_checked(["/usr/bin/python3", "-B", str(WRAPPER), str(EXECUTION),
                            "--launcher-aggregate-gib", "16.2158"], STDOUT, STDERR, lockfd)
        stdout = stable_regular(STDOUT, maximum=MAX_CAPTURE)
        stderr = stable_regular(STDERR, maximum=MAX_CAPTURE)
        try:
            result = strict(stdout.strip().splitlines()[-1])
        except (IndexError, ValueError, TypeError) as exc:
            raise Refusal("wrapper terminal output malformed") from exc
        terminal = {"schema": "mckernel.native-exact-scratch21-heavy-build-terminal.v2",
                    "release_commit": release_commit, "request_sha256": DERIVED_SHA256,
                    "returncode": code, "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
                    "deferred_signals": requested, "wrapper_result": result}
        publish(TERMINAL, canonical(terminal))
        safe_to_release = retirement_proven(result)
        if not safe_to_release:
            raise Refusal("terminal retirement is uncertain")
        if code != 0 or not isinstance(result, dict) or result.get("status") != "PASS":
            raise Refusal("heavy build failed after positive retirement")
        if os.path.lexists(LEASE):
            raise Refusal("retired request lease unexpectedly remains")
        if not os.path.lexists(EXCLUSION) or not os.path.lexists(SHARED):
            raise Refusal("shared exclusions were not retained for cleanup")
        if requested:
            raise Refusal("signal received during build; retirement was preserved")
        return {"status": "PASS_EXECUTED", "release_commit": release_commit,
                "request_sha256": DERIVED_SHA256, "wrapper_result": result,
                "terminal_sha256": sha(stable_regular(TERMINAL))}
    finally:
        if build_started and not safe_to_release:
            quarantine_root_lock(lockfd, "build-started-without-positive-terminal-retirement")
        fcntl.flock(lockfd, fcntl.LOCK_UN)
        os.close(lockfd)
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"status": "REFUSED", "reason": "--execute required"}, sort_keys=True))
        return 1
    try:
        print(json.dumps(execute(args.release_commit), sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
