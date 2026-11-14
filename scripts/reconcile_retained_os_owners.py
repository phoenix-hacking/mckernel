#!/usr/bin/env python3
"""Root-only exact old McKernel actor cancellation and resource observations.

Functional OS/Rust cleanup only; NO SECURITY TESTING. Default is a read-only
plan. No waitpid, original tool poll, FD byte read, private IPC entry, FLOCK,
Docker action, ledger edit or resource release. --apply uses the existing
pidfd_compat implementation and requires an independently reviewed exact plan.
Every attempt checkpoints before signals. Observations are input to Q/Root,
never historical successful waits or permission to reuse unresolved resources.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import socket
import stat
import struct
import time

import pidfd_compat

ROOT_THREAD = "01a18bc3-e072-7810-9426-75101b0856c0"
ORIGIN = "20261112T094452Z-12a4bea0"
CREDIT_RUN = "7c6ef3604bfb4008a917bba8cfb6cfaa"
# Source-owned original identities, not a grant to signal a reused numeric PID.
ACTORS = ((2342216, "66270999"), (2342218, "66271010"),
          (2318455, "65818096"), (2318467, "65818149"),
          (2318474, "65818157"), (2318476, "65818170"), (2318477, "65818186"))
MAX_READ = 16 * 1024 * 1024
MAX_TASKS = 65536


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, limit=MAX_READ):
    with open(path, "rb", buffering=0) as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "Metadata read exceeded bound: " + str(path))
    return raw


def identity(meta):
    return {"device": meta.st_dev, "inode": meta.st_ino, "mode": meta.st_mode,
            "rdev": meta.st_rdev}


def process(pid):
    root = Path("/proc") / str(pid)
    raw = read(root / "stat", 8192)
    tail = raw.rsplit(b")", 1)[1].split()
    require(len(tail) >= 20, "Incomplete process stat")
    status = read(root / "status", 65536).decode()
    uids = [line.split()[1:] for line in status.splitlines() if line.startswith("Uid:")]
    require(len(uids) == 1 and len(uids[0]) == 4 and all(value.isdecimal() for value in uids[0]),
            "Complete process UID metadata required")
    return {"pid": pid, "start": tail[19].decode(), "parent": int(tail[1]),
            "state": tail[0].decode(), "uids": [int(value) for value in uids[0]],
            "procfs_owner_uid": root.stat().st_uid}


def process_table():
    rows = {}
    pids = sorted(int(row.name) for row in Path("/proc").iterdir() if row.name.isdigit())
    require(len(pids) <= MAX_TASKS, "Process census exceeds bound")
    for pid in pids:
        try:
            rows[pid] = process(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue  # A vanished process cannot retain an FD; final sweep repeats.
    return rows


def fd_snapshot(task):
    out = []
    for entry in sorted((task / "fd").iterdir(), key=lambda row: int(row.name)):
        try:
            link = os.readlink(entry)
            meta = entry.stat()
            info = read(task / "fdinfo" / entry.name, 65536).decode()
            mnt = [line.split(":", 1)[1].strip() for line in info.splitlines() if line.startswith("mnt_id:")]
            out.append(dict(identity(meta), fd=int(entry.name), link=link,
                            mount_id=mnt[0] if len(mnt) == 1 else None))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return out


def pin_process(row):
    root = Path("/proc") / str(row["pid"])
    before = process(row["pid"])
    require(before["start"] == row["start"], "Actor birth changed before pin")
    exe = root / "exe"
    result = dict(before, exe=os.readlink(exe), exe_identity=identity(exe.stat()),
                  process_root_link=os.readlink(root / "root"),
                  process_root_identity=identity((root / "root").stat()),
                  cmdline_sha256=sha(read(root / "cmdline", 131072)),
                  namespaces={p.name: os.readlink(p) for p in (root / "ns").iterdir()},
                  cgroup=read(root / "cgroup", 65536).decode(),
                  mountinfo_sha256=sha(read(root / "mountinfo")),
                  fds=fd_snapshot(root))
    require(process(row["pid"])["start"] == before["start"], "Actor changed during pin")
    return result


def decode_unix_diag(raw, sequence):
    """Decode only kernel UNIX socket inode/peer/queue metadata, never payloads."""
    rows, done = [], False
    offset = 0
    while offset < len(raw):
        require(len(raw) - offset >= 16, "Truncated UNIX diagnostic header")
        size, kind, flags, seq, pid = struct.unpack_from("=IHHII", raw, offset)
        require(16 <= size <= len(raw) - offset and seq == sequence,
                "UNIX diagnostic frame identity/length differs")
        require(not flags & 0x10, "Interrupted UNIX diagnostic dump is incomplete")
        payload = raw[offset + 16:offset + size]
        if kind == 3:
            require(not payload or (len(payload) >= 4 and struct.unpack_from("=i", payload)[0] == 0),
                    "Incomplete UNIX diagnostic dump")
            done = True
        elif kind == 2:
            require(len(payload) >= 4 and struct.unpack_from("=i", payload)[0] == 0,
                    "UNIX diagnostic kernel error")
        else:
            require(kind == 20 and len(payload) >= 16 and payload[0] == socket.AF_UNIX,
                    "Unexpected UNIX diagnostic record")
            family, sock_type, state, pad, inode, cookie0, cookie1 = struct.unpack_from("=BBBBIII", payload)
            row = {"inode": inode, "type": sock_type, "state": state, "peer": None,
                   "pending_connection_inodes": [], "receive_queue": None}
            attr = 16
            while attr < len(payload):
                require(len(payload) - attr >= 4, "Truncated UNIX diagnostic attribute")
                length, tag = struct.unpack_from("=HH", payload, attr)
                require(4 <= length <= len(payload) - attr, "Invalid UNIX diagnostic attribute")
                data = payload[attr + 4:attr + length]
                if tag == 2:
                    require(len(data) == 4 and row["peer"] is None, "Invalid duplicate UNIX peer")
                    row["peer"] = struct.unpack("=I", data)[0]
                elif tag == 3:
                    require(len(data) % 4 == 0, "Invalid UNIX pending-connection identities")
                    row["pending_connection_inodes"] = list(struct.unpack("=" + "I" * (len(data) // 4), data))
                elif tag == 4:
                    require(len(data) == 8, "Invalid UNIX queue metadata")
                    row["receive_queue"], row["send_queue"] = struct.unpack("=II", data)
                attr += (length + 3) & ~3
            rows.append(row)
        offset += (size + 3) & ~3
    return rows, done


def unix_graph():
    sequence = 1
    request = struct.pack("=BBHIIIII", socket.AF_UNIX, 0, 0, 0xffffffff, 0, 4 | 8 | 16, 0xffffffff, 0xffffffff)
    with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW | socket.SOCK_CLOEXEC, 4) as channel:
        channel.settimeout(2)
        channel.bind((0, 0))
        header = struct.pack("=IHHII", 16 + len(request), 20, 0x301, sequence, channel.getsockname()[0])
        channel.sendto(header + request, (0, 0))
        rows, total = {}, 0
        until = time.monotonic() + 5
        while True:
            require(time.monotonic() < until, "UNIX diagnostic census exceeded deadline")
            raw, ancillary, flags, address = channel.recvmsg(1024 * 1024)
            require(address[0] == 0 and not flags & socket.MSG_TRUNC,
                    "UNIX diagnostic census truncated or foreign")
            total += len(raw); require(total <= MAX_READ, "UNIX socket census exceeds bound")
            batch, done = decode_unix_diag(raw, sequence)
            for row in batch:
                require(row["inode"] not in rows, "Duplicate UNIX socket diagnostic identity")
                rows[row["inode"]] = row
            if done:
                return rows


def scoped_unix_graph(actors, graph):
    expected = {fd["inode"] for actor in actors for fd in actor["fds"] if stat.S_ISSOCK(fd["mode"])}
    selected = set(expected)
    while True:
        added = set()
        for inode, row in graph.items():
            neighbours = set(row["pending_connection_inodes"])
            if row["peer"]:
                neighbours.add(row["peer"])
            if inode in selected or neighbours.intersection(selected):
                added.add(inode); added.update(neighbours)
        added -= selected
        if not added:
            break
        selected.update(added)
    control = {fd["inode"] for actor in actors if (actor.get("pid"), actor.get("start")) == (2318474, "65818157")
               for fd in actor["fds"] if fd["fd"] == 19 and fd["inode"] in graph
               and graph[fd["inode"]]["type"] == socket.SOCK_SEQPACKET}
    return {"socket_inodes": sorted(selected), "missing_socket_inodes": sorted(selected - graph.keys()),
            "source_identified_lease_control_socket_inodes": sorted(control),
            "shared_datagram_peers_are_not_exclusive_owners": True,
            "missing_UNIX_rows_may_be_other_socket_families": True,
            "rows": [graph[inode] for inode in sorted(selected) if inode in graph],
            "same_network_namespace": all(actor["namespaces"].get("net") == os.readlink("/proc/self/ns/net")
                                          for actor in actors)}


def plan():
    rows, expected = process_table(), dict(ACTORS)
    mismatched = [pid for pid, birth in ACTORS if pid in rows and rows[pid]["start"] != birth]
    require(not mismatched, "Original PID reused; cannot build cancellation scope: " + str(mismatched))
    family = {pid for pid, birth in ACTORS if pid in rows and rows[pid]["start"] == birth}
    while True:
        added = {pid for pid, row in rows.items() if row["parent"] in family} - family
        if not added:
            break
        family.update(added)
    require(os.getpid() not in family and os.getppid() not in family,
            "Cleanup runtime is inside the cancellation scope")
    actors = [pin_process(rows[pid]) for pid in sorted(family)]
    return {"schema": "mckernel-old-owner-cancellation-plan-v1", "root_thread_id": ROOT_THREAD,
            "origin_invocation": ORIGIN, "credit_run": CREDIT_RUN,
            "boot_id": read("/proc/sys/kernel/random/boot_id", 128).decode().strip(),
            "observed_monotonic_ns": time.monotonic_ns(),
            "observer": {"pid": os.getpid(), "process": process(os.getpid()),
                         "namespaces": {p.name: os.readlink(p) for p in Path("/proc/self/ns").iterdir()},
                         "proc_root_identity": identity(Path("/proc").stat()),
                         "host_root_identity": identity(Path("/").stat()),
                         "pid1_namespaces": {p.name: os.readlink(p) for p in Path("/proc/1/ns").iterdir()}},
            "actors": actors, "unix_channels": scoped_unix_graph(actors, unix_graph()),
            "historical_actors_absent": [{"pid": pid, "start": birth} for pid, birth in ACTORS if pid not in rows],
            "observation_scope": "CURRENT_KNOWN_ACTORS_AND_CURRENT_PPID_DESCENDANTS_ONLY",
            "limitations": ["leader_FD_tables_only_in_preflight",
                            "historical_escaped_family_members_require_original_source_custody_Q",
                            "socket_graph_seeds_current_actor_FDs_not_all_historical_transfers",
                            "queued_SCM_RIGHTS_or_namespace_persistence_not_proven_closed"],
            "operation_result": "UNKNOWN", "release_authorized": False,
            "native_allocation_or_cleanup": False}


class Journal:
    def __init__(self, path):
        target = Path(path)
        require(target.is_absolute() and ".." not in target.parts
                and not any(part.is_symlink() for part in (target.parent, *target.parent.parents)),
                "Fresh absolute nonsymlink cancellation journal required")
        parent = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        self.fd = None
        try:
            self.fd = os.open(target.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                              0o600, dir_fd=parent)
            os.fsync(parent)  # The checkpoint name must survive before any signal.
        except BaseException:
            if self.fd is not None:
                os.close(self.fd); self.fd = None
            raise
        finally:
            os.close(parent)
        self.previous = None

    def append(self, state, **data):
        event = dict(data, state=state, previous_sha256=self.previous,
                     observed_monotonic_ns=time.monotonic_ns(), observed_utc_ns=time.time_ns(), operation_result="UNKNOWN",
                     historical_direct_wait_reconstructed=False, release_authorized=False)
        raw = canonical(event) + b"\n"
        offset = 0
        while offset < len(raw):
            count = os.write(self.fd, raw[offset:])
            require(count > 0, "Short cancellation checkpoint write")
            offset += count
        os.fsync(self.fd)
        self.previous = sha(raw)

    def close(self):
        os.close(self.fd)


def same_actor(expected):
    actual = pin_process(expected)
    keys = ("pid", "start", "uids", "exe", "exe_identity", "cmdline_sha256", "namespaces", "cgroup",
            "process_root_link", "process_root_identity")
    require(all(actual[key] == expected[key] for key in keys), "Exact actor identity changed")


def pidfd_terminal(fd):
    poller = select.poll(); poller.register(fd, select.POLLIN | select.POLLHUP | select.POLLERR)
    events = poller.poll(0)
    require(all(handle == fd and not mask & (select.POLLERR | select.POLLNVAL) for handle, mask in events),
            "Ambiguous/error pidfd readiness is not terminal evidence")
    return any(mask & (select.POLLIN | select.POLLHUP) for handle, mask in events)


def cancel(scope, review, journal, *, kill_after_term=False):
    require(review == {"schema": "mckernel-old-owner-cancellation-review-v1",
        "decision": "GO_EXACT_CANCELLATION_ONLY", "plan_sha256": sha(canonical(scope)),
        "helper_sha256": sha(Path(__file__).read_bytes()), "root_thread_id": ROOT_THREAD,
        "allow_sigkill": kill_after_term, "no_resource_release": True},
        "Independent exact plan/source cancellation review required")
    require(scope["schema"] == "mckernel-old-owner-cancellation-plan-v1"
            and scope["origin_invocation"] == ORIGIN and scope["root_thread_id"] == ROOT_THREAD
            and scope["credit_run"] == CREDIT_RUN
            and scope["boot_id"] == read("/proc/sys/kernel/random/boot_id", 128).decode().strip(),
            "Cancellation plan owner/boot differs")
    # A saved plan is an identity constraint, never an execution admission.
    # Fresh actual Root admission remains external. Revalidate every actor and
    # complete current descendant cut below; never rewrite an old observation's
    # timestamp merely to make independent review fit a short freshness window.
    require(type(scope["observed_monotonic_ns"]) is int and scope["observed_monotonic_ns"] > 0
            and scope["observed_monotonic_ns"] <= time.monotonic_ns(), "Cancellation identity plan is from the future")
    handles = []
    try:
        for row in scope["actors"]:
            same_actor(row)
            fd = pidfd_compat.open_pidfd(row["pid"])
            handles.append((row, fd))
            same_actor(row)
        # All live descendants must be included before any mutation.
        rows = process_table()
        family = {row["pid"] for row, fd in handles}
        require(not any(row["parent"] in family and pid not in family for pid, row in rows.items()),
                "Owning family changed; make and review a fresh plan")
        journal.append("CANCELLATION_REQUESTED", plan_sha256=sha(canonical(scope)),
                       identities=[{"pid": row["pid"], "start": row["start"]} for row, fd in handles])
        for signum, seconds in ((signal.SIGTERM, 5), (signal.SIGKILL, 10)):
            if signum == signal.SIGKILL and not kill_after_term:
                break
            for row, fd in handles:
                if pidfd_terminal(fd):
                    continue
                journal.append("BEFORE_SIGNAL", pid=row["pid"], start=row["start"], signal=int(signum))
                try:
                    pidfd_compat.send_signal(fd, signum)
                    journal.append("SIGNAL_RETURNED", pid=row["pid"], start=row["start"], signal=int(signum))
                except ProcessLookupError:
                    journal.append("SIGNAL_TARGET_ALREADY_TERMINAL", pid=row["pid"], start=row["start"])
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                polls = []
                for row, fd in handles:
                    polls.append(pidfd_terminal(fd))
                if all(polls):
                    journal.append("ALL_PINNED_PIDFDS_TERMINAL_RESOURCE_PROOF_PENDING")
                    return "ALL_PINNED_PIDFDS_TERMINAL_RESOURCE_PROOF_PENDING"
                time.sleep(0.05)
        journal.append("CANCELLATION_BOUNDED_CHECKPOINT_UNRESOLVED")
        return "CANCELLATION_BOUNDED_CHECKPOINT_UNRESOLVED"
    except BaseException as error:
        journal.append("CANCELLATION_UNKNOWN_RETAINED", error_type=type(error).__name__)
        raise
    finally:
        for row, fd in handles:
            os.close(fd)


def verify(scope):
    """Two complete privileged thread-FD sweeps; a bounded Q input, no release.

    All inaccessible/changing namespaces or metadata refuse. UNIX socket tables
    must additionally be checked by Q: queued SCM_RIGHTS may retain lease FDs
    with no process FD holder. This helper cannot equate zero holders to closure.
    """
    interesting = {(row["device"], row["inode"]) for actor in scope["actors"] for row in actor["fds"]
                   if stat.S_ISREG(row["mode"]) or stat.S_ISSOCK(row["mode"]) or stat.S_ISFIFO(row["mode"])}
    passes = []
    for sweep in range(2):
        hits, namespaces, unix_tables, tasks, errors = [], {}, {}, [], []
        for pid, row in process_table().items():
            root = Path("/proc") / str(pid)
            try:
                for task in (root / "task").iterdir():
                    tasks.append(int(task.name)); require(len(tasks) <= MAX_TASKS, "Task census exceeds bound")
                    ns = {entry.name: os.readlink(entry) for entry in (task / "ns").iterdir()}
                    namespaces[int(task.name)] = ns
                    for fd in fd_snapshot(task):
                        if (fd["device"], fd["inode"]) in interesting:
                            hits.append(dict(fd, pid=pid, tid=int(task.name), start=row["start"]))
                        if fd["link"].startswith("anon_inode:") and "io_uring" in fd["link"]:
                            errors.append("uninspectable_registered_file_custody")
                    net = ns.get("net")
                    if net not in unix_tables:
                        unix_tables[net] = read(task / "net/unix").decode()
                require(process(pid)["start"] == row["start"], "Process changed during FD census")
            except (OSError, ValueError) as error:
                errors.append({"pid": pid, "error_type": type(error).__name__})
        survivors = []
        for actor in scope["actors"]:
            try:
                actual = process(actor["pid"])
                if actual["start"] == actor["start"] and actual["state"] not in {"Z", "X", "x"}:
                    survivors.append(actual)
            except (FileNotFoundError, ProcessLookupError):
                pass
        passes.append({"sweep": sweep, "holders": hits, "surviving_actors": survivors,
                       "namespaces": namespaces, "unix_tables": unix_tables,
                       "task_count": len(tasks), "errors": errors})
    return {"schema": "mckernel-old-owner-resource-observations-v1", "plan_sha256": sha(canonical(scope)),
            "sweeps": passes, "operation_result": "UNKNOWN", "release_authorized": False,
            "Q_must_verify": ["complete_original_family_and_all_lease_transfers", "all_UNIX_channel_endpoints_and_queued_SCM_RIGHTS_gone",
                              "all_namespace_and_bind_mount_persistence", "cgroup_container_scope_or_source_proven_inapplicability",
                              "exact_HOST_resource_free_readback"],
            "native_cleanup_or_acceptance": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope")
    parser.add_argument("--scope-sha256")
    parser.add_argument("--review")
    parser.add_argument("--review-sha256")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-sigkill", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--journal")
    args = parser.parse_args(argv)
    require(os.geteuid() == 0, "Complete ownership metadata requires privileged Root executor")
    require(os.readlink("/proc/self/ns/pid") == os.readlink("/proc/1/ns/pid"), "Host PID namespace required")
    if not args.apply and not args.verify:
        print(json.dumps(plan(), sort_keys=True, indent=2)); return
    require(bool(args.scope and args.scope_sha256), "Exact reviewed plan reference required")
    raw = read(args.scope); require(sha(canonical(json.loads(raw))) == args.scope_sha256, "Plan digest differs")
    scope = json.loads(raw)
    if args.apply:
        require(not args.verify and bool(args.review and args.review_sha256 and args.journal),
                "Apply requires exact review and fresh append-only cancellation journal")
        raw = read(args.review); require(sha(raw) == args.review_sha256, "Review bytes differ")
        journal = Journal(args.journal)
        try:
            status = cancel(scope, json.loads(raw), journal, kill_after_term=args.allow_sigkill)
        finally:
            journal.close()
        print(json.dumps({"status": status, "journal": args.journal,
                          "journal_sha256": sha(read(args.journal)), "operation_result": "UNKNOWN",
                          "historical_direct_wait_reconstructed": False, "release_authorized": False}, sort_keys=True))
    else:
        print(json.dumps(verify(scope), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
