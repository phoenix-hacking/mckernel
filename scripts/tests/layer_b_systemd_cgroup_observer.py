"""Pure, conservative observer for a v1 systemd cgroup hierarchy.

This module only parses supplied bytes and constructs paths; it never reads
procfs, invokes systemd, or mutates a cgroup.
"""
from __future__ import annotations

from dataclasses import dataclass
import posixpath
from typing import Any


class CgroupObserverError(ValueError):
    pass


def _text(data: bytes | str) -> str:
    # Linux pathnames need not be UTF-8. Surrogate escapes retain each original
    # byte and round-trip through filesystem APIs without changing identity.
    return data.decode("utf-8", "surrogateescape") if isinstance(data, bytes) else data


def _unescape(field: str) -> str:
    # mountinfo uses octal escapes, and no other escapes are accepted.
    out, i = [], 0
    while i < len(field):
        if field[i] == "\\":
            if i + 3 >= len(field) or any(c not in "01234567" for c in field[i + 1:i + 4]):
                raise CgroupObserverError("malformed mountinfo escape")
            out.append(chr(int(field[i + 1:i + 4], 8)))
            i += 4
        else:
            out.append(field[i]); i += 1
    return "".join(out)


def _path(value: str, *, allow_root: bool = True) -> str:
    if not value or not value.startswith("/") or "\x00" in value:
        raise CgroupObserverError("cgroup path is not absolute")
    bits = value.split("/")
    if any(bit in (".", "..") for bit in bits):
        raise CgroupObserverError("cgroup traversal")
    if not allow_root and value == "/":
        raise CgroupObserverError("empty cgroup path")
    # Repeated separators do not identify a distinct hierarchy and are rejected
    # to keep the retained identity byte-for-byte canonical.
    if "//" in value or (value != "/" and value.endswith("/")):
        raise CgroupObserverError("non-canonical cgroup path")
    return value


@dataclass(frozen=True)
class Mount:
    mount_id: int
    parent_id: int
    root: str
    mountpoint: str
    options: tuple[str, ...]
    fstype: str
    super_options: tuple[str, ...]


@dataclass(frozen=True)
class Mapping:
    mount_id: int
    mount_root: str
    mountpoint: str
    hierarchy_path: str
    original_control_group: str
    filesystem_path: str

    def to_dict(self) -> dict[str, Any]:
        return {"mount_id": self.mount_id, "mount_root": self.mount_root,
                "mountpoint": self.mountpoint, "hierarchy_path": self.hierarchy_path,
                "original_control_group": self.original_control_group,
                "filesystem_path": self.filesystem_path}


def parse_mountinfo(data: bytes | str) -> list[Mount]:
    mounts = []
    for raw in _text(data).split("\n"):
        if not raw:
            continue
        fields = raw.split(" - ", 1)
        if len(fields) != 2:
            raise CgroupObserverError("malformed mountinfo separator")
        left, right = fields
        a, b = left.split(" "), right.split(" ")
        if len(a) < 6 or len(b) < 3 or "" in a or "" in b:
            raise CgroupObserverError("malformed mountinfo record")
        try: mount_id, parent_id = int(a[0]), int(a[1])
        except ValueError as exc: raise CgroupObserverError("bad mount id") from exc
        if mount_id <= 0 or parent_id < 0 or any(m.mount_id == mount_id for m in mounts):
            raise CgroupObserverError("invalid or duplicate mount id")
        # Non-cgroup mount roots are opaque (nsfs commonly uses mnt:[N])
        # and must not be subjected to cgroup pathname grammar.
        fstype = b[0]
        root_raw, point = _unescape(a[3]), _path(_unescape(a[4]))
        if fstype in ("cgroup", "cgroup2"):
            root = _path(root_raw)
        else:
            root = root_raw
        mounts.append(Mount(mount_id, parent_id, root, point, tuple(a[5].split(",")),
                            fstype, tuple(b[2].split(","))))
    return mounts


def parse_cgroup(data: bytes | str) -> list[tuple[str, str, str]]:
    result = []
    for line in _text(data).split("\n"):
        # Do not strip: pathname bytes, including spaces, are identity.  Only
        # the first two separators delimit the cgroup record.
        if line == "":
            continue
        first, sep, rest = line.partition(":")
        second, sep2, path = rest.partition(":") if sep else ("", "", "")
        if not sep or not sep2 or not first.isdigit() or not path.startswith("/"):
            raise CgroupObserverError("malformed proc cgroup record")
        path = _path(path)
        result.append((first, second, path))
    return result


def _under(root: str, value: str) -> str | None:
    """Return value relative to root, enforcing component containment."""
    if root == "/":
        return value
    if value == root:
        return "/"
    if value.startswith(root + "/"):
        return value[len(root):]
    return None


def _shared_nonroot_parent(left: str, right: str) -> bool:
    a, b = left.strip("/").split("/"), right.strip("/").split("/")
    common = 0
    for x, y in zip(a, b):
        if x != y:
            break
        common += 1
    return common > 0


def _filesystem_path(root: str, mountpoint: str, hierarchy_path: str) -> str:
    relative = _under(_path(root), _path(hierarchy_path))
    if relative is None:
        raise CgroupObserverError("cgroup path is outside selected mount root")
    point = _path(mountpoint)
    return point if relative == "/" else posixpath.join(point, relative[1:])


def _check_observation_mounts(mounts: list[Mount], selected: Mount,
                              paths: tuple[str, ...]) -> None:
    # A normal ancestor mount (e.g. / or the tmpfs at /sys/fs/cgroup) contains
    # the selected mount in its parent-ID chain. A later overmount at that same
    # pathname is not in that chain. Path prefixes alone cannot distinguish them.
    by_id = {m.mount_id: m for m in mounts}
    ancestors: set[int] = set()
    seen = {selected.mount_id}
    parent = selected.parent_id
    while parent in by_id:
        if parent in seen:
            raise CgroupObserverError("cyclic mount topology")
        seen.add(parent)
        ancestor = by_id[parent]
        if (_under(ancestor.mountpoint, selected.mountpoint) is None
                or ancestor.mountpoint == selected.mountpoint):
            raise CgroupObserverError("selected systemd mount is stacked or topology is invalid")
        ancestors.add(parent)
        parent = ancestor.parent_id
    # A missing parent is normal when it lies outside this namespace's root.
    for mount in mounts:
        if mount.mount_id == selected.mount_id or mount.mount_id in ancestors:
            continue
        if any(_under(mount.mountpoint, path) is not None for path in paths):
            raise CgroupObserverError("systemd observation path is stacked or covered")


def resolve_systemd_mapping(mountinfo: bytes | str, self_cgroup: bytes | str,
                            control_group: str) -> Mapping:
    control = _path(control_group)
    mounts = parse_mountinfo(mountinfo)
    candidates = [m for m in mounts
                  if m.fstype == "cgroup" and "name=systemd" in m.super_options]
    if len(candidates) != 1:
        raise CgroupObserverError("missing or ambiguous systemd mount")
    mount = candidates[0]
    named = [(controllers, path) for _, controllers, path in parse_cgroup(self_cgroup)
             if "name=systemd" in controllers.split(",")]
    if len(named) != 1:
        raise CgroupObserverError("missing or ambiguous systemd cgroup mapping")
    _, hierarchy = named[0]
    # ControlGroup and proc cgroup are hierarchy-relative.  A non-/ mount root
    # is an offset into that hierarchy. Both supplied paths must contain it.
    root = mount.root
    hierarchy_relative = _under(root, hierarchy)
    control_relative = _under(root, control)
    if hierarchy_relative is None or control_relative is None:
        raise CgroupObserverError("cgroup path is outside selected mount root")
    # The observer may be an external sibling.  It must still be in the same
    # systemd subtree; ControlPID membership is checked independently.
    if (hierarchy != control and not hierarchy.startswith(control.rstrip("/") + "/")
            and not control.startswith(hierarchy.rstrip("/") + "/")
            and not _shared_nonroot_parent(hierarchy, control)):
        raise CgroupObserverError("ControlGroup does not match systemd hierarchy")
    fs = _filesystem_path(root, mount.mountpoint, control)
    mapping = Mapping(mount.mount_id, root, mount.mountpoint, hierarchy, control, fs)
    _check_observation_mounts(mounts, mount, parent_paths(mapping))
    return mapping


def verify_pid_membership(pid_cgroup: bytes | str, mapping: Mapping) -> bool:
    try:
        rows = [(controllers, path) for _, controllers, path in parse_cgroup(pid_cgroup)
                if "name=systemd" in controllers.split(",")]
    except CgroupObserverError:
        return False
    if len(rows) != 1:
        return False
    path = rows[0][1]
    return path == mapping.original_control_group or path.startswith(mapping.original_control_group.rstrip("/") + "/")


def parent_paths(mapping: Mapping) -> tuple[str, ...]:
    """Filesystem parents up to (and including) this mountpoint only."""
    value = mapping.original_control_group
    paths = []
    while True:
        paths.append(_filesystem_path(mapping.mount_root, mapping.mountpoint, value))
        if value == mapping.mount_root:
            return tuple(paths)
        value = posixpath.dirname(value)


# Explicit aliases make the small API convenient to callers without adding I/O.
derive_systemd_mapping = resolve_systemd_mapping
map_cgroup_path = resolve_systemd_mapping
