#!/usr/bin/env python3
"""Read-only observational inventory of explicitly supplied candidate roots.

The result binds names, types, modes, bytes, and symlink targets observed during
one bounded walk.  It is not an atomic filesystem snapshot; a destructive
consumer must revalidate it after excluding mutators with descriptor-relative,
no-follow operations.
"""

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

SCHEMA_VERSION = 1


class InventoryError(RuntimeError):
    pass


def _root(path):
    p = Path(path)
    if not p.is_absolute():
        raise InventoryError("root must be absolute: " + str(path))
    if ".." in p.parts:
        raise InventoryError("root contains parent traversal: " + str(path))
    # resolve(strict=False) normalizes dot components, but does not follow a
    # final symlink (lstat below rejects that) and gives stable row names.
    p = Path(os.path.abspath(os.fspath(p)))
    # Do not let a symlinked parent redirect an explicitly named root outside
    # the caller's intended path.  Descendant symlinks are recorded, never
    # traversed.
    current = Path(p.anchor)
    for component in p.parts[1:]:
        current /= component
        try:
            if stat.S_ISLNK(os.lstat(current).st_mode):
                raise InventoryError("symlink path component is not allowed: " + str(current))
        except FileNotFoundError:
            break
    try:
        st = os.lstat(p)
    except OSError as exc:
        raise InventoryError("cannot stat root {}: {}".format(p, exc)) from exc
    if stat.S_ISLNK(st.st_mode):
        raise InventoryError("symlink root is not allowed: " + str(p))
    if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):
        raise InventoryError("unsupported root inode: " + str(p))
    return p


def _roots(values):
    if not values:
        raise InventoryError("at least one explicit root is required")
    roots = [_root(value) for value in values]
    names = [os.fspath(p) for p in roots]
    if len(set(names)) != len(names):
        raise InventoryError("duplicate roots are not allowed")
    for i, left in enumerate(roots):
        for right in roots[i + 1 :]:
            try:
                right.relative_to(left)
                nested = True
            except ValueError:
                nested = False
            try:
                left.relative_to(right)
                nested = True
            except ValueError:
                pass
            if nested:
                raise InventoryError("nested roots are not allowed")
    return roots


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _stable_stat(path):
    try:
        return os.lstat(path)
    except OSError as exc:
        raise InventoryError("entry disappeared or is unreadable: {}: {}".format(path, exc)) from exc


def _row(path, root_dev):
    before = _stable_stat(path)
    if before.st_dev != root_dev:
        raise InventoryError("cross-device entry: " + str(path))
    mode = stat.S_IMODE(before.st_mode)
    if stat.S_ISDIR(before.st_mode):
        kind, digest = "directory", None
    elif stat.S_ISREG(before.st_mode):
        kind = "regular"
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                opened = os.fstat(fd)
                if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mode) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mode
                ):
                    raise InventoryError("entry changed while opening: " + str(path))
                h = hashlib.sha256()
                while True:
                    chunk = os.read(fd, 1024 * 1024)
                    if not chunk:
                        break
                    h.update(chunk)
                digest = h.hexdigest()
            finally:
                os.close(fd)
        except OSError as exc:
            raise InventoryError("cannot hash regular entry {}: {}".format(path, exc)) from exc
    elif stat.S_ISLNK(before.st_mode):
        kind = "symlink"
        try:
            digest = _digest(os.fsencode(os.readlink(path)))
        except OSError as exc:
            raise InventoryError("cannot read symlink {}: {}".format(path, exc)) from exc
    else:
        raise InventoryError("unsupported inode type: " + str(path))
    after = _stable_stat(path)
    if (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns
    ):
        raise InventoryError("entry changed during inventory: " + str(path))
    return {
        "path": os.fspath(path).lstrip(os.sep),
        "type": "file" if kind == "regular" else kind,
        "mode": "{:04o}".format(mode),
        "sha256": digest,
    }, before


def inventory(root_values):
    roots = _roots(root_values)
    rows = []
    seen = set()
    for root in roots:
        root_stat = _stable_stat(root)
        stack = [root]
        while stack:
            current = stack.pop()
            row, st = _row(current, root_stat.st_dev)
            name = row["path"]
            if name in seen:
                raise InventoryError("duplicate inventory path: " + name)
            seen.add(name)
            rows.append(row)
            if row["type"] == "directory":
                try:
                    children = list(os.scandir(current))
                except OSError as exc:
                    raise InventoryError("cannot enumerate directory {}: {}".format(current, exc)) from exc
                for child in sorted(children, key=lambda e: e.name, reverse=True):
                    stack.append(Path(child.path))
                after = _stable_stat(current)
                if (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns) != (
                    after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns
                ):
                    raise InventoryError("directory changed during inventory: " + str(current))
    rows.sort(key=lambda row: row["path"])
    return {
        "schema_version": SCHEMA_VERSION,
        "roots": [os.fspath(r) for r in roots],
        "worktree_inventory": rows,
    }


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, ValueError) as exc:
        raise InventoryError("cannot read inventory: {}".format(exc)) from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise InventoryError("unsupported inventory schema")
    if not isinstance(value.get("roots"), list) or not isinstance(value.get("worktree_inventory"), list):
        raise InventoryError("inventory roots/worktree_inventory must be arrays")
    for row in value["worktree_inventory"]:
        if not isinstance(row, dict) or set(row) != {"path", "type", "mode", "sha256"}:
            raise InventoryError("inventory row fields do not match deleter contract")
        if row["path"].startswith("/") or row["type"] not in {"directory", "file", "symlink"}:
            raise InventoryError("invalid inventory row path/type")
        if (not isinstance(row["mode"], str) or len(row["mode"]) != 4 or
                any(c not in "01234567" for c in row["mode"])):
            raise InventoryError("invalid inventory row mode")
    return value


def verify(path, root_values):
    expected = _load(path)
    roots = _roots(root_values)
    actual_roots = [os.fspath(r) for r in roots]
    if expected.get("roots") != actual_roots:
        raise InventoryError("verification roots differ from inventory roots")
    actual = inventory(actual_roots)
    if expected != actual:
        raise InventoryError("inventory does not match live roots")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--root", action="append", required=True)
    generate.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("verify")
    check.add_argument("--inventory", type=Path, required=True)
    check.add_argument("--root", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            result = inventory(args.root)
            with open(args.output, "x", encoding="utf-8") as stream:
                stream.write(_canonical(result))
                stream.flush()
                os.fsync(stream.fileno())
        else:
            verify(args.inventory, args.root)
    except (InventoryError, OSError) as exc:
        print("inventory error: {}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
