#!/usr/bin/env python3
"""Use tracked IHK sources or restore a historical checkout from pinned bundles.

Only Git data is imported. No archived script, controller, build or runtime is
executed. Bundles come from the committed parent tree, including in a sparse
checkout. An optional local base repository changes transport, never identities.
The working IHK checkout is left untouched unless the destination is empty.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile


class RestoreError(RuntimeError):
    pass


def git(repo, *args, input=None):
    result = subprocess.run(
        ["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0",
         "-C", str(repo), *args], input=input,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RestoreError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def object_id(value, label):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise RestoreError(f"{label} must be a lowercase 40-digit Git object ID")
    return value


def tree_entry(repo, revision, path):
    records = git(repo, "ls-tree", "-z", revision, "--", path).split(b"\0")
    for record in records:
        if not record:
            continue
        metadata, name = record.split(b"\t", 1)
        if name.decode("utf-8") == path:
            return metadata.decode("ascii").split()
    raise RestoreError(f"committed tree has no entry for {path}")


def load_manifest(repo, revision, manifest_path=None):
    try:
        if manifest_path is None:
            # The CLI's declared chain comes from the same committed revision
            # as the gitlink and bundles, never a dirty working-tree manifest.
            data = git(repo, "cat-file", "blob", f"{revision}:scripts/ihk_source_bundles.json")
            manifest = json.loads(data.decode("utf-8"))
        else:
            manifest = json.loads(Path(manifest_path).read_text())
        if manifest["version"] != 1:
            raise RestoreError("unsupported IHK source manifest version")
        base = manifest["base"]
        object_id(base["commit"], "base commit")
        if base["url"] != "https://github.com/ihkmckernel/ihk.git":
            raise RestoreError("base URL must be the canonical IHK source URL")
        bundles = manifest["bundles"]
        if not isinstance(bundles, list) or not bundles:
            raise RestoreError("manifest must contain an ordered nonempty bundle list")
        for bundle in bundles:
            object_id(bundle["blob"], "bundle blob")
            object_id(bundle["tip"], "bundle tip")
            path = bundle["path"]
            if (not isinstance(path, str) or not path
                    or PurePosixPath(path).is_absolute()
                    or any(part in ("", ".", "..") for part in path.split("/"))):
                raise RestoreError("bundle path must be relative to the committed tree")
            mode, kind, oid = tree_entry(repo, revision, path)
            if mode != "100644" or kind != "blob" or oid != bundle["blob"]:
                raise RestoreError(f"bundle blob does not match committed tree: {path}")
        mode, kind, target = tree_entry(repo, revision, "ihk")
        if mode == "040000" and kind == "tree":
            target = object_id(
                git(repo, "cat-file", "blob", f"{revision}:ihk/VENDORED-REVISION")
                .decode("ascii").strip(), "vendored IHK revision")
        elif mode != "160000" or kind != "commit":
            raise RestoreError("committed ihk entry must be a source tree or Git submodule")
        if bundles[-1]["tip"] != target:
            raise RestoreError("final bundle tip does not match committed IHK source revision")
        return base, bundles, target
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RestoreError(f"invalid IHK source manifest: {error}") from error


def destination_ready(destination, target):
    """Return True for an exact clean checkout; otherwise require absent/empty."""
    if destination.is_symlink():
        raise RestoreError("refusing a symlink destination")
    if not destination.exists():
        return False
    if not destination.is_dir():
        raise RestoreError("destination is not a directory")
    if not any(destination.iterdir()):
        return False
    try:
        root = Path(git(destination, "rev-parse", "--show-toplevel").decode().strip())
        head = git(destination, "rev-parse", "HEAD").decode().strip()
        dirty = git(destination, "status", "--porcelain", "--untracked-files=all")
    except RestoreError as error:
        raise RestoreError("refusing a nonempty unrelated destination") from error
    if root.resolve() != destination.resolve():
        raise RestoreError("destination is not the root of its own Git checkout")
    sparse = git(destination, "config", "--bool", "--default=false", "--get", "core.sparseCheckout").strip()
    entries = git(destination, "ls-files", "-v", "-z").split(b"\0")
    if sparse == b"true" or any(
        entry and (entry[:1] == b"S" or entry[:1].islower()) for entry in entries
    ):
        raise RestoreError("refusing a sparse checkout or hidden tracked index entries")
    if head != target or dirty:
        raise RestoreError("refusing an existing dirty or mismatched IHK checkout")
    return True


def vendored_destination_ready(repo, destination, revision):
    """Verify tracked bytes directly without creating a nested Git repository."""
    if (destination.is_symlink() or not destination.is_dir()
            or os.path.lexists(str(destination / ".git"))):
        raise RestoreError("vendored ihk/ must be a materialized directory without .git")
    git(repo, "diff-index", "--cached", "--quiet", revision, "--", "ihk")
    if git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", "ihk"):
        raise RestoreError("vendored IHK source contains untracked files")
    for row in git(repo, "ls-tree", "-r", "-z", revision, "--", "ihk").split(b"\0"):
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, expected = metadata.split()
        path = repo / name.decode("utf-8")
        info = path.lstat()
        if mode == b"120000" and stat.S_ISLNK(info.st_mode):
            data = os.fsencode(os.readlink(str(path)))
        elif mode in (b"100644", b"100755") and stat.S_ISREG(info.st_mode):
            if stat.S_IMODE(info.st_mode) != (0o755 if mode == b"100755" else 0o644):
                raise RestoreError("vendored IHK file mode differs: " + str(path))
            data = path.read_bytes()
        else:
            raise RestoreError("vendored IHK entry type differs: " + str(path))
        actual = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
        if kind != b"blob" or actual.hexdigest().encode("ascii") != expected:
            raise RestoreError("vendored IHK file bytes differ: " + str(path))


def restore(repo, destination=None, base_repository=None, manifest_path=None):
    repo = Path(repo).resolve()
    # Freeze the parent revision once: every subsequent tree lookup uses it.
    revision = git(repo, "rev-parse", "HEAD^{commit}").decode().strip()
    base, bundles, target = load_manifest(repo, revision, manifest_path)
    destination = Path(os.path.abspath(destination if destination is not None else repo / "ihk"))
    mode, kind, unused_id = tree_entry(repo, revision, "ihk")
    if mode == "040000" and kind == "tree" and destination == repo / "ihk":
        vendored_destination_ready(repo, destination, revision)
        return target, False
    if destination_ready(destination, target):
        return target, False
    source = base["url"]
    if base_repository is not None:
        source = str(Path(base_repository).resolve())
        if not Path(source).is_dir():
            raise RestoreError("local base repository must be an existing directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ihk-source-", dir=destination.parent) as work:
        work = Path(work)
        staged = work / "checkout"
        staged.mkdir()
        git(staged, "init", "--quiet")
        git(staged, "remote", "add", "origin", base["url"])
        git(staged, "fetch", "--no-tags", "--update-shallow", source, base["commit"])
        fetched = git(staged, "rev-parse", "FETCH_HEAD^{commit}").decode().strip()
        if fetched != base["commit"]:
            raise RestoreError("base transport returned a different commit")
        for index, bundle in enumerate(bundles):
            data = git(repo, "cat-file", "blob", bundle["blob"])
            actual = git(repo, "hash-object", "--stdin", input=data).decode().strip()
            if actual != bundle["blob"]:
                raise RestoreError(f"bundle bytes failed blob identity check: {bundle['path']}")
            bundle_path = work / f"source-{index}.bundle"
            bundle_path.write_bytes(data)
            git(staged, "bundle", "verify", str(bundle_path))
            heads = git(staged, "bundle", "list-heads", str(bundle_path))
            if not any(line.split()[0].decode() == bundle["tip"] for line in heads.splitlines()):
                raise RestoreError(f"bundle does not advertise its pinned tip: {bundle['path']}")
            git(staged, "fetch", "--no-tags", str(bundle_path), bundle["tip"])
        git(staged, "-c", "core.hooksPath=/dev/null", "checkout", "--quiet", "--detach", target)
        if git(staged, "rev-parse", "HEAD").decode().strip() != target:
            raise RestoreError("staged checkout does not match committed ihk gitlink")
        # Directory rename refuses a newly nonempty destination. No existing
        # checkout is removed or modified to make installation succeed.
        if destination_ready(destination, target):
            return target, False
        os.rename(staged, destination)
    return target, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--destination", type=Path, help="optional historical Git checkout destination; default: use REPO/ihk")
    parser.add_argument("--base-repository", type=Path, help="local transport for the same pinned public base commit")
    args = parser.parse_args()
    try:
        target, changed = restore(args.repo, args.destination, args.base_repository)
    except (RestoreError, OSError) as error:
        parser.exit(1, f"IHK source restoration refused: {error}\n")
    print(f"{'Restored' if changed else 'Already present'} IHK source {target}")


if __name__ == "__main__":
    main()
