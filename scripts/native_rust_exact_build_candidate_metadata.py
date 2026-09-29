#!/usr/bin/env python3
"""Relocate exact-build Git metadata without copying source blobs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

HEX40 = re.compile(r"[0-9a-f]{40}\Z")


class Reject(RuntimeError):
    pass


def run(args, *, git_dir=None, work_tree=None, input_bytes=None):
    env = os.environ.copy()
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"})
    if git_dir is not None:
        env["GIT_DIR"] = str(git_dir)
    if work_tree is not None:
        env["GIT_WORK_TREE"] = str(work_tree)
    p = subprocess.run(["git", *args], input=input_bytes, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, env=env, check=False)
    if p.returncode:
        raise Reject("git failed: %s: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()))
    return p.stdout


def exact_sha(value):
    if not HEX40.fullmatch(value):
        raise Reject("invalid exact commit SHA")
    return value


def safe_dir(path, *, existing=False):
    path = Path(path)
    if path.is_symlink() or (existing and not path.is_dir()):
        raise Reject("unsafe metadata/worktree path: " + str(path))
    if not path.is_absolute():
        raise Reject("paths must be absolute: " + str(path))
    return path.resolve(strict=existing)


def metadata_root(path, source=False):
    path = Path(path)
    if path.is_symlink():
        raise Reject("metadata root is a symlink")
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir:"):
            raise Reject("malformed gitfile")
        target = Path(text[7:].strip())
        if not target.is_absolute():
            target = path.parent / target
        path = target
    if not path.is_dir() or (path / "objects").is_symlink():
        raise Reject("metadata root is not a self-contained Git directory")
    if source:
        if ((path / "commondir").exists() or
                (path / "objects" / "info" / "alternates").exists() or
                (path / "objects" / "info" / "http-alternates").exists()):
            raise Reject("object source uses external Git indirection")
        config = path / "config"
        if any(item.is_symlink() for item in path.rglob("*")):
            raise Reject("object source contains symlink indirection")
        if config.is_symlink() or (config.exists() and any(line.lstrip().startswith("[") and
                                      line.lstrip()[1:].lower().startswith(("include]", "includeif "))
                                      for line in config.read_text(encoding="utf-8").splitlines())):
            raise Reject("object source uses external Git configuration")
        if (path / "objects" / "info" / "alternates").is_file():
            raise Reject("object source uses alternates")
    return path.resolve()


def git_dir_identity(worktree, metadata, expected):
    observed = run(["rev-parse", "HEAD"], git_dir=metadata, work_tree=worktree).decode().strip()
    if observed != expected:
        raise Reject("HEAD differs for " + str(worktree))
    if run(["status", "--porcelain=1", "--untracked-files=all"], git_dir=metadata,
           work_tree=worktree).strip():
        raise Reject("working tree is dirty: " + str(worktree))
    tree = run(["rev-parse", "HEAD^{tree}"], git_dir=metadata).decode().strip()
    if not HEX40.fullmatch(tree):
        raise Reject("malformed HEAD tree")
    return tree


def object_bytes(source, kind, oid):
    data = run(["cat-file", kind, oid], git_dir=source)
    if run(["hash-object", "-t", kind, "--stdin"], git_dir=source, input_bytes=data).decode().strip() != oid:
        raise Reject("malformed object stream: " + oid)
    return data


def collect_trees(source, tree, result):
    if tree in result:
        return
    raw = object_bytes(source, "tree", tree)
    result[tree] = raw
    # cat-file --batch-check is deliberately avoided: parse canonical tree bytes.
    pos = 0
    while pos < len(raw):
        nul = raw.find(b"\0", pos)
        if nul < 0 or b" " not in raw[pos:nul]:
            raise Reject("malformed tree stream")
        mode, name = raw[pos:nul].split(b" ", 1)
        if not re.fullmatch(rb"[0-7]{5,6}", mode) or not name or b"/" in name:
            raise Reject("malformed tree entry")
        start = nul + 1
        oid = raw[start:start + 20]
        if len(oid) != 20:
            raise Reject("truncated tree entry")
        pos = start + 20
        if mode == b"40000":
            collect_trees(source, oid.hex(), result)


def install_objects(destination, commit, trees):
    for oid, raw in [(commit[0], commit[1]), *trees.items()]:
        got = run(["hash-object", "-t", "commit" if oid == commit[0] else "tree", "-w", "--stdin"],
                  git_dir=destination, input_bytes=raw).decode().strip()
        if got != oid:
            raise Reject("object identity changed while installing")


def install_index_symlink_blobs(destination, source, index_bytes):
    """Install only blobs Git needs to compare tracked symlink text."""
    installed = 0
    for row in index_bytes.split(b"\0"):
        if not row:
            continue
        metadata, separator, _ = row.partition(b"\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise Reject("malformed source index entry")
        mode, oid, stage = fields
        if stage != b"0" or not re.fullmatch(rb"[0-9a-f]{40}", oid):
            raise Reject("malformed source index identity")
        if mode != b"120000":
            continue
        expected = oid.decode("ascii")
        raw = object_bytes(source, "blob", expected)
        observed = run(["hash-object", "-t", "blob", "-w", "--stdin"],
                       git_dir=destination, input_bytes=raw).decode().strip()
        if observed != expected:
            raise Reject("symlink blob identity changed while installing")
        installed += 1
    return installed


def build_metadata(stage, source, index_source, worktree, commit_sha, tree, full_objects=False):
    stage.mkdir()
    (stage / "objects").mkdir()
    (stage / "refs").mkdir()
    (stage / "HEAD").write_text("ref: refs/heads/exact-candidate\n", encoding="ascii")
    (stage / "config").write_text("[core]\n\trepositoryformatversion = 0\n\tbare = false\n", encoding="utf-8")
    if full_objects:
        # IHK's independent source checks use historical refs. Copy only the
        # local object/ref stores; alternates, commondir and hooks never enter.
        for name in ("objects", "refs"):
            shutil.copytree(source / name, stage / name, dirs_exist_ok=True)
        if (source / "packed-refs").is_file():
            shutil.copy2(source / "packed-refs", stage / "packed-refs")
    raw = object_bytes(source, "commit", commit_sha)
    trees = {}
    collect_trees(source, tree, trees)
    # The commit is installed after the tree traversal, and no blob is requested.
    if not full_objects:
        install_objects(stage, (commit_sha, raw), trees)
    run(["update-ref", "refs/heads/exact-candidate", commit_sha], git_dir=stage)
    index = stage / "index"
    if not (index_source / "index").is_file() or (index_source / "index").is_symlink():
        raise Reject("source metadata index is missing")
    shutil.copy2(index_source / "index", index)
    index_bytes = run(["ls-files", "-s", "-z"], git_dir=index_source,
                      work_tree=worktree)
    symlink_blobs = 0 if full_objects else install_index_symlink_blobs(
        stage, source, index_bytes)
    return {"head": commit_sha, "tree": tree, "index": str(index),
            "symlink_blobs": symlink_blobs}


def clean_without_blobs(worktree, metadata, expected_index, expected_ihk=None):
    rows = run(["ls-files", "-s", "-z"], git_dir=metadata, work_tree=worktree).split(b"\0")
    observed = []
    gitlinks = {}
    for row in rows:
        if not row:
            continue
        left, sep, name = row.partition(b"\t")
        fields = left.split()
        if not sep or len(fields) != 3:
            raise Reject("malformed index entry")
        mode, oid, stage = fields
        if stage != b"0" or not re.fullmatch(rb"[0-9a-f]{40}", oid):
            raise Reject("malformed index identity")
        rel = name.decode("utf-8", "surrogateescape")
        observed.append(row)
        path = worktree / rel
        if mode == b"160000":
            gitlinks[rel] = oid.decode()
            continue
    if b"\0".join(observed) + (b"\0" if observed else b"") != expected_index:
        raise Reject("installed index differs")
    if expected_ihk and gitlinks.get("ihk") != expected_ihk:
        raise Reject("ihk gitlink identity differs")
    others = run(["ls-files", "--others", "--exclude-standard", "-z"], git_dir=metadata,
                 work_tree=worktree).split(b"\0")
    if any(others):
        raise Reject("untracked files remain")
    dirty = run(["status", "--porcelain=1", "--untracked-files=all"],
                git_dir=metadata, work_tree=worktree).strip()
    if dirty:
        raise Reject("working tree is dirty after installation: " +
                     dirty.decode("utf-8", "backslashreplace"))
    return len(observed), len(gitlinks)


def atomic_json(path, value):
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with tmp.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata_inventory(root):
    rows = []
    for item in sorted(Path(root).rglob("*")):
        if item.is_symlink() or not item.is_file():
            continue
        rel = str(item.relative_to(root))
        rows.append((rel, item.stat().st_size, file_hash(item)))
    encoded = json.dumps(rows, separators=(",", ":"), sort_keys=False).encode()
    return {"files": len(rows), "bytes": sum(row[1] for row in rows),
            "sha256": hashlib.sha256(encoded).hexdigest()}


def relocate(args):
    main = safe_dir(args.main, existing=True)
    ihk = safe_dir(args.ihk, existing=True)
    source_main = metadata_root(args.source_main, source=True)
    source_ihk = metadata_root(args.source_ihk, source=True)
    candidate_main_meta = metadata_root(main / ".git")
    candidate_ihk_meta = metadata_root(ihk / ".git")
    backup = Path(args.backup).resolve()
    evidence = Path(args.evidence).resolve()
    if backup.exists() or backup.is_symlink() or evidence.exists() or evidence.is_symlink():
        raise Reject("backup/evidence destination already exists")
    if ihk != main / "ihk":
        raise Reject("ihk must be main/ihk")
    for destination in (backup, evidence):
        if destination == main or destination == ihk or main in destination.parents or ihk in destination.parents:
            raise Reject("backup/evidence destination overlaps worktree")
    if backup == evidence or backup in evidence.parents or evidence in backup.parents:
        raise Reject("backup/evidence destinations overlap")
    old_main = main / ".git"
    old_ihk = ihk / ".git"
    if old_main.is_symlink() or not (old_main.is_file() or old_main.is_dir()):
        raise Reject("candidate main .git metadata is unsafe")
    if old_ihk.is_symlink() or not (old_ihk.is_file() or old_ihk.is_dir()):
        raise Reject("candidate ihk .git metadata is unsafe")
    main_sha, ihk_sha = exact_sha(args.main_sha), exact_sha(args.ihk_sha)
    main_tree = git_dir_identity(main, candidate_main_meta, main_sha)
    ihk_tree = git_dir_identity(ihk, candidate_ihk_meta, ihk_sha)
    main_index = run(["ls-files", "-s", "-z"], git_dir=candidate_main_meta, work_tree=main)
    ihk_index = run(["ls-files", "-s", "-z"], git_dir=candidate_ihk_meta, work_tree=ihk)
    evidence.mkdir(parents=True)
    receipt = {"status": "FAIL", "rollback": "not-started", "main_sha": main_sha, "ihk_sha": ihk_sha}
    stages = []
    try:
        stage_root = Path(tempfile.mkdtemp(prefix="exact-metadata-", dir=str(main.parent)))
        stages = [stage_root / "main", stage_root / "ihk"]
        main_info = build_metadata(stages[0], source_main, candidate_main_meta, main, main_sha, main_tree)
        ihk_info = build_metadata(stages[1], source_ihk, candidate_ihk_meta, ihk, ihk_sha, ihk_tree, full_objects=True)
        backup.mkdir(parents=True)
        os.replace(old_main, backup / "main.git")
        os.replace(old_ihk, backup / "ihk.git")
        os.replace(stages[0], old_main)
        os.replace(stages[1], old_ihk)
        main_counts = clean_without_blobs(main, old_main, main_index, ihk_sha)
        ihk_counts = clean_without_blobs(ihk, old_ihk, ihk_index)
        main_info["index"] = str(old_main / "index")
        ihk_info["index"] = str(old_ihk / "index")
        main_info.update({"index_sha256": file_hash(old_main / "index"), "tracked": main_counts[0], "gitlinks": main_counts[1]})
        ihk_info.update({"index_sha256": file_hash(old_ihk / "index"), "tracked": ihk_counts[0], "gitlinks": ihk_counts[1]})
        main_info["metadata_inventory"] = metadata_inventory(old_main)
        ihk_info["metadata_inventory"] = metadata_inventory(old_ihk)
        receipt.update({"status": "PASS", "rollback": "not-needed", "installed": {"main": main_info, "ihk": ihk_info},
                        "backup": {"main": str(backup / "main.git"), "ihk": str(backup / "ihk.git")}})
    except Exception as error:
        receipt["error"] = str(error)
        receipt["rollback"] = "attempted"
        try:
            if (backup / "main.git").exists():
                if old_main.exists():
                    shutil.rmtree(old_main) if old_main.is_dir() else old_main.unlink()
                os.replace(backup / "main.git", old_main)
            if (backup / "ihk.git").exists():
                if old_ihk.exists():
                    shutil.rmtree(old_ihk) if old_ihk.is_dir() else old_ihk.unlink()
                os.replace(backup / "ihk.git", old_ihk)
            receipt["rollback"] = "restored"
        except Exception as rollback_error:
            receipt["rollback"] = "failed: " + str(rollback_error)
        if evidence.exists():
            atomic_json(evidence / "receipt.json", receipt)
        raise
    finally:
        for stage in stages:
            if stage.exists():
                shutil.rmtree(stage)
        if 'stage_root' in locals() and stage_root.exists():
            shutil.rmtree(stage_root)
    atomic_json(evidence / "receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("main", "ihk", "source-main", "source-ihk", "backup", "evidence"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--ihk-sha", required=True)
    args = parser.parse_args(argv)
    try:
        result = relocate(args)
    except (Reject, OSError, subprocess.SubprocessError) as error:
        print("candidate metadata rejected: " + str(error), file=os.sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
