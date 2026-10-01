#!/usr/bin/env python3
"""Read-only cgroup-v1 observations of one exact diagnostic container.

This sidecar does not own the container or authorize guest execution. It
writes a report only after a verified exit of the same owned container.
"""

import argparse
import errno
import json
import math
import os
import re
import selectors
import subprocess
import time


CID_RE = re.compile(r"[0-9a-f]{64}\Z")
NONCE_RE = re.compile(r"[0-9a-f]{32}\Z")
PROC_ROOT = "/proc"
CGROUP_ROOT = "/sys/fs/cgroup"
DOCKER = ("/usr/bin/sudo", "-A", "/usr/bin/docker")
IMAGE = "sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94"
FILES = {"memory": ("memory.max_usage_in_bytes", "memory.usage_in_bytes"),
         "cpuacct": ("cpuacct.usage",), "cpu": ("cpu.stat",),
         "pids": ("pids.current", "pids.max")}
MAX_SAMPLES = 4096


class ObserverError(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise ObserverError(message)


def read(path, limit=65536):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        data = os.read(fd, limit + 1)
    finally:
        os.close(fd)
    need(len(data) <= limit, "oversized read: " + path)
    return data


def inspect(container_id):
    """Read only Docker inspect, with a deadline and capped stdout/stderr."""
    argv = (*DOCKER, "inspect", "--type", "container", container_id)
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, close_fds=True)
    output = {process.stdout: bytearray(), process.stderr: bytearray()}
    deadline = time.monotonic() + 5
    try:
        with selectors.DefaultSelector() as selector:
            for stream in output:
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                need(remaining > 0, "Docker inspect timeout")
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fileobj.fileno(), 65537)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        output[key.fileobj].extend(chunk)
                        need(len(output[key.fileobj]) <= 65536, "oversized Docker inspect")
        need(process.wait(timeout=max(0.001, deadline - time.monotonic())) == 0,
             "Docker inspect failed")
        rows = json.loads(output[process.stdout].decode("utf-8"))
        need(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict,
             "ambiguous Docker inspect")
        return rows[0]
    except (ValueError, UnicodeError) as exc:
        raise ObserverError("malformed Docker inspect") from exc
    except subprocess.TimeoutExpired as exc:
        raise ObserverError("Docker inspect timeout") from exc
    finally:
        if process.poll() is None:
            process.kill()  # Only this inspect client; never the container.
        process.wait()
        process.stdout.close()
        process.stderr.close()


def container_state(row, container_id, nonce):
    need(type(row) is dict and row.get("Id") == container_id and
         row.get("Name") == "/mckernel-native-diagnostic-" + nonce and
         row.get("Image") == IMAGE, "container ID/name/image drift")
    host = row.get("HostConfig")
    need(type(host) is dict and host.get("CgroupParent") == "/mckernel-dev",
         "container cgroup parent drift")
    config = row.get("Config")
    need(type(config) is dict and type(config.get("Labels")) is dict and
         config["Labels"].get("mckernel.native-diagnostic.owner") == nonce,
         "owner label drift")
    state = row.get("State")
    need(type(state) is dict and type(state.get("Running")) is bool,
         "ambiguous container state")
    need((state.get("Status") == "running" if state["Running"] else
          state.get("Status") in ("exited", "dead")), "inconsistent container state")
    pid = state.get("Pid")
    need(type(pid) is int and (pid > 0 if state["Running"] else pid == 0),
         "ambiguous container PID")
    return state["Running"], pid


def proc_start(pid):
    need(type(pid) is int and pid > 0, "invalid PID")
    raw = read("%s/%d/stat" % (PROC_ROOT, pid), 4096).decode("ascii")
    end = raw.rfind(")")
    need(raw.startswith(str(pid) + " (") and end > len(str(pid)) + 2 and
         raw[end + 1:end + 2] == " ", "malformed process identity")
    fields = raw[end + 2:].split()
    need(len(fields) >= 20 and fields[19].isdigit() and int(fields[19]) > 0,
         "malformed process start time")
    return int(fields[19])


def owned_path(path, container_id):
    parts = path.split("/")
    need(path.startswith("/") and all(part not in ("", ".", "..") for part in parts[1:]),
         "malformed cgroup path")
    need(parts[1:] in (["mckernel-dev", container_id],
                       ["mckernel-dev", "docker", container_id],
                       ["mckernel-dev", "docker-" + container_id + ".scope"]),
         "cgroup is not the exact owned container")


def membership(pid, container_id):
    lines = read("%s/%d/cgroup" % (PROC_ROOT, pid)).decode("ascii").splitlines()
    need(lines, "empty cgroup membership")
    result, hierarchies = {}, set()
    for line in lines:
        parts = line.split(":", 2)
        need(len(parts) == 3 and parts[0].isdigit() and parts[0] not in hierarchies,
             "malformed or duplicate cgroup hierarchy")
        hierarchies.add(parts[0])
        hierarchy, controllers, path = parts
        names = controllers.split(",") if controllers else []
        need(len(names) == len(set(names)) and all(names) and path.startswith("/"),
             "malformed cgroup membership")
        for controller in FILES:
            if controller in names:
                need(controller not in result and hierarchy != "0",
                     "ambiguous cgroup controller: " + controller)
                owned_path(path, container_id)
                result[controller] = CGROUP_ROOT + "/" + controller + path
    need(result, "no owned cgroup-v1 controller")
    return result


def counter(path):
    try:
        value = read(path, 256).decode("ascii").strip()
    except OSError as exc:
        if exc.errno in (errno.ENOENT, errno.EACCES, errno.EPERM):
            return None
        raise
    need(value.isascii() and value.isdigit(), "malformed counter: " + path)
    return int(value)


def pids_limit(path):
    try:
        value = read(path, 256).decode("ascii").strip()
    except OSError as exc:
        if exc.errno in (errno.ENOENT, errno.EACCES, errno.EPERM):
            return None
        raise
    if value == "max":
        return value
    need(value.isascii() and value.isdigit(), "malformed pids.max")
    return int(value)


def cpu_stat(path):
    try:
        raw = read(path, 4096).decode("ascii")
    except OSError as exc:
        if exc.errno in (errno.ENOENT, errno.EACCES, errno.EPERM):
            return None
        raise
    stat = {}
    for line in raw.splitlines():
        parts = line.split()
        need(len(parts) == 2 and parts[0].isidentifier() and parts[1].isascii() and
             parts[1].isdigit() and parts[0] not in stat, "malformed cpu.stat")
        stat[parts[0]] = int(parts[1])
    # A syntactically valid but incomplete cpu.stat is not a measurement.  In
    # particular, accepting only nr_periods would make a throttling report
    # look complete while silently losing the throttled counters.  cgroup-v1
    # exposes throttled_time; tolerate the kernel's spelling variant only for
    # fixtures/forward compatibility, but require the complete core tuple.
    need(stat and {"nr_periods", "nr_throttled"}.issubset(stat) and
         ("throttled_time" in stat or "throttled_usec" in stat),
         "incomplete cpu.stat")
    return stat


def sample(paths):
    values, missing = {}, []
    for controller, names in FILES.items():
        for name in names:
            key = controller + "." + name
            if controller not in paths:
                missing.append(key)
                continue
            path = paths[controller] + "/" + name
            if name == "cpu.stat":
                value = cpu_stat(path)
            elif name == "pids.max":
                value = pids_limit(path)
            else:
                value = counter(path)
            if value is None:
                missing.append(key)
            else:
                values[key] = value
    need(not missing, "incomplete cgroup resource sampling: " + ",".join(missing))
    need(values, "no cgroup counters available")
    return {"counters": values, "missing": missing, "monotonic_ns": time.monotonic_ns()}


def write_result(output, result):
    raw = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
    need(len(raw) <= 16 * 1024 * 1024, "oversized result")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            need(written > 0, "output write stalled")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def observe(container_id, nonce, output, *, timeout=300, interval=0.1,
            inspect_container=inspect, sleep=time.sleep, clock=time.monotonic):
    need(type(container_id) is str and CID_RE.fullmatch(container_id), "full container ID required")
    need(type(nonce) is str and NONCE_RE.fullmatch(nonce), "owner nonce required")
    need(type(output) is str and output.startswith("/"), "absolute output path required")
    need(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 300,
         "invalid timeout")
    need(type(interval) in (int, float) and math.isfinite(interval) and 0.05 <= interval <= timeout,
         "invalid interval")
    need(not os.path.lexists(output), "output already exists")
    deadline = clock() + timeout
    rows = []
    pid = start = paths = None
    while True:
        need(clock() < deadline, "observation timeout before verified exit")
        running, current_pid = container_state(inspect_container(container_id), container_id, nonce)
        if not running:
            need(rows, "container stopped before first sample")
            # Docker can report exit before procfs has retired the exact
            # process. Publish only after that identity is gone; never signal
            # or kill the container from this observer.
            try:
                proc_start(pid)
            except OSError as exc:
                need(exc.errno == errno.ENOENT, "unexpected process retirement error")
            else:
                need(False, "container PID not retired")
            break
        if pid is None:
            pid = current_pid
            start = proc_start(pid)
            paths = membership(pid, container_id)
        else:
            need(current_pid == pid and proc_start(pid) == start,
                 "container process identity drift")
            need(membership(pid, container_id) == paths, "cgroup membership drift")
        row = sample(paths)
        need(proc_start(pid) == start and membership(pid, container_id) == paths,
             "process/cgroup identity drift during sample")
        rows.append(row)
        need(len(rows) <= MAX_SAMPLES, "sample limit before verified exit")
        sleep(min(interval, max(0, deadline - clock())))

    peaks = {}
    for key in ("memory.memory.max_usage_in_bytes", "memory.memory.usage_in_bytes",
                "pids.pids.current", "cpu.cpu.stat.nr_throttled",
                "cpu.cpu.stat.throttled_time"):
        if key.startswith("cpu.cpu.stat."):
            values = [row["counters"].get("cpu.cpu.stat", {}).get(key.rsplit(".", 1)[1])
                      for row in rows]
        else:
            values = [row["counters"].get(key) for row in rows]
        available = [value for value in values if value is not None]
        peaks[key] = max(available) if available else None
    cpu_key = "cpuacct.cpuacct.usage"
    first, last = rows[0]["counters"].get(cpu_key), rows[-1]["counters"].get(cpu_key)
    need(first is None or last is None or last >= first, "CPU counter decreased")
    rates = []
    for before, after in zip(rows, rows[1:]):
        b, a = before["counters"].get(cpu_key), after["counters"].get(cpu_key)
        elapsed = after["monotonic_ns"] - before["monotonic_ns"]
        need(elapsed >= 0 and (b is None or a is None or a >= b),
             "counter/time reversal")
        if b is not None and a is not None and elapsed:
            rates.append(1000 * (a - b) // elapsed)
        old_peak = before["counters"].get("memory.memory.max_usage_in_bytes")
        new_peak = after["counters"].get("memory.memory.max_usage_in_bytes")
        need(old_peak is None or new_peak is None or new_peak >= old_peak,
             "memory peak counter decreased")
    result = {"status": "PARTIAL" if any(row["missing"] for row in rows) else "MEASURED",
              "scope": "diagnostic-only", "container_id": container_id,
              "owner_nonce": nonce, "pid": pid, "proc_starttime": start,
              "cgroup_paths": paths, "sample_count": len(rows), "samples": rows,
              "peaks": peaks, "cpu_delta_ns": last - first if len(rows) > 1 and
              first is not None and last is not None else None,
              "peak_sampled_cpu_millicores": max(rates) if rates else None,
              "elapsed_ns": rows[-1]["monotonic_ns"] - rows[0]["monotonic_ns"],
              "stop_reason": "verified_container_exit"}
    write_result(output, result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--container-id", required=True)
    parser.add_argument("--owner-nonce", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--interval", type=float, default=0.1)
    args = parser.parse_args()
    observe(args.container_id, args.owner_nonce, args.output,
            timeout=args.timeout, interval=args.interval)


if __name__ == "__main__":
    main()
