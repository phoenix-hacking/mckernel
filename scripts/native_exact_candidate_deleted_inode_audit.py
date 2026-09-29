#!/usr/bin/env python3
"""Current-state, read-only deleted-inode reference audit.

This is deliberately independent of the consumed retirement observer.  It only
reads the retained archive/inventory and procfs; it never mutates a target,
interprets retirement state, or removes a path.
"""
from __future__ import print_function

import argparse
import errno
from enum import Enum
import hashlib
import json
import os
import re
import stat
import sys
import tarfile
import time

ARCHIVE_SHA = "16cafe645dfe2ca70eccddfb5d1f3127797643d4a66f24a9f1b2902020625af2"
OBSERVER_SHA = "780edb7fae406840433cd3094b9fb7cce9a009cc17acbacad63fc5e5f1a90121"
INVENTORY_SHA = "4067c653e4767e63d99f8cc396587e1121dba601ea4f51f1020168cd4c61b8e1"
IDENTITY_SHA = "3ee0942c4e5f1934220c8dafed3c4664ae47d05cb30ed4679ec0fe6cadd0a1e8"
BOOT_RE = re.compile(r"^[0-9a-fA-F-]{36}$")
PROC_RE = re.compile(r"^[0-9]+$")


class AuditError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                return h.hexdigest()
            h.update(b)


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _archive_observer(archive):
    if sha256_file(archive) != ARCHIVE_SHA:
        raise AuditError("archive sha256 mismatch")
    with tarfile.open(archive, "r:gz") as tf:
        members = [m for m in tf.getmembers() if m.name.endswith("observer.stdout")]
        if len(members) != 1:
            raise AuditError("archive must contain exactly one observer.stdout")
        raw = tf.extractfile(members[0]).read()
    if hashlib.sha256(raw).hexdigest() != OBSERVER_SHA:
        raise AuditError("observer.stdout sha256 mismatch")
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise AuditError("observer.stdout is not JSON: %s" % e)
    return value


def load_baseline(archive, inventory_path):
    if sha256_file(inventory_path) != INVENTORY_SHA:
        raise AuditError("inventory sha256 mismatch")
    with open(inventory_path, "r") as f:
        inventory = json.load(f)
    observed = _archive_observer(archive)
    if observed.get("boot_id") and not BOOT_RE.match(observed["boot_id"]):
        raise AuditError("malformed baseline boot id")
    roots = observed.get("roots")
    if not isinstance(roots, list) or not roots:
        raise AuditError("baseline has no roots")
    deleted = set()
    counts = []
    for root in roots:
        members = root.get("tree_member_identities")
        if not isinstance(members, list) or root.get("tree_inode_count") != len(members):
            raise AuditError("incomplete baseline tree")
        for row in members:
            if not isinstance(row, list) or len(row) < 2 or not all(isinstance(x, int) for x in row[:2]):
                raise AuditError("malformed tree identity")
            deleted.add((int(row[0]), int(row[1])))
        counts.append(len(members))
    inv_roots = inventory.get("roots")
    if not isinstance(inv_roots, list) or len(inv_roots) != len(roots):
        raise AuditError("inventory roots do not bind baseline roots")
    inv_paths = []
    for r in inv_roots:
        ident = r.get("identity", {})
        if (ident.get("dev"), ident.get("inode")) not in deleted:
            raise AuditError("inventory root is absent from deleted set")
        inv_paths.append(r.get("path"))
    if len(deleted) != 10611 or hashlib.sha256(canonical_json(sorted(deleted)).encode()).hexdigest() != IDENTITY_SHA:
        raise AuditError("deleted identity binding mismatch")
    retained_mount_roots(observed)
    return observed, inventory, deleted, counts, inv_paths


def _base(pid, tid=None):
    return "/proc/%d" % pid if tid is None else "/proc/%d/task/%d" % (pid, tid)


def _starttime(pid, tid=None):
    with open(_base(pid, tid) + "/stat", "r") as f:
        line = f.read()
    close = line.rfind(")")
    expected = tid if tid is not None else pid
    if close < 0 or not line.startswith("%d (" % expected):
        raise ValueError("malformed stat")
    fields = line[close + 2:].split()
    if (len(fields) < 50 or fields[0] not in ("R", "S", "D", "Z", "T", "t", "X", "x", "K", "W", "P", "I")
            or any(not re.fullmatch(r"-?[0-9]+", value) for value in fields[1:])
            or not fields[19].isdigit()):
        raise ValueError("malformed starttime")
    return fields[19]


def _identity(pid, tid=None):
    return (int(pid), int(tid if tid is not None else pid), _starttime(pid, tid))


class IdentityState(Enum):
    LIVE = "live"
    EXITED = "exited"
    REUSED = "reused"
    UNCERTAIN = "uncertain"


def _identity_state(bound, task=False):
    """Only an absent proc directory proves disappearance, never a stat error.

    The caller must already have bound this identity. Errors (including an
    unreadable or malformed stat for an existing directory) remain failures.
    """
    pid, tid, _ = bound
    task_tid = tid if task else None
    try:
        current = _identity(pid, task_tid)
    except OSError as e:
        if e.errno not in (errno.ENOENT, errno.ESRCH):
            return IdentityState.UNCERTAIN
        try:
            os.stat(_base(pid, task_tid))
        except OSError as missing:
            if missing.errno == errno.ENOENT:
                return IdentityState.EXITED
        return IdentityState.UNCERTAIN
    except ValueError:
        return IdentityState.UNCERTAIN
    return IdentityState.LIVE if current == bound else IdentityState.REUSED


def _revalidate(bound, failures, reconciled, task=False):
    state = _identity_state(bound, task)
    label = "%d:%d" % bound[:2]
    if state == IdentityState.EXITED:
        if reconciled is not None:
            reconciled.append("exit:" + label)
    elif state != IdentityState.LIVE:
        failures.append("identity-%s:%s" % (state.value, label))
    return state


def _stat_target(path, deleted, failures, refs, label, reconciled=None, bound=None, task=False):
    try:
        s = os.stat(path)
    except OSError as e:
        if e.errno in (errno.ENOENT, errno.ESRCH) and bound is not None:
            state = _revalidate(bound, failures, reconciled, task)
            if state != IdentityState.EXITED:
                failures.append("unresolved-target-churn:%s" % label)
            return False
        failures.append("stat:%s:%s" % (label, e.errno))
        return False
    key = (int(s.st_dev), int(s.st_ino))
    if key in deleted:
        refs.append({"identity": [key[0], key[1]], "source": label})
    return True


def _absolute_path(value):
    return (isinstance(value, str) and value.startswith("/") and not value.startswith("//")
            and "\0" not in value and os.path.normpath(value) == value)


def retained_mount_roots(observed):
    result = []
    for root in observed["roots"]:
        dev, path = root.get("device_number"), root.get("filesystem_root")
        mount = root.get("observer_mount", {})
        if (type(dev) is not int or dev < 0 or not _absolute_path(path) or path == "/"
                or mount.get("device") != "%d:%d" % (os.major(dev), os.minor(dev))
                or not _absolute_path(mount.get("root")) or not _absolute_path(mount.get("mountpoint"))):
            raise AuditError("invalid retained mount root")
        rel = os.path.relpath(root["path"], mount["mountpoint"])
        if rel == ".." or rel.startswith("../") or os.path.normpath(os.path.join(mount["root"], rel)) != path:
            raise AuditError("retained mount root does not bind observer path")
        result.append((dev, path))
    return tuple(result)


def _mount_path(encoded):
    if re.search(r"\\(?!040|011|012|134)", encoded):
        raise ValueError("mount escape")
    value = re.sub(r"\\(040|011|012|134)", lambda m: chr(int(m.group(1), 8)), encoded)
    if not _absolute_path(value):
        raise ValueError("mount path")
    return value


def _mount_rows(data):
    if not data or not data.endswith("\n"):
        raise ValueError("empty or incomplete mountinfo")
    rows, ids = [], set()
    for line in data.splitlines():
        left, sep, right = line.partition(" - ")
        fields, tail = left.split(), right.split()
        if (not sep or len(fields) < 6 or len(tail) != 3
                or not re.fullmatch(r"[1-9][0-9]*", fields[0])
                or not re.fullmatch(r"[0-9]+", fields[1])
                or not re.fullmatch(r"[0-9]+:[0-9]+", fields[2])
                or fields[0] in ids or fields[5].split(",")[0] not in ("ro", "rw")
                or any(not x for x in fields[5].split(",") + tail[2].split(","))
                or any(not re.fullmatch(r"(?:shared|master|propagate_from):[1-9][0-9]*|unbindable", x) for x in fields[6:])):
            raise ValueError("mount row")
        ids.add(fields[0])
        major, minor = map(int, fields[2].split(":"))
        rows.append((os.makedev(major, minor), _mount_path(fields[3]), _mount_path(fields[4])))
    if not rows:
        raise ValueError("empty mountinfo")
    return rows


def _namespace(base, name):
    value = os.readlink(base + "/ns/" + name)
    if not re.fullmatch(re.escape(name) + r":\[[1-9][0-9]*\]", value):
        raise ValueError("malformed namespace")
    return value


def _scan_mountinfo(pid, failures, mount_roots=(), task_tid=None):
    base = _base(pid, task_tid)
    label = "%d:%d" % (pid, task_tid if task_tid is not None else pid)
    try:
        before = _namespace(base, "mnt")
        with open(base + "/mountinfo", "r") as f:
            rows = _mount_rows(f.read())
        after = _namespace(base, "mnt")
        if before != after:
            failures.append("mount-namespace-churn:" + label)
        for dev, root, _ in rows:
            if any(dev == target_dev and (root == target or root.startswith(target + "/")
                                         or root == target + " (deleted)")
                   for target_dev, target in mount_roots):
                failures.append("mount-alias:" + label)
    except (OSError, ValueError, OverflowError):
        failures.append("mountinfo-uninspected:" + label)


def _scan_fds(base, bound, task, deleted, failures, refs, reconciled):
    label = "%d:%d" % bound[:2]
    try:
        # Keep the enumeration descriptor alive while inspecting it when the
        # target is this observer. listdir closes it before returning its name.
        with os.scandir(base + "/fd") as entries:
            for entry in entries:
                if not re.fullmatch(r"[0-9]+", entry.name):
                    failures.append("malformed-fd-entry:" + label)
                    continue
                _stat_target(base + "/fd/" + entry.name, deleted, failures, refs,
                             label + "/fd/" + entry.name, reconciled, bound, task)
    except OSError as e:
        failures.append("fd-directory:%s:%s" % (label, e.errno))


def _scan_process(pid, deleted, failures, refs, counters, reconciled=None, mount_roots=()):
    first_error = len(failures)
    try:
        ident = _identity(pid)
    except (OSError, IOError, ValueError) as e:
        failures.append("identity:%d:%s" % (pid, getattr(e, "errno", "malformed"))); return None
    counters["processes"] += 1
    base = "/proc/%d" % pid
    for name in ("cwd", "root", "exe"):
        _stat_target(os.path.join(base, name), deleted, failures, refs, "%s/%s" % (pid, name), reconciled, ident)
    for name in ("pid", "net", "user", "uts", "ipc"):
        try:
            _namespace(base, name)
        except (OSError, ValueError):
            failures.append("namespace:%s:%s" % (pid, name))
    _scan_fds(base, ident, False, deleted, failures, refs, reconciled)
    _scan_mountinfo(pid, failures, mount_roots)
    mapdir = os.path.join(base, "map_files")
    try:
        entries = os.listdir(mapdir)
    except OSError as e:
        failures.append("map_files-directory:%d:%s" % (pid, e.errno)); entries = None
    if entries is None:
        counters["map_files_denials"] += 1
    else:
        counters["map_files_entries"] += len(entries)
        for ent in entries:
            if (not re.fullmatch(r"[0-9a-f]+-[0-9a-f]+", ent)
                    or int(ent.split("-")[0], 16) >= int(ent.split("-")[1], 16)):
                failures.append("malformed-map-entry:%d" % pid)
                continue
            _stat_target(os.path.join(mapdir, ent), deleted, failures, refs, "map_files/%s/%s" % (pid, ent), reconciled, ident)
    state = _revalidate(ident, failures, reconciled)
    return ident if state == IdentityState.LIVE and len(failures) == first_error else None


def audit_round(deleted, mount_roots=(), reconciled=None):
    failures, refs = [], []
    counters = {"processes": 0, "tasks": 0, "map_files_entries": 0, "map_files_denials": 0}
    identities = []
    try:
        pids = sorted(int(x) for x in os.listdir("/proc") if PROC_RE.match(x))
    except OSError as e:
        return identities, failures + ["proc-list:%s" % e.errno], refs, counters
    for pid in pids:
        first_error = len(failures)
        ident = _scan_process(pid, deleted, failures, refs, counters, reconciled, mount_roots)
        if ident is None:
            continue
        candidates = [(ident, False)]
        taskdir = "/proc/%d/task" % pid
        try:
            tids = sorted(int(x) for x in os.listdir(taskdir) if PROC_RE.match(x))
        except OSError as e:
            failures.append("task-directory:%d:%s" % (pid, e.errno)); continue
        for tid in tids:
            try:
                tident = _identity(pid, tid)
            except (OSError, IOError, ValueError):
                failures.append("task-identity:%d:%d" % (pid, tid)); continue
            counters["tasks"] += 1
            # Per-task descriptors and namespaces are read, but map_files is
            # intentionally process-level: task map_files is absent on Linux.
            tbase = "/proc/%d/task/%d" % (pid, tid)
            for name in ("cwd", "root", "exe"):
                _stat_target(os.path.join(tbase, name), deleted, failures, refs, "%d/%d/%s" % (pid, tid, name), reconciled, tident, True)
            _scan_fds(tbase, tident, True, deleted, failures, refs, reconciled)
            _scan_mountinfo(pid, failures, mount_roots, tid)
            if _revalidate(tident, failures, reconciled, True) == IdentityState.LIVE:
                candidates.append((tident, True))
        try:
            final_tids = sorted(int(x) for x in os.listdir(taskdir) if PROC_RE.fullmatch(x))
            expected_tids = sorted(x[0][1] for x in candidates if x[1])
            if final_tids != expected_tids:
                failures.append("task-census-churn:%d" % pid)
        except OSError:
            failures.append("task-census-uninspected:%d" % pid)
        if len(failures) == first_error and tids:
            identities.extend(candidates)
        elif not tids:
            failures.append("empty-task-census:%d" % pid)
    # Revalidate only completely scanned identities, after all process/task
    # reads. An old tuple from an unsuccessful scan cannot authenticate an anchor.
    verified = []
    live_processes = []
    for ident, task in identities:
        if _revalidate(ident, failures, reconciled, task) == IdentityState.LIVE:
            verified.append(ident)
            if not task:
                live_processes.append(ident[0])
    try:
        final_pids = sorted(int(x) for x in os.listdir("/proc") if PROC_RE.fullmatch(x))
        if final_pids != sorted(live_processes):
            failures.append("process-census-churn")
    except OSError:
        failures.append("process-census-uninspected")
    # Any failure invalidates this round's authorization set, even if the same
    # PID/starttime was also seen through a successfully scanned leader task.
    identities = [] if failures else verified
    return identities, failures, refs, counters


def _write_exclusive(path, value):
    parent = os.path.dirname(os.path.abspath(path)) or "."
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        data = (canonical_json(value) + "\n").encode("utf-8")
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError(errno.EIO, "zero-progress output write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    dfd = os.open(parent, os.O_RDONLY)
    try: os.fsync(dfd)
    finally: os.close(dfd)


def run(args):
    if os.geteuid() != 0:
        raise AuditError("live mode requires euid 0")
    observed, inventory, deleted, counts, inventory_paths = load_baseline(args.archive, args.inventory)
    mount_roots = retained_mount_roots(observed)
    boot = open("/proc/sys/kernel/random/boot_id").read().strip()
    failures = []
    if boot != observed.get("boot_id"):
        failures.append("boot-id-mismatch")
    # Both the original inventory roots and the quarantine roots must remain absent.
    for path in inventory_paths + [r.get("path") for r in observed.get("roots", [])]:
        if not path: failures.append("malformed-root-path"); continue
        try: os.lstat(path); failures.append("root-present:%s" % path)
        except OSError as e:
            if e.errno != errno.ENOENT: failures.append("root-check:%s:%s" % (path, e.errno))
    rounds = []
    anchors = []
    for spec in args.anchor:
        try:
            pid, start = spec.split(":", 1)
            if not re.fullmatch(r"[1-9][0-9]*", pid) or not re.fullmatch(r"[0-9]+", start):
                raise ValueError("invalid anchor identity")
            anchors.append((int(pid), start))
        except Exception:
            raise AuditError("malformed --anchor")
    if not anchors:
        for pid in (os.getpid(), os.getppid()):
            try: anchors.append((pid, _starttime(pid)))
            except (OSError, IOError, ValueError): raise AuditError("cannot bind self/parent anchor")
    previous = None
    for n in range(1, args.rounds + 1):
        reconciled = []
        identities, errs, refs, counters = audit_round(deleted, mount_roots, reconciled)
        now = sorted(set(identities))
        churn = [] if previous is None else sorted(set(previous).symmetric_difference(now))
        anchor_failures = ["anchor-missing:%d" % pid for pid, start in anchors if (pid, pid, start) not in now]
        if not now or counters["tasks"] == 0: anchor_failures.append("empty-or-unstable-proc-census")
        round_failures = sorted(set(errs + anchor_failures + (["unresolved-churn"] if churn else [])))
        rounds.append({"round": n, "processes": counters["processes"], "tasks": counters["tasks"],
                       "map_files_entries": counters["map_files_entries"], "map_files_denials": counters["map_files_denials"],
                       "references": sorted(refs, key=lambda x: (x["identity"], x["source"])),
                       "failures": round_failures, "identity_count": len(now),
                       "reconciled_exits": sorted(set(reconciled))})
        failures.extend(round_failures)
        failures.extend("reference:%s:%s" % (r["identity"], r["source"]) for r in refs)
        previous = now
        if n != args.rounds: time.sleep(args.delay)
    result = {"schema": "mckernel.native-exact-deleted-inode-audit.v1", "status": "PASS" if not failures else "FAIL",
              "tool": {"sha256": sha256_file(__file__)}, "baseline": {"archive_sha256": sha256_file(args.archive), "observer_sha256": OBSERVER_SHA, "inventory_sha256": sha256_file(args.inventory), "boot_id": observed.get("boot_id")},
              "target": {"identity_count": len(deleted), "root_counts": counts, "identity_sha256": hashlib.sha256(canonical_json(sorted(deleted)).encode()).hexdigest()},
              "rounds": rounds, "failures": sorted(set(failures))}
    _write_exclusive(args.output, result)
    return 0 if result["status"] == "PASS" else 1


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True)
    p.add_argument("--inventory", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--delay", type=float, default=0.1)
    p.add_argument("--anchor", action="append", default=[], metavar="PID:STARTTIME")
    a = p.parse_args(argv)
    if a.rounds != 3 or not (0 <= a.delay <= 5):
        p.error("--rounds must be 3 and --delay must be between 0 and 5 seconds")
    try: return run(a)
    except (AuditError, OSError, IOError, ValueError) as e:
        print("audit failed: %s" % e, file=sys.stderr); return 2


if __name__ == "__main__":
    sys.exit(main())
