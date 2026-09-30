#!/usr/bin/env python3
"""Prepare an authenticated, local checkout for one consumed gitlink.

This helper never fetches.  It copies the required commit from a local object
source into a fresh, non-shared checkout, authenticates that checkout's Git
object graph, and publishes the supplemental manifest consumed by the image
owner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


SCHEMA = "mckernel.native-exact-mckernel-gitlink-inputs.v1"
LIBDWARF_COMMIT = "ab9230b2b8aa66a3d1d52e4be11fca17a3b63753"
LIBDWARF_PATH = "executer/user/lib/libdwarf/libdwarf"
GIT_SHA256 = "c3edb15c9715b79fcfb1fa978256cdfc14a9ad72a4a8d5680a9fc5ebc6a57e0e"
GIT_VERSION = "git version 2.25.1"


class GitlinkPreparationError(RuntimeError):
    pass


def _fail(ok, message):
    if not ok:
        raise GitlinkPreparationError(message)


def _git(root, *args):
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0",
           "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "0"}
    result = subprocess.run(["/usr/bin/git", "-c", "core.fsmonitor=", "-c",
                             "core.hooksPath=/dev/null", "-C", str(root), *args],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env, check=False)
    _fail(result.returncode == 0 and not result.stderr,
          "git command failed: " + " ".join(args))
    return result.stdout


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _authenticate_git():
    path = Path("/usr/bin/git")
    _fail(path.is_file() and not path.is_symlink() and _sha256(path) == GIT_SHA256,
          "Git executable differs")
    result = subprocess.run([str(path), "--version"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True,
                            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
                            check=False)
    _fail(result.returncode == 0 and not result.stderr and result.stdout.strip() == GIT_VERSION,
          "Git version differs")
    return {"path": str(path), "sha256": GIT_SHA256, "version": GIT_VERSION}


def _safe_rel(raw):
    _fail(raw and not raw.startswith("/") and "\\" not in raw and "\0" not in raw,
          "unsafe tracked path")
    parts = raw.split("/")
    _fail(all(part not in ("", ".", "..") for part in parts), "unsafe tracked path")


def _metadata_inventory(git_meta):
    rows = {}
    for item in sorted(git_meta.rglob("*")):
        relative = item.relative_to(git_meta).as_posix()
        _safe_rel(relative)
        metadata = item.lstat()
        _fail(not stat.S_ISLNK(metadata.st_mode), "Git metadata contains symlink")
        _fail(stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode),
              "Git metadata contains special file")
        if stat.S_ISREG(metadata.st_mode):
            rows[relative] = {"mode": format(stat.S_IMODE(metadata.st_mode), "04o"),
                              "size": metadata.st_size, "sha256": _sha256(item)}
    _fail(rows and "HEAD" in rows and "index" in rows and "config" in rows,
          "Git metadata inventory incomplete")
    return rows


def inventory(checkout):
    checkout = Path(checkout)
    _fail(checkout.is_absolute() and checkout.is_dir() and not checkout.is_symlink(),
          "checkout must be an absolute directory")
    git_dir = _git(checkout, "rev-parse", "--absolute-git-dir").strip()
    common_raw = _git(checkout, "rev-parse", "--git-common-dir").strip()
    _fail(common_raw and "\n" not in common_raw, "malformed Git common directory")
    common_path = Path(common_raw)
    common_dir = common_path if common_path.is_absolute() else (checkout / common_path).resolve()
    git_meta = checkout / ".git"
    _fail(Path(git_dir) == git_meta and Path(common_dir) == git_meta,
          "checkout uses external Git metadata")
    head = _git(checkout, "rev-parse", "--verify", "HEAD^{commit}").strip()
    tree = _git(checkout, "rev-parse", "--verify", "HEAD^{tree}").strip()
    _fail(len(head) == 40 and len(tree) == 40, "malformed Git identity")
    status = _git(checkout, "status", "--porcelain=v1", "--ignored=matching", "--untracked-files=all")
    _fail(not status, "libdwarf checkout is dirty or has ignored extras")
    rows = {}
    index_rows = _git(checkout, "ls-files", "--stage", "-z")
    tree_rows = _git(checkout, "ls-tree", "-r", "--full-tree", "-z", "HEAD")
    for line in index_rows.split("\0"):
        if not line:
            continue
        header, relative = line.split("\t", 1)
        mode, blob, stage = header.split()
        _safe_rel(relative)
        _fail(stage == "0", "staged conflict in checkout")
        path = checkout / relative
        st = os.lstat(path)
        _fail(stat.S_ISREG(st.st_mode), "libdwarf tracked path is not regular: " + relative)
        _fail(mode in ("100644", "100755"), "unsupported tracked mode: " + relative)
        _fail(stat.S_IMODE(st.st_mode) == (0o755 if mode == "100755" else 0o644),
              "libdwarf tracked permission differs: " + relative)
        _fail(_git(checkout, "hash-object", "--no-filters", "--", relative).strip() == blob,
              "tracked blob differs: " + relative)
        rows[relative] = {"mode": mode, "blob": blob, "sha256": _sha256(path)}
    _fail(rows, "libdwarf tracked inventory is empty")
    tree_files = {}
    for line in tree_rows.split("\0"):
        if not line:
            continue
        header, relative = line.split("\t", 1)
        mode, kind, blob = header.split()
        _safe_rel(relative)
        _fail(kind == "blob" and mode in ("100644", "100755"),
              "unsupported HEAD tree entry: " + relative)
        tree_files[relative] = {"mode": mode, "blob": blob}
    _fail({name: {"mode": row["mode"], "blob": row["blob"]}
           for name, row in rows.items()} == tree_files,
          "libdwarf index differs from HEAD tree")
    # A self-contained closure cannot contain a submodule/gitlink, nested
    # repository, symlink, or special file even if it is ignored by Git.
    _fail(git_meta.is_dir() and not git_meta.is_symlink(), "checkout git metadata missing")
    _fail((git_meta / "objects/info/alternates").exists() is False and
          not (git_meta / "shallow").exists() and not (git_meta / "refs/replace").exists(),
          "checkout uses external or replacement Git objects")
    for item in checkout.rglob("*"):
        if item == git_meta or git_meta in item.parents:
            continue
        st = item.lstat()
        _fail(not stat.S_ISLNK(st.st_mode), "libdwarf closure contains symlink")
        _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),
              "libdwarf closure contains special file")
        _fail(not (item.is_dir() and (item / ".git").exists()),
              "libdwarf closure contains nested git repository")
    _fail(_git(checkout, "rev-parse", "--is-shallow-repository").strip() == "false",
          "checkout is shallow")
    _fail(not _git(checkout, "for-each-ref", "--format=%(refname)", "refs/replace").strip(),
          "checkout contains replacement refs")
    _git(checkout, "fsck", "--full", "--no-dangling")
    return {"head": head, "tree": tree, "files": rows,
            "git_metadata": _metadata_inventory(git_meta)}


def _fresh_clone(source, checkout, expected_commit):
    source = Path(source).resolve(strict=True)
    checkout = Path(checkout)
    _fail(source.is_dir() and not source.is_symlink(), "source repository is not a directory")
    _fail(checkout.is_absolute() and not checkout.exists() and not checkout.is_symlink(),
          "checkout destination must be fresh")
    checkout.parent.mkdir(parents=True, exist_ok=True)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0",
           "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "0"}
    command = ["/usr/bin/git", "-c", "core.fsmonitor=", "-c",
               "core.hooksPath=/dev/null", "clone", "--no-local", "--no-hardlinks", "--no-checkout",
               "--no-recurse-submodules", str(source), str(checkout)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env, check=False)
    _fail(result.returncode == 0, "local libdwarf clone failed")
    try:
        resolved = _git(checkout, "rev-parse", "--verify", expected_commit + "^{commit}").strip()
        _fail(resolved == expected_commit, "source repository lacks exact libdwarf commit")
        _git(checkout, "checkout", "--quiet", "--detach", "--force", expected_commit)
        _git(checkout, "remote", "remove", "origin")
        for line in _git(checkout, "ls-files", "--stage", "-z").split("\0"):
            if not line:
                continue
            header, relative = line.split("\t", 1)
            mode, unused_blob, stage = header.split()
            _safe_rel(relative)
            _fail(stage == "0" and mode in ("100644", "100755"),
                  "unsupported libdwarf checkout entry")
            path = checkout / relative
            _fail(stat.S_ISREG(path.lstat().st_mode),
                  "libdwarf checkout entry is not regular")
            os.chmod(path, 0o755 if mode == "100755" else 0o644)
    except BaseException:
        raise
    return checkout


def prepare(*, source, checkout, output, base_manifest, candidate_sha, ihk_sha,
            consumed_path=LIBDWARF_PATH, expected_commit=LIBDWARF_COMMIT):
    _fail(len(expected_commit) == 40 and all(char in "0123456789abcdef" for char in expected_commit),
          "expected full libdwarf commit")
    git_tool = _authenticate_git()
    checkout = _fresh_clone(source, checkout, expected_commit).resolve(strict=True)
    base_manifest = Path(base_manifest).resolve(strict=True)
    data = inventory(checkout)
    _fail(data["head"] == expected_commit, "libdwarf HEAD differs")
    base_bytes = base_manifest.read_bytes()
    base_sha = hashlib.sha256(base_bytes).hexdigest()
    try:
        base = json.loads(base_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GitlinkPreparationError("malformed base manifest") from exc
    _fail(isinstance(base, dict) and base.get("candidate_sha") == candidate_sha and
          base.get("ihk_sha") == ihk_sha, "base manifest identity differs")
    _fail((base.get("gitlinks") or {}).get(consumed_path) == data["head"],
          "base manifest gitlink differs")
    document = {"schema": SCHEMA, "base_manifest_sha256": base_sha,
                "candidate_sha": candidate_sha, "ihk_sha": ihk_sha,
                "preparer_git": git_tool,
                "consumed_gitlinks": {consumed_path: {
                    "path": consumed_path, "commit": data["head"], "tree": data["tree"],
                    "files": data["files"], "git_metadata": data["git_metadata"]}}}
    output = Path(output)
    _fail(output.is_absolute() and not output.exists() and not output.is_symlink(),
          "supplemental manifest must be fresh")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, payload); os.fsync(fd)
    finally:
        os.close(fd)
    return document


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True); parser.add_argument("--checkout", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-manifest", required=True); parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--ihk-sha", required=True); parser.add_argument("--path", default=LIBDWARF_PATH)
    args = parser.parse_args(argv)
    print(json.dumps(prepare(source=args.source, checkout=args.checkout, output=args.output,
                             base_manifest=args.base_manifest, candidate_sha=args.candidate_sha,
                             ihk_sha=args.ihk_sha, consumed_path=args.path), sort_keys=True))


if __name__ == "__main__":
    main()
