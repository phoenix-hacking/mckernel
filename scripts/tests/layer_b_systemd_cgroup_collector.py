"""Pure validation of caller-collected, non-following cgroup observations.

No I/O is performed here. A trusted caller must supply complete readdir/lstat
records and before/after mountinfo under the execution packet's deadline. The
accepted baseline is created once while the pre-command is alive, never from
terminal state. Empty ControlGroup is retained literally, not used as a path.
"""
from __future__ import annotations

from dataclasses import dataclass
import posixpath

from layer_b_systemd_cgroup_observer import (
    CgroupObserverError, Mapping, _check_observation_mounts, _filesystem_path,
    _path, _text, _under, parent_paths, parse_mountinfo,
)


@dataclass(frozen=True)
class Entry:
    """One lstat identity; directory children are complete raw basename bytes.

    Only ordinary directories and regular cgroup control files are admissible.
    procs is the complete read of a cgroup.procs file, including an empty read.
    Parent records also carry complete listings (needed to prove target absence).
    """
    raw_path: bytes
    device: int
    inode: int
    kind: str
    children: tuple[bytes, ...] = ()
    procs: bytes | None = None


@dataclass(frozen=True)
class AcceptedObservation:
    mapping: Mapping
    mount_records: tuple[bytes, ...]
    entries: tuple[Entry, ...]
    parents: tuple[Entry, ...]
    pre_command_member_pids: tuple[int, ...]


@dataclass(frozen=True)
class RecursiveObservation:
    accepted: AcceptedObservation
    entries: tuple[Entry, ...]
    parents: tuple[Entry, ...]
    terminal_control_group: bytes
    target_absent: bool
    member_pids: tuple[int, ...]

    @property
    def mapping(self) -> Mapping:
        return self.accepted.mapping

    @property
    def raw_paths(self) -> tuple[bytes, ...]:
        return tuple(entry.raw_path for entry in self.entries)


def _raw(value: bytes | str) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8", "surrogateescape")


def _identity(entry: Entry) -> tuple[int, int, str]:
    return entry.device, entry.inode, entry.kind


def _index(entries: tuple[Entry, ...]) -> dict[str, Entry]:
    if not isinstance(entries, tuple):
        raise CgroupObserverError("observations must be immutable tuples")
    result: dict[str, Entry] = {}
    identities = set()
    for entry in entries:
        if not isinstance(entry, Entry) or not isinstance(entry.raw_path, bytes):
            raise CgroupObserverError("entry requires raw pathname bytes")
        path = _path(_text(entry.raw_path))
        if (type(entry.device) is not int or type(entry.inode) is not int
                or entry.device < 0 or entry.inode <= 0
                or entry.kind not in ("directory", "file")):
            raise CgroupObserverError("invalid entry identity or type")
        identity = (entry.device, entry.inode)
        if path in result or identity in identities:
            raise CgroupObserverError("duplicate pathname or aliased identity")
        identities.add(identity)
        if not isinstance(entry.children, tuple):
            raise CgroupObserverError("listing must be an immutable tuple")
        names = set()
        for child in entry.children:
            if (not isinstance(child, bytes) or not child or child in (b".", b"..")
                    or b"/" in child or b"\x00" in child or child in names):
                raise CgroupObserverError("invalid or duplicate directory child")
            names.add(child)
        if entry.kind == "file" and entry.children:
            raise CgroupObserverError("file cannot have children")
        is_procs = entry.kind == "file" and posixpath.basename(path) == "cgroup.procs"
        if is_procs != isinstance(entry.procs, bytes) or (not is_procs and entry.procs is not None):
            raise CgroupObserverError("missing or misplaced cgroup.procs bytes")
        result[path] = entry
    return result


def _mount_records(mountinfo: bytes | str, mapping: Mapping,
                   paths: tuple[str, ...]) -> tuple[bytes, ...]:
    if not isinstance(mapping, Mapping):
        raise CgroupObserverError("collector requires immutable Mapping")
    if _filesystem_path(mapping.mount_root, mapping.mountpoint,
                        mapping.original_control_group) != mapping.filesystem_path:
        raise CgroupObserverError("inconsistent original mapping")
    mounts = parse_mountinfo(mountinfo)
    selected = [m for m in mounts if m.fstype == "cgroup" and "name=systemd" in m.super_options]
    if len(selected) != 1:
        raise CgroupObserverError("missing or ambiguous systemd controller")
    mount = selected[0]
    if (mount.mount_id != mapping.mount_id or mount.root != mapping.mount_root
            or mount.mountpoint != mapping.mountpoint):
        raise CgroupObserverError("mapping mount identity changed")
    _check_observation_mounts(mounts, mount, parent_paths(mapping) + paths)
    by_id = {m.mount_id: m for m in mounts}
    retained = {mount.mount_id}
    parent = mount.parent_id
    while parent in by_id:
        if parent in retained:
            raise CgroupObserverError("cyclic mount topology")
        retained.add(parent)
        parent = by_id[parent].parent_id
    # Retain complete raw records, including device, source, options and optional
    # fields absent from the resolver's deliberately smaller Mount structure.
    result = []
    for line in _raw(mountinfo).split(b"\n"):
        if not line:
            continue
        try:
            mount_id = int(line.split(b" ", 1)[0])
        except (ValueError, IndexError) as exc:
            raise CgroupObserverError("malformed retained mount record") from exc
        if mount_id in retained:
            result.append(line)
    if len(result) != len(retained):
        raise CgroupObserverError("incomplete retained mount records")
    return tuple(result)


def _walk(mapping: Mapping, entries: tuple[Entry, ...], parents: tuple[Entry, ...],
          *, allow_absent: bool) -> tuple[bool, tuple[int, ...]]:
    nodes, ancestors = _index(entries), _index(parents)
    # Combined indexing forbids aliases between tree entries and parent records.
    _index(entries + parents)
    target = mapping.filesystem_path
    expected_parents = parent_paths(mapping)[1:]
    if not expected_parents or set(ancestors) != set(expected_parents):
        raise CgroupObserverError("missing or extraneous original parent identities")
    for path in expected_parents:
        if ancestors[path].kind != "directory":
            raise CgroupObserverError("parent is not a directory")
    # Verify every edge, including target -> its immediate parent.  The
    # nearest parent is an independently lstat'ed record, not inferred from
    # pathname text.
    chain = (target,) + expected_parents
    # If the target is absent, its missing edge is the evidence being checked
    # below; all retained ancestor-to-ancestor edges must still be present.
    edge_chain = chain if target in nodes else chain[1:]
    for child, parent in zip(edge_chain, edge_chain[1:]):
        if _raw(posixpath.basename(child)) not in ancestors[parent].children:
            raise CgroupObserverError("parent chain missing from listing")
    listed = _raw(posixpath.basename(target)) in ancestors[expected_parents[0]].children
    if target not in nodes:
        if not allow_absent or nodes or listed:
            raise CgroupObserverError("original target omitted without verified absence")
        return True, ()
    if not listed or nodes[target].kind != "directory":
        raise CgroupObserverError("original target is not the listed directory")
    pids: list[int] = []
    for path, entry in nodes.items():
        if _under(target, path) is None:
            raise CgroupObserverError("observed path is outside original target")
        if path != target:
            parent = nodes.get(posixpath.dirname(path))
            if (parent is None or parent.kind != "directory"
                    or _raw(posixpath.basename(path)) not in parent.children):
                raise CgroupObserverError("entry lacks its listed directory parent")
        if entry.kind == "directory":
            if b"cgroup.procs" not in entry.children:
                raise CgroupObserverError("directory lacks cgroup.procs")
            for name in entry.children:
                child = nodes.get(posixpath.join(path, _text(name)))
                if child is None:
                    raise CgroupObserverError("incomplete recursive directory listing")
                if name == b"cgroup.procs" and child.kind != "file":
                    raise CgroupObserverError("cgroup.procs is not a regular file")
        if entry.procs is not None:
            rows = entry.procs.splitlines()
            for row in rows:
                if not row or any(c < 48 or c > 57 for c in row) or int(row) <= 0:
                    raise CgroupObserverError("malformed cgroup.procs")
                pids.append(int(row))
    if len(set(pids)) != len(pids):
        raise CgroupObserverError("PID repeated across recursive membership")
    return False, tuple(pids)


def accept_observation(mountinfo: bytes | str, mapping: Mapping,
                       entries: tuple[Entry, ...], parents: tuple[Entry, ...]) -> AcceptedObservation:
    """Freeze the complete original tree while live pre-command evidence exists."""
    _, pids = _walk(mapping, entries, parents, allow_absent=False)
    records = _mount_records(
        mountinfo, mapping,
        tuple(_text(e.raw_path) for e in entries + parents))
    return AcceptedObservation(mapping, records, entries, parents, pids)


def collect_recursive_observation(
    mountinfo: bytes | str, accepted: AcceptedObservation,
    entries: tuple[Entry, ...], parents: tuple[Entry, ...],
    terminal_control_group: bytes | str, *, require_retired: bool = True,
) -> RecursiveObservation:
    """Reconcile the original tree; omission or substitution is never retirement.

    require_retired=False is for live pre/post-ack revalidation, not cleanup.
    A caller cannot use such a result to satisfy the terminal retirement check.
    """
    if not isinstance(accepted, AcceptedObservation):
        raise CgroupObserverError("collector requires accepted immutable baseline")
    mapping = accepted.mapping
    if not isinstance(terminal_control_group, (bytes, str)):
        raise CgroupObserverError("actual ControlGroup property is required")
    terminal = _raw(terminal_control_group)
    if terminal and _path(_text(terminal)) != mapping.original_control_group:
        raise CgroupObserverError("terminal ControlGroup replaced original mapping")
    if not require_retired and not terminal:
        raise CgroupObserverError("live observation requires original ControlGroup")
    absent, pids = _walk(mapping, entries, parents, allow_absent=require_retired)
    records = _mount_records(
        mountinfo, mapping,
        tuple(_text(e.raw_path) for e in entries + parents))
    if records != accepted.mount_records:
        raise CgroupObserverError("retained mount ancestry or controller identity changed")
    originals = _index(accepted.entries + accepted.parents)
    current = _index(entries + parents)
    original_ids = {_identity(e): path for path, e in originals.items()}
    for path, entry in current.items():
        if path in originals and _identity(entry) != _identity(originals[path]):
            raise CgroupObserverError("original filesystem identity replaced")
        if _identity(entry) in original_ids and original_ids[_identity(entry)] != path:
            raise CgroupObserverError("original filesystem identity aliased or moved")
    if require_retired and pids:
        raise CgroupObserverError("original recursive cgroup still has members")
    return RecursiveObservation(accepted, entries, parents, terminal, absent, pids)


collect_cgroup_observation = collect_recursive_observation
