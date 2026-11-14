#!/usr/bin/env python3
"""Two isolated, resource-bounded diagnostic guests; never formal acceptance.

One process holds the existing development lock for both containers.  Each
guest has a separate Docker identity, two *different physical* host cores,
seven GiB/no swap, a private output root and its own result.  This deliberately
does not change the published single-guest owner or its execution releases.
"""

import argparse
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid


REPO = Path("/home/holden/mckernel")
SCRATCH = Path("/home/holden/mckernel-work/scratch")
RUNNER = REPO / "scripts/application-tests/native_diagnostic_runner.py"
DIAGNOSTIC = REPO / "scripts/application-tests/native_diagnostic.py"
IMAGE = "sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94"
LOCK = Path("/run/lock/mckernel-development.lock")
DOCKER = ("/usr/bin/sudo", "-A", "/usr/bin/docker")
SLOTS = ((2, 3), (4, 5))
CONTAINER_MEMORY = 7 * 1024 ** 3
GIB = 1024 ** 3
HEX = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_FILES = (RUNNER, DIAGNOSTIC, REPO / "scripts/application-tests/native_diagnostic_backend.py",
                REPO / "scripts/application-tests/qmp_capture.py")


class PilotError(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise PilotError(message)


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def input_hashes(manifests):
    return {str(path): sha(path) for path in (*SOURCE_FILES, *manifests)}


def privileged(*args):
    result = subprocess.run(["/usr/bin/sudo", "-A", *args], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    need(result.returncode == 0, "private snapshot operation failed: " + args[0])


def prepare_source_snapshot(manifests, nonce):
    """Freeze runtime code and manifests under a root-owned sticky-parent path."""
    originals = (*SOURCE_FILES, *manifests)
    before = input_hashes(manifests)
    directory = Path("/run/lock/mckernel-dual-snapshot-" + nonce)
    need(not directory.exists() and not directory.is_symlink(), "private snapshot name in use")
    privileged("/usr/bin/install", "-d", "-m", "0755", "--", str(directory))
    copies = []
    for index, source in enumerate(originals):
        need(source.is_file() and not source.is_symlink(), "runtime input is not regular")
        target = directory / (source.name if index < len(SOURCE_FILES) else "manifest-%d.json" % (index - len(SOURCE_FILES)))
        privileged("/usr/bin/cp", "--", str(source), str(target))
        copies.append(target)
    privileged("/usr/bin/chmod", "0444", "--", *(str(copy) for copy in copies))
    privileged("/usr/bin/chmod", "0555", "--", str(directory))
    need(directory.stat().st_uid == 0 and stat.S_IMODE(directory.stat().st_mode) == 0o555 and
         all(copy.stat().st_uid == 0 and stat.S_IMODE(copy.stat().st_mode) == 0o444
             for copy in copies), "private snapshot ownership/mode drift")
    sealed = {str(copy): sha(copy) for copy in copies}
    need(input_hashes(manifests) == before and
         all(sealed[str(copy)] == before[str(source)] for source, copy in zip(originals, copies)),
         "input changed during private snapshot")
    return directory, sealed, copies[len(SOURCE_FILES):]


def timestamp(value):
    need(isinstance(value, str) and value not in ("", "0001-01-01T00:00:00Z"),
         "Docker event timestamp unavailable")
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})", value)
    need(match is not None, "invalid Docker event timestamp")
    fraction = (match.group(2) or "0")[:6].ljust(6, "0")
    zone = "+00:00" if match.group(3) == "Z" else match.group(3)
    return datetime.fromisoformat(match.group(1) + "." + fraction + zone).timestamp()


def overlap_seconds(states):
    """Require observed Docker state intervals to overlap, not merely wall-clock batching."""
    intervals = [(timestamp(state["StartedAt"]), timestamp(state["FinishedAt"])) for state in states]
    need(all(end > start for start, end in intervals), "invalid Docker guest interval")
    if len(intervals) == 1:
        return 0.0
    overlap = min(end for _, end in intervals) - max(start for start, _ in intervals)
    need(overlap >= 1.0, "guests did not overlap for one second")
    return round(overlap, 3)


def canonical_file(value):
    path = Path(value)
    need(path.is_absolute() and not path.is_symlink() and path.is_file() and
         str(path.resolve(strict=True)) == str(path), "manifest must be a canonical regular file")
    return path


def diagnostic_module():
    spec = importlib.util.spec_from_file_location("dual_native_diagnostic", DIAGNOSTIC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_manifest(path):
    module = diagnostic_module()
    manifest = module.load_manifest(str(canonical_file(path)))
    need(manifest["profile"]["name"] == module.PROFILE_DUAL,
         "dual pilot requires the four-vCPU/six-GiB profile")
    return manifest


def derive_dual_manifest(source):
    """Preserve exact inputs while selecting the testable 4-vCPU/6-GiB topology."""
    module = diagnostic_module()
    source = canonical_file(source)
    original = module.load_manifest(str(source))
    need(original["profile"]["name"] in (module.PROFILE_SMALL, module.PROFILE_RETAINED),
         "derive only from a bound small or retained diagnostic manifest")
    raw = json.loads(source.read_text())
    raw["profile"] = {"name": module.PROFILE_DUAL, "memory_mib": 6144,
                      "vcpus": 4, "numa_nodes": 2}
    directory = Path(tempfile.mkdtemp(prefix="dual-profile-", dir=str(SCRATCH)))
    path = directory / "manifest.json"
    data = (json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    load_manifest(path)
    return path


def mem_available():
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        parts = line.split()
        if parts[:1] == ["MemAvailable:"] and len(parts) == 3 and parts[2] == "kB":
            return int(parts[1]) * 1024
    raise PilotError("MemAvailable unavailable")


def admit(guests=2):
    """Refuse overcommit; four selected logical CPUs must be four real cores."""
    affinity = os.sched_getaffinity(0)
    chosen = set(SLOTS[0] + SLOTS[1])
    need(chosen <= affinity, "four selected CPUs are not in this process affinity")
    cores = []
    for cpu in sorted(chosen):
        base = Path("/sys/devices/system/cpu") / ("cpu%d" % cpu) / "topology"
        cores.append((int((base / "physical_package_id").read_text()),
                      int((base / "core_id").read_text())))
    need(len(set(cores)) == 4, "selected CPUs share physical cores")
    need(guests in (1, 2), "only one or two bounded guests")
    need(mem_available() >= guests * CONTAINER_MEMORY + 4 * GIB,
         "guest limits plus four-GiB host reserve unavailable")
    need(shutil.disk_usage(REPO).free >= 16 * GIB and
         shutil.disk_usage(SCRATCH).free >= 12 * GIB,
         "host/scratch free-space floor")
    need(SCRATCH.is_mount(), "scratch mount missing")
    return {"cpusets": ["2,3", "4,5"], "physical_cores": cores,
            "mem_available_bytes": mem_available(), "host_free_bytes": shutil.disk_usage(REPO).free,
            "scratch_free_bytes": shutil.disk_usage(SCRATCH).free}


def docker(*args, timeout=20, allow_failure=False):
    command = [*DOCKER, *args]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    output = {process.stdout: bytearray(), process.stderr: bytearray()}
    oversized = False
    deadline = None if timeout is None else time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for stream in output:
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                remaining = None if deadline is None else max(0, deadline - time.monotonic())
                if remaining == 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        budget = max(0, 1024 * 1024 - len(output[key.fileobj]))
                        output[key.fileobj].extend(chunk[:budget])
                        oversized |= len(chunk) > budget
        remaining = None if deadline is None else max(0.001, deadline - time.monotonic())
        code = process.wait(timeout=remaining)
        need(not oversized, "Docker CLI output exceeded one-MiB cap")
        result = subprocess.CompletedProcess(command, code, bytes(output[process.stdout]),
                                             bytes(output[process.stderr]))
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()
    if not allow_failure and result.returncode:
        raise PilotError("docker %s failed: %s" % (args[0], result.stderr.decode("utf-8", "replace")[:500]))
    return result


def inspect_one(cid):
    value = json.loads(docker("inspect", cid).stdout)
    need(type(value) is list and len(value) == 1 and value[0]["Id"] == cid, "Docker inspect identity")
    return value[0]


def acquire_lock():
    fd = os.open(LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1,
             "development lock identity")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def create_args(name, nonce, cpus, parent, manifest, runtime_runner=None, runtime_dir=None):
    runtime_runner = RUNNER if runtime_runner is None else runtime_runner
    return ("create", "--pull=never", "--name=" + name,
            "--label=mckernel.dual-pilot.owner=" + nonce,
            "--cpus=2", "--cpuset-cpus=" + ",".join(map(str, cpus)),
            "--memory=7g", "--memory-swap=7g", "--pids-limit=256",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only", "--network=none",
            "--user=1000:1000", "--ulimit", "core=0", "--ulimit", "fsize=104857600:104857600",
            "--log-driver=local", "--log-opt=max-size=5m", "--log-opt=max-file=2",
            "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m",
            "--mount", "type=bind,src=" + str(REPO) + ",dst=" + str(REPO) + ",readonly",
            "--mount", "type=bind,src=" + str(SCRATCH) + ",dst=" + str(SCRATCH) + ",readonly",
            *(("--mount", "type=bind,src=" + str(runtime_dir) + ",dst=" + str(runtime_dir) + ",readonly")
              if runtime_dir is not None else ()),
            "--mount", "type=bind,src=" + str(parent) + ",dst=" + str(parent),
            "--env", "HOME=/tmp", "--env", "TMPDIR=/tmp", "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--workdir=" + str(parent), "--entrypoint=/usr/bin/python3", IMAGE,
            "-B", str(runtime_runner), "--manifest", str(manifest), "--attempt-parent", str(parent),
            "--attempt-name", "attempt", "--timeout", "300")


def verify_created(row, cid, name, cpus, parent, nonce, manifest, runtime_runner=None, runtime_dir=None):
    runtime_runner = RUNNER if runtime_runner is None else runtime_runner
    host = row["HostConfig"]
    labels = row["Config"]["Labels"]
    need(row["Id"] == cid and row["Name"] == "/" + name and row["Image"] == IMAGE and
         labels.get("mckernel.dual-pilot.owner") == nonce, "container ownership drift")
    need(host["NanoCpus"] == 2_000_000_000 and host["CpusetCpus"] == ",".join(map(str, cpus)) and
         host["Memory"] == CONTAINER_MEMORY and host["MemorySwap"] == CONTAINER_MEMORY and
         host["PidsLimit"] == 256 and host["NetworkMode"] == "none" and
         host["Privileged"] is False and host["ReadonlyRootfs"] is True and
         host["CapDrop"] == ["ALL"] and host.get("CapAdd") in (None, []) and
         host.get("PidMode") == "" and host.get("IpcMode") == "private" and
         host.get("UsernsMode") == "" and host.get("Devices") in (None, []) and
         host.get("RestartPolicy", {}).get("Name") == "no", "resource/isolation profile drift")
    expected_mounts = {str(REPO): (str(REPO), False), str(SCRATCH): (str(SCRATCH), False),
                       str(parent): (str(parent), True)}
    if runtime_dir is not None:
        expected_mounts[str(runtime_dir)] = (str(runtime_dir), False)
    mounts = row["Mounts"]
    need(len(mounts) == len(expected_mounts) and
         {m["Destination"] for m in mounts} == set(expected_mounts) and
         all(m["Type"] == "bind" and (m["Source"], m["RW"]) == expected_mounts[m["Destination"]]
             for m in mounts), "bind-mount isolation drift")
    config = row["Config"]
    expected_cmd = ["-B", str(runtime_runner), "--manifest", str(manifest),
                    "--attempt-parent", str(parent), "--attempt-name", "attempt",
                    "--timeout", "300"]
    need(config["User"] == "1000:1000" and config["WorkingDir"] == str(parent) and
         config["Entrypoint"] == ["/usr/bin/python3"] and config["Cmd"] == expected_cmd and
         {"HOME=/tmp", "TMPDIR=/tmp", "PYTHONDONTWRITEBYTECODE=1"} <= set(config["Env"]),
         "entrypoint drift")
    need(host["LogConfig"]["Type"] == "local" and
         host["LogConfig"]["Config"] == {"max-size": "5m", "max-file": "2"} and
         host["SecurityOpt"] == ["no-new-privileges"] and
         host["Tmpfs"] == {"/tmp": "rw,nodev,nosuid,size=256m"} and
         {item["Name"]: (item["Soft"], item["Hard"]) for item in host["Ulimits"]} ==
         {"core": (0, 0), "fsize": (104857600, 104857600)},
         "output/security cap drift")
    need(row["State"]["Status"] == "created", "guest started before profile verification")


def lookup(name, nonce):
    views = []
    for key in ("name=^/" + name + "$", "label=mckernel.dual-pilot.owner=" + nonce):
        result = docker("ps", "-aq", "--no-trunc", "--filter", key)
        ids = result.stdout.decode("ascii").splitlines()
        need(len(ids) <= 2 and all(HEX.fullmatch(cid) for cid in ids), "ambiguous owned container")
        views.append(ids)
    named = views[0]
    need(len(named) <= 1 and all(cid in views[1] for cid in named), "name/label owner mismatch")
    return named[0] if named else None


def owned_census(names, nonce):
    """Find owned IDs by label AND all exact reserved names, including renamed IDs."""
    result = docker("ps", "-aq", "--no-trunc", "--filter", "label=mckernel.dual-pilot.owner=" + nonce)
    owned = result.stdout.decode("ascii").splitlines()
    need(len(owned) <= len(names) and len(set(owned)) == len(owned) and
         all(HEX.fullmatch(cid) for cid in owned), "ambiguous owned container census")
    for name in names:
        result = docker("ps", "-aq", "--no-trunc", "--filter", "name=^/" + name + "$")
        named = result.stdout.decode("ascii").splitlines()
        need(len(named) <= 1 and all(HEX.fullmatch(cid) and cid in owned for cid in named),
             "reserved name belongs to another container")
    for cid in owned:
        row = inspect_one(cid)
        need(row["Config"]["Labels"].get("mckernel.dual-pilot.owner") == nonce,
             "owned label changed during cleanup")
    return owned


def cleanup(names, nonce):
    """Hold the lock until both exact owned containers are provably absent."""
    empty_once = False
    while True:
        try:
            owned = owned_census(names, nonce)
            if not owned:
                if empty_once:
                    return
                empty_once = True
            else:
                empty_once = False
                for cid in owned:
                    docker("stop", "--time=2", cid, timeout=8, allow_failure=True)
                    docker("rm", "--force", cid, timeout=12, allow_failure=True)
        except Exception as exc:
            empty_once = False
            print("cleanup retry: %s" % type(exc).__name__, file=sys.stderr, flush=True)
        time.sleep(2)


def run_guests(manifests):
    need(os.environ.get("SUDO_ASKPASS") and os.environ.get("MCKERNEL_OS_SUDO_CREDENTIAL"),
         "configure the existing private sudo helper")
    need(type(manifests) is list and len(manifests) == 2, "two manifests required for a parallel pilot")
    manifests = [canonical_file(path) for path in manifests]
    parsed = [load_manifest(path) for path in manifests]
    snapshot = admit(len(manifests))
    lock = acquire_lock()
    nonce = uuid.uuid4().hex
    names = ["mckernel-dual-pilot-" + nonce + "-" + str(i) for i in range(len(manifests))]
    output = Path(tempfile.mkdtemp(prefix="dual-guest-", dir=str(SCRATCH)))
    os.chmod(output, 0o700)
    parents, cids, processes = [], [], []
    summary = None
    previous_signals = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    interrupted = []

    def request_stop(number, _frame):
        # Defer the exception until a Docker create CLI has returned, so its
        # daemon request cannot complete after we pronounce cleanup finished.
        interrupted.append(number)

    def check_stop():
        need(not interrupted, "interrupted by signal %s" % (interrupted[0] if interrupted else ""))

    try:
        for number in previous_signals:
            signal.signal(number, request_stop)
        admit(len(manifests))  # Recheck under the lease, immediately before creating guests.
        before_hashes = input_hashes(manifests)
        source_dir, source_hashes, sealed_manifests = prepare_source_snapshot(manifests, nonce)
        runtime_runner = source_dir / RUNNER.name
        image = json.loads(docker("image", "inspect", IMAGE).stdout)
        need(type(image) is list and len(image) == 1 and image[0]["Id"] == IMAGE and
             image[0]["Architecture"] == "amd64" and image[0]["Os"] == "linux", "pinned image drift")
        for i, manifest in enumerate(sealed_manifests):
            parent = output / ("guest-" + str(i))
            parent.mkdir(mode=0o700)
            parents.append(parent)
            args = create_args(names[i], nonce, SLOTS[i], parent, manifest,
                               runtime_runner, source_dir)
            # A create request must return before cleanup; otherwise a daemon
            # operation could appear after an empty-container observation.
            check_stop()
            result = docker(*args, timeout=None)
            cid = result.stdout.decode("ascii").strip()
            need(HEX.fullmatch(cid), "Docker create did not return full CID")
            cids.append(cid)
            verify_created(inspect_one(cid), cid, names[i], SLOTS[i], parent, nonce,
                           manifest, runtime_runner, source_dir)
            check_stop()
        admit(len(manifests))
        need(input_hashes(manifests) == before_hashes and
             {str(path): sha(path) for path in source_dir.iterdir()} == source_hashes,
             "input/source changed before guest start")
        guests_started_at = time.monotonic()
        for i, cid in enumerate(cids):
            check_stop()
            processes.append(subprocess.Popen([*DOCKER, "start", "--attach", cid],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True))
        deadline = time.monotonic() + 360
        while any(process.poll() is None for process in processes):
            check_stop()
            if time.monotonic() >= deadline:
                raise PilotError("pair deadline; exact guests will be stopped and retained")
            if any(process.poll() not in (None, 0) for process in processes):
                raise PilotError("one guest start failed; stopping peer")
            need(shutil.disk_usage(REPO).free >= 16 * GIB and
                 shutil.disk_usage(SCRATCH).free >= 12 * GIB,
                 "free-space floor crossed during guest execution")
            time.sleep(0.2)
        results = []
        states = []
        for i, cid in enumerate(cids):
            row = inspect_one(cid)
            state = row["State"]
            need(state["Status"] == "exited" and state["ExitCode"] == 0 and
                 state["OOMKilled"] is False and processes[i].returncode == 0,
                 "guest exited unsuccessfully")
            states.append(state)
            result_path = parents[i] / "attempt" / "result.json"
            with result_path.open("rb") as stream:
                payload = stream.read(1024 * 1024 + 1)
            need(len(payload) <= 1024 * 1024, "inner result exceeded one-MiB cap")
            result = json.loads(payload)
            need(result.get("status") == "PROTOCOL_PASS" and
                 result.get("application_acceptance") is False and
                 result.get("mckernel_application_executed") is False and
                 result.get("capture_errors") == [] and
                 result.get("case_id") == parsed[i]["case_id"] and
                 result.get("cleanup") == {"reaped": True, "errors": []},
                 "inner diagnostic/result mismatch")
            results.append({"case_id": parsed[i]["case_id"], "container": cid,
                            "manifest_sha256": sha(manifests[i]), "result_sha256": sha(result_path)})
        actual_overlap = overlap_seconds(states)
        need(input_hashes(manifests) == before_hashes and
             {str(path): sha(path) for path in source_dir.iterdir()} == source_hashes,
             "input/source changed during guest execution")
        summary = {"status": "DIAGNOSTIC_PASS", "application_acceptance": False,
                   "kind": "isolated-small-guest-pilot", "resource_snapshot": snapshot,
                   "output": str(output), "guest_count": len(results),
                   "pair_wall_seconds": round(time.monotonic() - guests_started_at, 3),
                   "observed_overlap_seconds": actual_overlap,
                   "input_sha256": before_hashes, "sealed_input_sha256": source_hashes,
                   "results": results}
        return summary
    except BaseException as exc:
        (output / "failure.txt").write_text(type(exc).__name__ + ": " + str(exc)[:500] + "\n")
        for i, cid in enumerate(cids):
            try:
                row = inspect_one(cid)
                evidence = {"container": cid, "state": row["State"],
                            "docker_log_tail": docker("logs", "--tail=100", cid,
                                                      timeout=10, allow_failure=True).stdout.decode("utf-8", "replace")[:4096]}
                (parents[i] / "docker-failure.json").write_text(json.dumps(evidence, sort_keys=True) + "\n")
            except Exception:
                pass
        raise
    finally:
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(number, signal.SIG_IGN)
        cleaned = False
        try:
            cleanup(names, nonce)
            cleaned = True
            for process in processes:
                if process.poll() is None:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=5)
            if summary is not None:
                with (output / "summary.json").open("x", encoding="utf-8") as stream:
                    json.dump(summary, stream, sort_keys=True, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
        finally:
            for number, handler in previous_signals.items():
                signal.signal(number, handler)
            if cleaned:
                fcntl.flock(lock, fcntl.LOCK_UN)
                os.close(lock)
            print("dual diagnostic evidence: " + str(output), file=sys.stderr, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_a")
    parser.add_argument("manifest_b", nargs="?")
    parser.add_argument("--derive-dual", action="store_true",
                        help="Write a bound four-vCPU/six-GiB manifest from a small or retained manifest")
    parser.add_argument("--execute", action="store_true", help="Launch two bounded Docker guests")
    args = parser.parse_args(argv)
    if args.derive_dual:
        need(args.manifest_b is None and not args.execute, "derive takes one source and never executes")
        path = derive_dual_manifest(args.manifest_a)
        print(json.dumps({"status": "DERIVED", "manifest": str(path), "sha256": sha(path)}, sort_keys=True))
        return 0
    manifests = [canonical_file(args.manifest_a)]
    if args.manifest_b is not None:
        manifests.append(canonical_file(args.manifest_b))
    parsed = [load_manifest(path) for path in manifests]
    if not args.execute:
        print(json.dumps({"status": "READY_TO_MEASURE", "cases": [row["case_id"] for row in parsed],
                          "resources": admit(len(manifests)), "execution": False}, sort_keys=True))
        return 0
    print(json.dumps(run_guests(manifests), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
