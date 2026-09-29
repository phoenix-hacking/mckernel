#!/usr/bin/env python3
"""Produce a fail-closed, descriptor-rooted retention inventory."""
from __future__ import print_function
import argparse
import errno
import hashlib
import json
import os
import stat
import subprocess
import sys
import time


class InventoryError(RuntimeError):
    pass


_DIR_FLAGS = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) |
              getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0))
_FILE_FLAGS = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) |
               getattr(os, "O_CLOEXEC", 0))


def _kind(st):
    if stat.S_ISDIR(st.st_mode): return "directory"
    if stat.S_ISREG(st.st_mode): return "regular"
    if stat.S_ISLNK(st.st_mode): return "symlink"
    if stat.S_ISFIFO(st.st_mode): return "fifo"
    if stat.S_ISCHR(st.st_mode): return "character-device"
    if stat.S_ISBLK(st.st_mode): return "block-device"
    if stat.S_ISSOCK(st.st_mode): return "socket"
    return "unsupported"


def _stable(st):
    return (st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode),
            st.st_uid, st.st_gid, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _identity(st):
    return {"dev": st.st_dev, "inode": st.st_ino, "uid": st.st_uid,
            "gid": st.st_gid, "mode": stat.S_IMODE(st.st_mode)}


def _same_lstat(path_st, fd_st, what):
    if _stable(path_st) != _stable(fd_st):
        raise InventoryError("%s changed while opening" % what)


def _open_root(path, label):
    path = os.path.abspath(path)
    try:
        before = os.lstat(path)
        if not stat.S_ISDIR(before.st_mode):
            raise InventoryError("root is not a directory: " + path)
        # Opening component-by-component makes a symlinked ancestor fail too;
        # O_NOFOLLOW on a single absolute open protects only its final name.
        fd = _open_dir_nofollow(path)
    except OSError as exc:
        raise InventoryError("cannot open root %s: %s" % (label, exc))
    try:
        _same_lstat(before, os.fstat(fd), "root " + label)
    except Exception:
        os.close(fd)
        raise
    return fd, before


def _blob_oid(data, fmt):
    algo = hashlib.sha1 if fmt == "sha1" else hashlib.sha256
    return algo(("blob %d\0" % len(data)).encode("ascii") + data).hexdigest()


def _digest_and_oids(fd, expected, what):
    plain, sha1_blob, sha256_blob = hashlib.sha256(), hashlib.sha1(), hashlib.sha256()
    header = ("blob %d\0" % expected).encode("ascii")
    sha1_blob.update(header); sha256_blob.update(header)
    total = 0
    while True:
        try: data = os.read(fd, 1024 * 1024)
        except OSError as exc: raise InventoryError("cannot read %s: %s" % (what, exc))
        if not data: break
        total += len(data)
        if total > expected: raise InventoryError("file changed while reading: " + what)
        plain.update(data); sha1_blob.update(data); sha256_blob.update(data)
    if total != expected: raise InventoryError("file changed while reading: " + what)
    return plain.hexdigest(), {"sha1": sha1_blob.hexdigest(), "sha256": sha256_blob.hexdigest()}


def _contained_link(prefix, target, rel):
    if os.path.isabs(target): raise InventoryError("symlink escapes root: " + rel)
    resolved = os.path.normpath(os.path.join(prefix, target))
    if resolved == ".." or resolved.startswith("../"):
        raise InventoryError("symlink escapes root: " + rel)


def _walk(root, label, global_regular_inodes):
    """Walk through already-opened directory FDs; never re-open file paths."""
    rootfd, root_before = _open_root(root, label)
    entries = []

    def visit(dirfd, prefix, initial):
        try: before_names = sorted(os.listdir(dirfd))
        except OSError as exc: raise InventoryError("cannot read %s: %s" % (prefix or label, exc))
        if any(not n or n in (".", "..") or "/" in n or "\0" in n for n in before_names):
            raise InventoryError("invalid directory entry")
        for name in before_names:
            rel = name if not prefix else prefix + "/" + name
            try: before = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
            except OSError as exc: raise InventoryError("cannot lstat %s: %s" % (rel, exc))
            kind = _kind(before)
            if kind not in ("directory", "regular", "symlink"):
                raise InventoryError("unsupported node %s (%s)" % (rel, kind))
            row = {"path": rel, "type": kind, "mode": stat.S_IMODE(before.st_mode),
                   "uid": before.st_uid, "gid": before.st_gid, "size": before.st_size}
            if kind == "regular":
                if before.st_nlink != 1: raise InventoryError("hardlinked regular file: " + rel)
                inode = (before.st_dev, before.st_ino)
                if inode in global_regular_inodes: raise InventoryError("cross-root regular inode alias: " + rel)
                global_regular_inodes.add(inode)
                try: child = os.open(name, _FILE_FLAGS, dir_fd=dirfd)
                except OSError as exc: raise InventoryError("cannot open %s: %s" % (rel, exc))
                try:
                    _same_lstat(before, os.fstat(child), rel)
                    row["sha256"], row["git_oids"] = _digest_and_oids(child, before.st_size, rel)
                    if _stable(before) != _stable(os.fstat(child)):
                        raise InventoryError("file changed while reading: " + rel)
                finally: os.close(child)
            elif kind == "symlink":
                if label == "metadata-backup" or _is_metadata(rel):
                    raise InventoryError("metadata Git symlink is not permitted: " + rel)
                try:
                    target = os.readlink(name, dir_fd=dirfd)
                    after_link = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
                except OSError as exc: raise InventoryError("cannot read link %s: %s" % (rel, exc))
                if _stable(before) != _stable(after_link):
                    raise InventoryError("symlink changed while reading: " + rel)
                _contained_link(prefix, target, rel)
                row["target"] = target; row["size"] = len(os.fsencode(target))
                raw = os.fsencode(target)
                row["git_oids"] = {"sha1": _blob_oid(raw, "sha1"), "sha256": _blob_oid(raw, "sha256")}
            entries.append(row)
            if kind == "directory":
                try: child = os.open(name, _DIR_FLAGS, dir_fd=dirfd)
                except OSError as exc: raise InventoryError("cannot descend %s: %s" % (rel, exc))
                try:
                    _same_lstat(before, os.fstat(child), rel)
                    visit(child, rel, os.fstat(child))
                    if _stable(before) != _stable(os.stat(name, dir_fd=dirfd, follow_symlinks=False)):
                        raise InventoryError("directory changed during inventory: " + rel)
                finally: os.close(child)
        try: after_names = sorted(os.listdir(dirfd))
        except OSError as exc: raise InventoryError("cannot reread %s: %s" % (prefix or label, exc))
        if before_names != after_names or _stable(initial) != _stable(os.fstat(dirfd)):
            raise InventoryError("directory changed during inventory: " + (prefix or label))

    try:
        visit(rootfd, "", os.fstat(rootfd))
        try: root_after = os.lstat(root)
        except OSError as exc: raise InventoryError("cannot revalidate root %s: %s" % (label, exc))
        if _stable(root_before) != _stable(root_after) or _stable(root_before) != _stable(os.fstat(rootfd)):
            raise InventoryError("root changed during inventory: " + label)
    finally: os.close(rootfd)
    return _identity(root_before), entries, _stable(root_before)


def _valid_oid(value, fmt):
    return len(value) == (40 if fmt == "sha1" else 64) and all(c in "0123456789abcdef" for c in value)


def _git_env():
    return {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "TZ": "UTC",
            "HOME": "/nonexistent", "XDG_CONFIG_HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat"}


def _git(root, args):
    git_dir = os.path.join(root, ".git")
    try: dotgit = os.lstat(git_dir)
    except OSError as exc: raise InventoryError("cannot lstat Git directory: %s" % exc)
    if not stat.S_ISDIR(dotgit.st_mode): raise InventoryError("Git directory must be a real directory: " + git_dir)
    try:
        return subprocess.check_output(["/usr/bin/git", "--no-optional-locks", "--git-dir=" + git_dir,
                                        "--work-tree=" + root] + args, env=_git_env(), stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError) as exc: raise InventoryError("cannot prove Git tree: %s" % exc)


def _tree_path(path):
    return bool(path) and not path.startswith(b"/") and all(x not in (b"", b".", b"..") for x in path.split(b"/"))


def _git_status_paths(root, tree, prefix, allow_dirty, allow_dirty_gitlink=False):
    """Validate worktree dirt without weakening the committed-tree proof.

    Only tracked regular files may be content-dirty.  A main repository's
    ``ihk`` gitlink is also allowed to be dirty because its nested repository
    is checked independently.  Deletions, type changes, symlink changes and
    all other tracked changes remain fail-closed; coverage and exact symlink
    checks below provide the second line of defence.
    """
    raw = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=no"])
    if not raw:
        return
    if not allow_dirty:
        raise InventoryError("Git repository is not clean: " + root)
    pos = 0
    while pos < len(raw):
        if pos + 3 > len(raw):
            raise InventoryError("malformed Git status record")
        status = raw[pos:pos + 2]
        pos += 2
        if pos < len(raw) and raw[pos:pos + 1] == b" ":
            pos += 1
        end = raw.find(b"\0", pos)
        if end < 0:
            raise InventoryError("unterminated Git status record")
        path_raw = raw[pos:end]
        pos = end + 1
        if status[0:1] in (b"R", b"C"):
            end = raw.find(b"\0", pos)
            if end < 0:
                raise InventoryError("unterminated Git rename record")
            # Renames/copies are never an allowed regular-file modification:
            # the old/new coverage and exact tree path checks must reject them.
            raise InventoryError("tracked rename/copy is not permitted")
        try:
            rel = os.fsdecode(path_raw)
        except UnicodeError:
            raise InventoryError("invalid Git status path")
        if not _tree_path(path_raw):
            raise InventoryError("unsafe Git status path")
        path = prefix + rel
        value = tree.get(path)
        if value is None:
            raise InventoryError("Git status path is not in committed tree: " + path)
        if value["mode"] in (0o100644, 0o100755):
            # A tracked regular modification is retained as capsule-required
            # if its descriptor walk finds it and its blob differs.
            if status != b" M":
                raise InventoryError("staged tracked change is not permitted: " + path)
            continue
        if (value["mode"] == 0o160000 and path == "ihk" and
                allow_dirty_gitlink and status == b" M"):
            continue
        raise InventoryError("only unstaged tracked regular files may be dirty: " + path)


def _git_tree(root, revision, prefix="", allow_dirty=False, allow_dirty_gitlink=False):
    if not revision: return {}, None
    fmt = _git(root, ["rev-parse", "--show-object-format"]).decode("ascii", "strict").strip()
    if fmt not in ("sha1", "sha256"): raise InventoryError("unsupported Git object format: " + fmt)
    head = _git(root, ["rev-parse", "--verify", "HEAD^{commit}"]).decode("ascii", "strict").strip()
    if not _valid_oid(head, fmt) or revision != head: raise InventoryError("Git repository is not requested exact HEAD: " + root)
    raw = _git(root, ["ls-tree", "-rz", "-r", head])
    result, raw_paths = {}, set()
    for record in raw.split(b"\0"):
        if not record: continue
        if record.count(b"\t") != 1: raise InventoryError("malformed Git tree record")
        left, path = record.split(b"\t", 1); fields = left.split(b" ")
        if len(fields) != 3: raise InventoryError("malformed Git tree record")
        try:
            mode = int(fields[0], 8); typ = fields[1].decode("ascii", "strict")
            oid = fields[2].decode("ascii", "strict"); rel0 = os.fsdecode(path)
        except (UnicodeError, ValueError): raise InventoryError("malformed Git tree record")
        if (fields[0] not in (b"100644", b"100755", b"120000", b"160000") or
                not _tree_path(path) or mode not in (0o100644, 0o100755, 0o120000, 0o160000) or
                not _valid_oid(oid, fmt) or ((mode == 0o160000) != (typ == "commit")) or
                (mode != 0o160000 and typ != "blob")):
            raise InventoryError("malformed Git tree record")
        rel = prefix + rel0
        if path in raw_paths or rel in result: raise InventoryError("duplicate/colliding Git tree path")
        raw_paths.add(path); result[rel] = {"mode": mode, "type": typ, "oid": oid, "format": fmt}
    _git_status_paths(root, result, prefix, allow_dirty, allow_dirty_gitlink)
    return result, fmt


def _is_metadata(path):
    return path == ".git" or path.startswith(".git/") or path == "ihk/.git" or path.startswith("ihk/.git/")


def _path_overlap(a, b):
    aa, bb, ra, rb = os.path.abspath(a), os.path.abspath(b), os.path.realpath(a), os.path.realpath(b)
    return os.path.commonpath([aa, bb]) in (aa, bb) or os.path.commonpath([ra, rb]) in (ra, rb)


def _revalidate_root(path, expected, label):
    """Catch a root altered after its own walk while the other root was read."""
    try:
        now = os.lstat(path)
    except OSError as exc:
        raise InventoryError("cannot revalidate root %s: %s" % (label, exc))
    if expected != _stable(now):
        raise InventoryError("root changed during combined inventory: " + label)


def build_plan(candidate_root, metadata_root, main_revision=None, ihk_revision=None,
               allow_dirty_tracked_regular=False):
    candidate_root, metadata_root = os.path.abspath(candidate_root), os.path.abspath(metadata_root)
    if _path_overlap(candidate_root, metadata_root): raise InventoryError("roots must not contain or alias one another")
    if ihk_revision and not main_revision: raise InventoryError("IHK revision requires main revision")
    # Traverse both roots before invoking Git.  Thus a poisoned/untrusted Git
    # directory never gets a subprocess opportunity until specials and all
    # metadata-link policy have been proven from descriptors.
    seen = set()
    candidate_ident, candidate_entries, candidate_before = _walk(candidate_root, "candidate", seen)
    metadata_ident, metadata_entries, metadata_before = _walk(metadata_root, "metadata-backup", seen)
    main_tree, main_fmt = _git_tree(candidate_root, main_revision, "", allow_dirty_tracked_regular,
                                    bool(ihk_revision))
    ihk_tree, _ = (_git_tree(os.path.join(candidate_root, "ihk"), ihk_revision, "ihk/",
                             allow_dirty_tracked_regular)
                   if ihk_revision else ({}, None))
    if ihk_revision:
        expected = {"mode": 0o160000, "type": "commit", "oid": ihk_revision, "format": main_fmt}
        if main_tree.get("ihk") != expected: raise InventoryError("main IHK gitlink does not bind requested IHK revision")
    tree = dict(main_tree)
    for path, value in ihk_tree.items():
        if path in tree: raise InventoryError("colliding main/IHK Git tree path: " + path)
        tree[path] = value
    # Git proof is an external reader, so prove both roots stayed stable after it.
    _revalidate_root(candidate_root, candidate_before, "candidate")
    _revalidate_root(metadata_root, metadata_before, "metadata-backup")
    # Root stat checks do not detect an in-place regular-file write.  Repeat
    # the complete descriptor/hash walk after Git proof and require byte-for-
    # byte equality with the original snapshot before classifying anything.
    seen_after = set()
    candidate_ident_after, candidate_entries_after, candidate_after = _walk(candidate_root, "candidate", seen_after)
    metadata_ident_after, metadata_entries_after, metadata_after = _walk(metadata_root, "metadata-backup", seen_after)
    if (candidate_ident_after, candidate_entries_after, candidate_after) != (candidate_ident, candidate_entries, candidate_before):
        raise InventoryError("candidate member changed during combined inventory")
    if (metadata_ident_after, metadata_entries_after, metadata_after) != (metadata_ident, metadata_entries, metadata_before):
        raise InventoryError("metadata-backup member changed during combined inventory")
    active = {r["path"]: r for r in candidate_entries if not _is_metadata(r["path"])}
    tracked_links = {p for p, v in tree.items() if v["mode"] == 0o120000}
    actual_links = {p for p, r in active.items() if r["type"] == "symlink"}
    if actual_links != tracked_links: raise InventoryError("tracked symlink set is not exact")
    for path in tracked_links:
        if active[path]["git_oids"][tree[path]["format"]] != tree[path]["oid"]:
            raise InventoryError("tracked symlink content mismatch: " + path)
    for path, value in tree.items():
        if value["mode"] in (0o100644, 0o100755):
            if path not in active: raise InventoryError("tracked regular file is missing: " + path)
            if active[path]["type"] != "regular": raise InventoryError("tracked regular file has wrong type: " + path)
    all_entries = []
    for label, entries in (("candidate", candidate_entries), ("metadata-backup", metadata_entries)):
        for original in entries:
            row = dict(original); row["root"] = label; path = row["path"]
            if label == "metadata-backup" or _is_metadata(path): row["classification"] = "capsule-required"
            elif row["type"] == "symlink": row["classification"] = "reconstructible"
            elif row["type"] == "regular":
                tracked = tree.get(path)
                row["classification"] = "reconstructible" if tracked and tracked["mode"] in (0o100644, 0o100755) and row["git_oids"][tracked["format"]] == tracked["oid"] else "capsule-required"
            elif row["type"] == "directory": row["classification"] = "reconstructible" if any(k.startswith(path + "/") for k in tree) else "capsule-required"
            else: raise InventoryError("unsupported node " + path)
            all_entries.append(row)
    all_entries.sort(key=lambda item: (item["root"], item["path"]))
    return {"format": "native-exact-candidate-retention-v1", "roots": [
                {"name": "candidate", "path": candidate_root, "identity": candidate_ident},
                {"name": "metadata-backup", "path": metadata_root, "identity": metadata_ident}],
            "revisions": {"main": main_revision, "ihk": ihk_revision}, "entries": all_entries,
            "capsule_required": [x["root"] + ":" + x["path"] for x in all_entries if x["classification"] == "capsule-required"]}


def _open_dir_nofollow(path):
    fd = os.open(os.path.sep, _DIR_FLAGS)
    try:
        for part in os.path.abspath(path).split(os.path.sep):
            if part:
                nxt = os.open(part, _DIR_FLAGS, dir_fd=fd); os.close(fd); fd = nxt
        return fd
    except Exception:
        os.close(fd); raise


def _write_all(fd, data):
    offset = 0
    while offset < len(data):
        amount = os.write(fd, data[offset:])
        if amount <= 0: raise OSError("short output write")
        offset += amount


def write_atomic(path, value):
    path = os.path.abspath(path); parent, name = os.path.dirname(path), os.path.basename(path)
    if not name or name in (".", ".."): raise InventoryError("invalid output name")
    dfd, tmp = _open_dir_nofollow(parent), None
    try:
        payload = (json.dumps(value, sort_keys=True, indent=2, separators=(",", ": ")) + "\n").encode("utf-8")
        for counter in range(128):
            tmp = ".retention.%d.%d.%d" % (os.getpid(), time.time_ns(), counter)
            try:
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), 0o600, dir_fd=dfd); break
            except OSError as exc:
                if exc.errno != errno.EEXIST: raise
        else: raise InventoryError("cannot allocate atomic output name")
        try: _write_all(fd, payload); os.fsync(fd)
        finally: os.close(fd)
        try: os.link(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd, follow_symlinks=False)
        except OSError as exc:
            if exc.errno == errno.EEXIST: raise InventoryError("output already exists: " + path)
            raise
        os.fsync(dfd); os.unlink(tmp, dir_fd=dfd); tmp = None; os.fsync(dfd)
    finally:
        if tmp is not None:
            try: os.unlink(tmp, dir_fd=dfd)
            except OSError: pass
        os.close(dfd)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", required=True); parser.add_argument("--metadata-backup-root", required=True)
    parser.add_argument("--main-revision", "--main-commit", dest="main_revision"); parser.add_argument("--ihk-revision", "--ihk-commit", dest="ihk_revision")
    parser.add_argument("--allow-dirty-tracked-regular", action="store_true",
                        help="allow tracked regular content changes; classify them as capsule-required")
    parser.add_argument("--output", required=True); args = parser.parse_args(argv)
    output = os.path.abspath(args.output)
    for root in (os.path.abspath(args.candidate_root), os.path.abspath(args.metadata_backup_root)):
        if _path_overlap(root, output): raise InventoryError("output must not contain, be inside, or alias an input root")
    write_atomic(output, build_plan(args.candidate_root, args.metadata_backup_root, args.main_revision,
                                    args.ihk_revision, args.allow_dirty_tracked_regular)); return 0


if __name__ == "__main__":
    try: sys.exit(main())
    except (InventoryError, OSError) as exc:
        print("retention inventory failed: %s" % exc, file=sys.stderr); sys.exit(2)
