"""Pure, conservative observer for a v1 systemd cgroup hierarchy.

This module only parses supplied bytes and constructs paths; it never reads
procfs, invokes systemd, or mutates a cgroup.
"""
from __future__ import annotations

from dataclasses import dataclass
import posixpath
import shlex
from typing import Any, Iterable


class CgroupObserverError(ValueError):
    pass


def _text(data: bytes | str) -> str:
    return data.decode("utf-8", "strict") if isinstance(data, bytes) else data


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
    if "//" in value:
        raise CgroupObserverError("non-canonical cgroup path")
    return value if value == "/" else value.rstrip("/")


@dataclass(frozen=True)
class Mount:
    mount_id: int
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
    for raw in _text(data).splitlines():
        if not raw.strip():
            continue
        fields = raw.split(" - ", 1)
        if len(fields) != 2:
            raise CgroupObserverError("malformed mountinfo separator")
        left, right = fields
        a, b = left.split(), right.split()
        if len(a) < 6 or len(b) < 3:
            raise CgroupObserverError("malformed mountinfo record")
        try: mount_id = int(a[0])
        except ValueError as exc: raise CgroupObserverError("bad mount id") from exc
        root, point = _path(_unescape(a[3])), _path(_unescape(a[4]))
        mounts.append(Mount(mount_id, root, point, tuple(a[5].split(",")),
                            b[0], tuple(b[2].split(","))))
    return mounts


def parse_cgroup(data: bytes | str) -> list[tuple[str, str, str]]:
    result = []
    for raw in _text(data).splitlines():
        line = raw.strip()
        if not line: continue
        fields = line.split(":")
        if len(fields) != 3 or not fields[0].isdigit() or not fields[2].startswith("/"):
            raise CgroupObserverError("malformed proc cgroup record")
        path = _path(fields[2])
        result.append((fields[0], fields[1], path))
    return result


def resolve_systemd_mapping(mountinfo: bytes | str, self_cgroup: bytes | str,
                            control_group: str) -> Mapping:
    control = _path(control_group)
    candidates = [m for m in parse_mountinfo(mountinfo)
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
    # is an offset into that hierarchy; accept either kernel spelling (root
    # included) and retain the canonical hierarchy-relative path.
    root = mount.root
    hierarchy_relative = hierarchy[len(root):] if root != "/" and hierarchy.startswith(root + "/") else hierarchy
    control_relative = control[len(root):] if root != "/" and control.startswith(root + "/") else control
    if control_relative != hierarchy_relative and not hierarchy_relative.startswith(control_relative.rstrip("/") + "/"):
        raise CgroupObserverError("ControlGroup does not match systemd hierarchy")
    fs = posixpath.join(mount.mountpoint, control_relative.lstrip("/"))
    return Mapping(mount.mount_id, root, mount.mountpoint, hierarchy, control, fs)


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
    if mapping.mount_root != "/" and value.startswith(mapping.mount_root + "/"):
        value = value[len(mapping.mount_root):]
    rel = value.strip("/").split("/") if value != "/" else []
    return tuple(posixpath.join(mapping.mountpoint, *rel[:i]) for i in range(len(rel), -1, -1))


# Explicit aliases make the small API convenient to callers without adding I/O.
derive_systemd_mapping = resolve_systemd_mapping
map_cgroup_path = resolve_systemd_mapping
