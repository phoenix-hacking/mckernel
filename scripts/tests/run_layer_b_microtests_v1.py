#!/usr/bin/env python3
"""Exact unprivileged Layer-B command supervisor; no root/runtime authority."""
import argparse
import hashlib
import json
import os
import resource
import signal
import subprocess
import time
from pathlib import Path

REPO = Path("/home/holden/mckernel")
PY39 = "/home/holden/anaconda3/bin/python3"
PY38 = "/usr/bin/python3"
M03_HARNESS = REPO / "kernel/rust/tests/pending_free_inventory_harness_v1.py"
TEST = "scripts.tests.test_collector_storage_fault_packet.StorageFaultV2SourceTests"
FOCUSED = (
    TEST + ".test_real_child_descriptor_remaps_preserve_abi_and_close_leaks",
    TEST + ".test_acquisition_sequence_and_live_identity_ownership",
)
ARCHIVE = REPO / "docs/verification/evidence/stability-linux-collector-root-success-20260915-2.tar.gz"
ARCHIVE_SHA256 = "ad7c670311f6756cf64610e1d3e0dbdcdb026f86857c8461c3295cc34c17a721"
ARCHIVE_MEMBERS = {
    "fixture": ("stability-linux-sealed-root-tests-20260913-2/work/cases/stdin-devnull/inputs/fixture", "9ad70dd23d699e72ad805f59446aec371c4e80b955056b845af921b4ce51f725"),
    "request.bin": ("stability-linux-sealed-root-tests-20260913-2/work/cases/stdin-devnull/inputs/request.bin", "e81b38bbe6116bf1df2807fa968e12dccfd28fe8c3ad225c45f282b36cab6716"),
    "selected-inputs.json": ("stability-linux-sealed-root-tests-20260913-2/work/cases/stdin-devnull/inputs/selected-inputs.json", "6b8761a9d2094147f02b9fe2a4c709246905a04c5122d68f6b9951162e01317d"),
}
INPUTS = {
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/witness_owner.py": "cd415301375a214e7f450b787c4832037e0fa046bbe17e4e6da8b7bc8f892232",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/supervise.py": "521a4d51225447424503446abdf8b4f11bb29380b618b8c3ff7a83c4e6c32e56",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/oracle.py": "7363f5a5401f32c1eb8efcd33acef8f1edc60a8d9a53d16e251fed0ba443f135",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/prepare.py": "2c85d284548a8a9f426943c6c61019bbae8e13b4eabe3e662bc068b94037ab74",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/packet.json": "b4acc91e6c92677f41eeaed31646cbbe4b556feee4b05a2920f78a195e60abdb",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/inject.h": "0711a9f5bdd60326ed919a8b39d9ac081044dd054431f049aeb8c32e8803b962",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/collector.patch": "e58c48dea6455cf0172dd5295db149cb29b5996b03dda3631513da86e68fb7b2",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1/tests.md": "eb0ad1868c021ce3091caa7095e427a3fd6a2b832dde51378842d9794deb4eb8",
    "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/collector.c": "09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f",
    "scripts/tests/test_collector_storage_fault_packet.py": "b259ad30e1704580d14ff898dfdf9d70d7307f6c0eae51e1b95d157c72a58644",
    "kernel/rust/tests/pending_free_inventory_reference_v1.c": "2755ba19e0d7083895daf82f815aca84090a0231d46c119bab93248467490aa6",
    "kernel/rust/tests/pending_free_inventory_vectors_v1.rs": "bf966b1226f4134609f565bb4e27d89ceff41a79fc842aeac7c8a05999668664",
    "kernel/rust/tests/pending_free_inventory_v1.rs": "26d1528f296979683850a846bb7a600a451a75a51db50f4d0900e9bdddc6b742",
    "kernel/rust/tests/pending_free_inventory_harness_v1.py": "95098a30d43596b3a80be9f0e56ecd4bb13e0514254d60207953be313fca89f1",
}
MAX_WALL_SECONDS = 60.0
MAX_PROCESSES = 8
MAX_RSS_BYTES = 512 * 1024 * 1024
MAX_TREE_BYTES = 256 * 1024 * 1024
POLL_SECONDS = 0.05
TERM_SECONDS = 5.0
KILL_SECONDS = 1.0
ZERO_OBSERVATIONS = 2
CLEANUP_ACTIVE = False


class SupervisorInterrupted(InterruptedError):
    """A termination signal that must traverse command cleanup."""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable_json(path, value):
    """Write one self-contained JSON record before returning to control flow."""
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        while encoded:
            written = os.write(fd, encoded)
            if written <= 0:
                raise OSError("short durable JSON write")
            encoded = encoded[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_text(path, value):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        encoded = value.encode()
        while encoded:
            written = os.write(fd, encoded)
            if written <= 0:
                raise OSError("short durable text write")
            encoded = encoded[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def archive_member_digest(member):
    """Hash a named regular archive member without extracting it to a work root."""
    import tarfile
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        info = archive.getmember(member)
        if not info.isfile():
            raise ValueError("archive member is not a regular file: " + member)
        stream = archive.extractfile(info)
        if stream is None:
            raise ValueError("archive member unavailable: " + member)
        try:
            value = hashlib.sha256(stream.read()).hexdigest()
        finally:
            stream.close()
    return value


def authenticate_inputs():
    """Authenticate all repository and retained-root bytes before any command."""
    for relative, expected in INPUTS.items():
        actual = digest(REPO / relative)
        if actual != expected:
            raise ValueError("input hash mismatch: %s %s" % (relative, actual))
    actual_archive = digest(ARCHIVE)
    if actual_archive != ARCHIVE_SHA256:
        raise ValueError("archive hash mismatch: " + actual_archive)
    authenticated = {}
    for label, (member, expected) in ARCHIVE_MEMBERS.items():
        actual = archive_member_digest(member)
        if actual != expected:
            raise ValueError("archive member hash mismatch: %s %s" % (member, actual))
        authenticated[label] = {"path": member, "sha256": actual}
    return authenticated


def tree_bytes(root):
    """Observation only: concurrent fixture cleanup may remove a scanned path."""
    total = 0
    try:
        entries = tuple(root.rglob("*"))
    except FileNotFoundError:
        return 0
    for path in entries:
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except FileNotFoundError:
            # M02's hash-bound TemporaryDirectory cleanup is an allowed race.
            continue
    return total


def proc_record(entry, session, page):
    """Read one /proc member, tolerating only disappearance during observation."""
    try:
        raw = (entry / "stat").read_text()
        close = raw.rfind(")")
        if close < 0:
            raise ValueError("malformed proc stat: " + entry.name)
        fields = raw[close + 2:].split()
        # fields start at kernel stat field 3: ppid=1, session=3, starttime=19.
        if int(fields[3]) != session:
            return None
        rss = int((entry / "statm").read_text().split()[1]) * page
        return {"pid": int(entry.name), "ppid": int(fields[1]), "rss_bytes": rss,
                "session": session, "startticks": int(fields[19])}
    except (FileNotFoundError, ProcessLookupError):
        return None


def session_snapshot(session):
    page = os.sysconf("SC_PAGE_SIZE")
    members = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            value = proc_record(entry, session, page)
            if value is not None:
                members.append(value)
    return sorted(members, key=lambda value: value["pid"])


def session_usage(session):
    members = session_snapshot(session)
    return len(members), sum(member["rss_bytes"] for member in members), members


def limits():
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (55, 55))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)


def signal_exact_session(session, signum, events):
    """Signal only members still carrying this exact session identity."""
    event = {"kind": "signal", "signal": signal.Signals(signum).name,
             "session": session, "timestamp_ns": time.time_ns()}
    try:
        before = session_snapshot(session)
        event["before"] = before
    except BaseException as error:
        event["observation_error"] = type(error).__name__ + ": " + str(error)
        before = []
    try:
        os.killpg(session, signum)
        event["group_signal"] = "sent"
    except ProcessLookupError:
        event["group_signal"] = "absent"
    except BaseException as error:
        event["group_signal_error"] = type(error).__name__ + ": " + str(error)
    # A member can be in another process group while retaining the session.
    for member in before:
        try:
            os.kill(member["pid"], signum)
        except ProcessLookupError:
            continue
        except BaseException as error:
            event.setdefault("member_signal_errors", []).append(
                {"pid": member["pid"], "error": type(error).__name__ + ": " + str(error)})
    events.append(event)


def wait_for_zero_session(session, seconds, events, phase, process=None):
    """Require two exact-session empty observations; record failure rather than hide it."""
    deadline = time.monotonic() + seconds
    zeros = 0
    last = []
    while time.monotonic() < deadline:
        try:
            # Popen.poll reaps a terminated direct leader so its zombie is not
            # mistaken for a surviving session member.
            if process is not None:
                process.poll()
            last = session_snapshot(session)
            events.append({"kind": "session-observation", "phase": phase,
                           "members": last, "timestamp_ns": time.time_ns()})
        except BaseException as error:
            events.append({"kind": "session-observation-error", "phase": phase,
                           "error": type(error).__name__ + ": " + str(error),
                           "timestamp_ns": time.time_ns()})
            return False, last
        if not last:
            zeros += 1
            if zeros >= ZERO_OBSERVATIONS:
                return True, []
        else:
            zeros = 0
        time.sleep(POLL_SECONDS)
    return False, last


def cleanup_command(process, identity, reason):
    """Bounded TERM/KILL and direct reap on all paths after a successful Popen."""
    global CLEANUP_ACTIVE
    CLEANUP_ACTIVE = True
    session = identity["session"]
    events = []
    try:
        signal_exact_session(session, signal.SIGTERM, events)
        zero_term, _remaining = wait_for_zero_session(session, TERM_SECONDS, events, "after-term", process)
        if not zero_term:
            signal_exact_session(session, signal.SIGKILL, events)
            zero_kill, _remaining = wait_for_zero_session(session, KILL_SECONDS, events, "after-kill", process)
        else:
            zero_kill = True
        try:
            returncode = process.wait(timeout=KILL_SECONDS)
            direct_reap = {"returncode": returncode, "state": "reaped"}
        except subprocess.TimeoutExpired:
            # A direct child that survived group cleanup is a failure, never an orphan.
            try:
                process.kill()
            except ProcessLookupError:
                pass
            returncode = process.wait()
            direct_reap = {"returncode": returncode, "state": "killed-and-reaped"}
        try:
            final_members = session_snapshot(session)
        except BaseException as error:
            final_members = [{"observation_error": type(error).__name__ + ": " + str(error)}]
        return {"direct_reap": direct_reap, "events": events,
                "final_members": final_members, "reason": reason,
                "session_zero_after_kill": zero_kill,
                "session_zero_after_term": zero_term}
    except BaseException as error:
        # Cleanup observation must not become a way for a live child to escape.
        events.append({"kind": "cleanup-error", "error": type(error).__name__ + ": " + str(error),
                       "timestamp_ns": time.time_ns()})
        try:
            os.killpg(session, signal.SIGKILL)
            events.append({"kind": "emergency-killpg", "session": session,
                           "timestamp_ns": time.time_ns()})
        except ProcessLookupError:
            events.append({"kind": "emergency-killpg", "session": session,
                           "state": "absent", "timestamp_ns": time.time_ns()})
        except BaseException as kill_error:
            events.append({"kind": "emergency-killpg-error", "session": session,
                           "error": type(kill_error).__name__ + ": " + str(kill_error),
                           "timestamp_ns": time.time_ns()})
        try:
            process.kill()
        except ProcessLookupError:
            pass
        try:
            returncode = process.wait(timeout=KILL_SECONDS)
            direct_reap = {"returncode": returncode, "state": "emergency-reaped"}
        except subprocess.TimeoutExpired:
            direct_reap = {"returncode": None, "state": "emergency-unreaped"}
        zero, _remaining = wait_for_zero_session(session, KILL_SECONDS, events, "after-emergency-kill", process)
        try:
            final_members = session_snapshot(session)
        except BaseException as final_error:
            final_members = [{"observation_error": type(final_error).__name__ + ": " + str(final_error)}]
        return {"cleanup_error": type(error).__name__ + ": " + str(error),
                "direct_reap": direct_reap, "events": events, "final_members": final_members,
                "reason": reason, "session_zero_after_kill": zero,
                "session_zero_after_term": False}
    finally:
        CLEANUP_ACTIVE = False


def run(command_id, argv, root, environment):
    stdout_path = root / "logs" / (command_id + ".stdout")
    stderr_path = root / "logs" / (command_id + ".stderr")
    started_ns = time.time_ns()
    record_path = root / "logs" / (command_id + ".json")
    record = {"argv": argv, "command_id": command_id, "started_ns": started_ns,
              "stderr": stderr_path.name, "stdout": stdout_path.name, "state": "STARTING"}
    durable_json(record_path, record)
    process = None
    identity = None
    primary_error = None
    peak_processes = peak_rss = 0
    violation = None
    cleanup = None
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(argv, cwd=str(REPO), env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                start_new_session=True, preexec_fn=limits)
            identity = {"pid": process.pid, "session": process.pid, "startticks": None}
            members = session_snapshot(process.pid)
            leader = next((member for member in members if member["pid"] == process.pid), None)
            if leader is None:
                raise RuntimeError("new session leader was not observable")
            identity["startticks"] = leader["startticks"]
            record.update({"identity": identity, "state": "RUNNING"})
            durable_json(record_path, record)
            deadline = time.monotonic() + MAX_WALL_SECONDS
            while process.poll() is None:
                processes, rss, _members = session_usage(process.pid)
                peak_processes = max(peak_processes, processes)
                peak_rss = max(peak_rss, rss)
                size = tree_bytes(root)
                if processes > MAX_PROCESSES:
                    violation = "process-count"
                elif rss > MAX_RSS_BYTES:
                    violation = "aggregate-rss"
                elif size > MAX_TREE_BYTES:
                    violation = "output-bytes"
                elif time.monotonic() >= deadline:
                    violation = "wall-time"
                if violation:
                    raise RuntimeError("resource violation: " + violation)
                time.sleep(POLL_SECONDS)
            # A completed leader is insufficient: descendants retain the same SID.
            remaining = session_snapshot(process.pid)
            if remaining:
                raise RuntimeError("residual exact-session members after leader exit")
            returncode = process.wait()
            if returncode:
                raise RuntimeError("nonzero child status: %d" % returncode)
    except BaseException as error:
        primary_error = error
    finally:
        if process is not None and identity is not None:
            cleanup = cleanup_command(process, identity,
                                      "normal-finalization" if primary_error is None else "exception-finalization")
    ended_ns = time.time_ns()
    record.update({"cleanup": cleanup, "ended_ns": ended_ns,
                   "peak_processes": peak_processes, "peak_rss_bytes": peak_rss,
                   "state": "TERMINAL", "violation": violation})
    if primary_error is not None:
        record["primary_error"] = type(primary_error).__name__ + ": " + str(primary_error)
    durable_json(record_path, record)
    if cleanup is None:
        raise RuntimeError("command did not acquire a child session") from primary_error
    if not cleanup["session_zero_after_kill"] or cleanup["final_members"]:
        raise RuntimeError("exact-session cleanup incomplete: %s" % cleanup) from primary_error
    if primary_error is not None:
        raise primary_error
    return stdout_path.read_text(), stderr_path.read_text(), record


def install_signal_handlers():
    def interrupted(signum, _frame):
        if CLEANUP_ACTIVE:
            return
        raise SupervisorInterrupted("supervisor received " + signal.Signals(signum).name)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    if not args.output.is_absolute() or root.exists() or not root.parent.is_dir():
        raise SystemExit("output must be an absent absolute path with existing parent")
    archive_members = authenticate_inputs()
    root.mkdir(mode=0o700)
    for name in ("home", "tmp", "logs"):
        (root / name).mkdir(mode=0o700)
    durable_json(root / "input-authentication.json", {
        "archive": {"path": str(ARCHIVE), "sha256": ARCHIVE_SHA256,
                    "members": archive_members}, "repository_inputs": INPUTS})
    environment = {"HOME": str(root / "home"), "LANG": "C", "LC_ALL": "C",
        "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": str(root / "tmp")}
    commands = (
        ("m02-focused-py39", [PY39, "-B", "-m", "unittest", *FOCUSED]),
        ("m02-focused-py38", [PY38, "-B", "-m", "unittest", *FOCUSED]),
        ("m03", [PY39, "-B", str(M03_HARNESS), "--execute", "--output", str(root / "m03")]),
    )
    results = []
    install_signal_handlers()
    try:
        for command_id, argv in commands:
            stdout, stderr, record = run(command_id, argv, root, environment)
            if command_id.startswith("m02-"):
                if stdout != "" or "Ran 2 tests" not in stderr or not stderr.rstrip().endswith("OK"):
                    raise RuntimeError("unexpected unittest streams: " + command_id)
            elif stdout != "PASS_PENDING_FREE_INVENTORY|executed=46|selectors=23|programs=2|state_hashes=equal\n" or stderr != "":
                raise RuntimeError("unexpected M03 streams")
            results.append(record)
        result = {"commands": len(results), "input_sha256": INPUTS,
            "max_processes": MAX_PROCESSES, "max_rss_bytes": MAX_RSS_BYTES,
            "max_tree_bytes": MAX_TREE_BYTES, "poll_seconds": POLL_SECONDS,
            "status": "PASS_LAYER_B_MICROTESTS"}
        durable_json(root / "result.json", result)
        print("PASS_LAYER_B_MICROTESTS|commands=3|m02_tests=4|m03_runs=46")
    except BaseException as error:
        failure = type(error).__name__ + ": " + str(error)
        durable_json(root / "failure.json", {"error": failure, "timestamp_ns": time.time_ns()})
        durable_text(root / "failure.txt", failure + "\n")
        raise


if __name__ == "__main__":
    main()
