#!/usr/bin/env python3
"""Capture active host-module negative-errno sites from compiler evidence.

The legacy host-module build is heavily conditional.  Looking for ``-EINVAL``
and similar spellings in the source tree therefore counts inactive branches and
headers that are not part of the compiled module.  This tool instead consumes
the exact Kbuild ``.cmd`` records emitted by the Rocky build, reconstructs a
side-effect-free preprocessing command, and scans only lines attributed by the
preprocessor to the effective target source.

No command text is ever evaluated by a shell.  Kbuild command text is parsed
with :mod:`shlex`, shell substitution is rejected, and the compiler is invoked
with an argument vector.  The standalone Rust helper has no C preprocessor, so
its exact source bytes are scanned directly while retaining its recorded
``.cmd`` and compiler provenance.
"""

import sys as _fp0006_entry_sys


if __name__ == "__main__":
    _fp0006_entry_sys.stderr.write(
        "host-module authority entry requires the commit-bound isolated "
        "workflow bootstrap; refusing worktree execution\n"
    )
    raise SystemExit(2)


import argparse
import bisect
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path


SCHEMA_VERSION = 1
PROFILE = "compiler-backed-active-host-module-failure-sites-v1"
ERRNO_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])-\s*(?:\(\s*)*(E[A-Z][A-Z0-9_]*)\b"
)
LINE_MARKER_PATTERN = re.compile(
    r'^\s*#\s*(?:line\s+)?(?P<line>[0-9]+)\s+"(?P<file>(?:\\.|[^"\\])*)"'
    r"(?:\s+[0-9]+)*\s*$"
)
ASSIGNMENT_PATTERN = re.compile(r"^(?P<kind>cmd|source)_(?P<key>.+?)\s*:=\s*(?P<value>.*)$")
CONTROL_TOKENS = {";", "&&", "||", "|", "&", ">", ">>", "<", "<<", "<>", "&>"}
COMPILE_SEPARATORS = {";", "&&", "||", "|", "&"}
DEPENDENCY_FLAGS = {"-M", "-MM", "-MD", "-MMD", "-MG", "-MP"}
DEPENDENCY_VALUE_FLAGS = {"-MF", "-MT", "-MQ", "-MJ"}
OUTPUT_VALUE_FLAGS = {"-o", "--output"}


# This is the exact x86_64/Rust-helper source closure selected by the current
# Rocky validation build.  Missing records fail the capture instead of silently
# shrinking the oracle.  Assembly inputs do not contain errno-return sites and
# are tracked separately by the assembly policy.
EXPECTED_SOURCES = (
    ("ihk", "c", "ihk/linux/core/host_driver.c", "ihk/linux/core/.host_driver.o.cmd"),
    ("ihk", "c", "ihk/linux/core/mem_alloc.c", "ihk/linux/core/.mem_alloc.o.cmd"),
    ("ihk", "c", "ihk/linux/core/mm.c", "ihk/linux/core/.mm.o.cmd"),
    ("ihk", "c", "ihk/linux/core/mikc.c", "ihk/linux/core/.mikc.o.cmd"),
    ("ihk", "c", "ihk/ikc/linux.c", "ihk/ikc/.linux.o.cmd"),
    ("ihk", "c", "ihk/ikc/master.c", "ihk/ikc/.master.o.cmd"),
    ("ihk", "c", "ihk/ikc/queue.c", "ihk/ikc/.queue.o.cmd"),
    (
        "ihk_smp_x86_64",
        "c",
        "ihk/linux/driver/smp/arch/x86_64/smp-arch-driver.c",
        "ihk/linux/driver/smp/arch/x86_64/.smp-arch-driver.o.cmd",
    ),
    (
        "ihk_smp_x86_64",
        "c",
        "ihk/linux/driver/smp/smp-driver.c",
        "ihk/linux/driver/smp/.smp-driver.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/driver.c",
        "executer/kernel/mcctrl/.driver.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/control.c",
        "executer/kernel/mcctrl/.control.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/syscall.c",
        "executer/kernel/mcctrl/.syscall.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/procfs.c",
        "executer/kernel/mcctrl/.procfs.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/sysfs.c",
        "executer/kernel/mcctrl/.sysfs.o.cmd",
    ),
    (
        "mcctrl",
        "c",
        "executer/kernel/mcctrl/futex.c",
        "executer/kernel/mcctrl/.futex.o.cmd",
    ),
    (
        "mcctrl",
        "rust",
        "executer/kernel/mcctrl/rust/mcctrl_helpers.rs",
        "executer/kernel/mcctrl/rust/.mcctrl_helpers.o.cmd",
    ),
)


# A fresh capture is allowed to read only committed main-repository authority
# bytes.  The IHK submodule is handled separately because the Rocky build
# intentionally applies the committed compatibility overlay before compiling.
# Keep the executable generators and their focused tests in this closure: a
# dirty authority script must not be able to mint evidence attributed to HEAD.
FRESH_MAIN_AUTHORITY_PATHS = (
    ".github/workflows/rust-x86_64-validation.yml",
    ".gitmodules",
    "executer/include/uprotocol.h",
    "executer/kernel/mcctrl/control.c",
    "executer/kernel/mcctrl/driver.c",
    "executer/kernel/mcctrl/futex.c",
    "executer/kernel/mcctrl/mcctrl.h",
    "executer/kernel/mcctrl/procfs.c",
    "executer/kernel/mcctrl/rust/mcctrl_helpers.rs",
    "executer/kernel/mcctrl/syscall.c",
    "executer/kernel/mcctrl/sysfs.c",
    "host-kernel/contracts/legacy-behavior-contract-f2eb7352.json",
    "host-kernel/contracts/native-rust-host-modules-policy-v1.json",
    "host-kernel/reference/legacy-host-modules-f2eb7352.json",
    "scripts/host_module_contracts.py",
    "scripts/host_module_failure_contract_gaps.py",
    "scripts/host_module_failure_contract_review_v2.py",
    "scripts/host_module_failure_contract_review_v3.py",
    "scripts/host_module_failure_flows.py",
    "scripts/host_module_failure_flows_v2.py",
    "scripts/host_module_failure_semantics_retention_v3.py",
    "scripts/host_module_failure_semantics_v3.py",
    "scripts/host_module_failure_sites.py",
    "scripts/host_module_inventory.py",
    "scripts/patches/ihk-linux-compat.patch",
    "scripts/record_compiler_argv.py",
    "scripts/rocky-rust-validation.sh",
    "scripts/tests/test_host_module_contracts.py",
    "scripts/tests/test_host_module_failure_contract_gaps.py",
    "scripts/tests/test_host_module_failure_contract_review_v2.py",
    "scripts/tests/test_host_module_failure_contract_review_v3.py",
    "scripts/tests/test_host_module_failure_flows.py",
    "scripts/tests/test_host_module_failure_flows_v2.py",
    "scripts/tests/test_host_module_failure_semantics_retention_v3.py",
    "scripts/tests/test_host_module_failure_semantics_v3.py",
    "scripts/tests/test_host_module_failure_sites.py",
)

MAX_AUTHORITY_FILE_BYTES = 64 * 1024 * 1024
GIT_EXECUTABLE = "/usr/bin/git"

AUTHORITY_CONTEXT_ATTRIBUTE = "_mckernel_fp0006_authority_context"
AUTHORITY_MODULE_PATHS = {
    "host_module_contracts": "scripts/host_module_contracts.py",
    "host_module_failure_contract_gaps": "scripts/host_module_failure_contract_gaps.py",
    "host_module_failure_contract_review_v2": "scripts/host_module_failure_contract_review_v2.py",
    "host_module_failure_contract_review_v3": "scripts/host_module_failure_contract_review_v3.py",
    "host_module_failure_flows": "scripts/host_module_failure_flows.py",
    "host_module_failure_flows_v2": "scripts/host_module_failure_flows_v2.py",
    "host_module_failure_semantics_retention_v3": "scripts/host_module_failure_semantics_retention_v3.py",
    "host_module_failure_semantics_v3": "scripts/host_module_failure_semantics_v3.py",
    "host_module_inventory": "scripts/host_module_inventory.py",
    "record_compiler_argv": "scripts/record_compiler_argv.py",
    "scripts.tests.test_host_module_contracts": "scripts/tests/test_host_module_contracts.py",
    "scripts.tests.test_host_module_failure_contract_gaps": "scripts/tests/test_host_module_failure_contract_gaps.py",
    "scripts.tests.test_host_module_failure_contract_review_v2": "scripts/tests/test_host_module_failure_contract_review_v2.py",
    "scripts.tests.test_host_module_failure_contract_review_v3": "scripts/tests/test_host_module_failure_contract_review_v3.py",
    "scripts.tests.test_host_module_failure_flows": "scripts/tests/test_host_module_failure_flows.py",
    "scripts.tests.test_host_module_failure_flows_v2": "scripts/tests/test_host_module_failure_flows_v2.py",
    "scripts.tests.test_host_module_failure_semantics_retention_v3": "scripts/tests/test_host_module_failure_semantics_retention_v3.py",
    "scripts.tests.test_host_module_failure_semantics_v3": "scripts/tests/test_host_module_failure_semantics_v3.py",
    "scripts.tests.test_host_module_failure_sites": "scripts/tests/test_host_module_failure_sites.py",
}
AUTHORITY_TARGET_MODULES = {
    "contracts": "host_module_contracts",
    "failure-contract-gaps": "host_module_failure_contract_gaps",
    "failure-contract-review-v2": "host_module_failure_contract_review_v2",
    "failure-contract-review-v3": "host_module_failure_contract_review_v3",
    "failure-flows-v1": "host_module_failure_flows",
    "failure-flows-v2": "host_module_failure_flows_v2",
    "failure-semantics-v3": "host_module_failure_semantics_v3",
}
AUTHORITY_TEST_MODULES = frozenset(
    name for name in AUTHORITY_MODULE_PATHS if name.startswith("scripts.tests.")
)
AUTHORITY_STDLIB_MODULES = (
    "argparse",
    "bisect",
    "collections",
    "hashlib",
    "io",
    "importlib",
    "json",
    "os",
    "pathlib",
    "re",
    "shlex",
    "shutil",
    "stat",
    "subprocess",
    "sys",
    "tarfile",
    "tempfile",
    "types",
)


class CaptureError(RuntimeError):
    """Raised when compiler-backed evidence is absent or ambiguous."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def file_digest(path):
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CaptureError("cannot read evidence file {0}: {1}".format(path, exc))
    return {"bytes": len(data), "sha256": sha256_bytes(data)}, data


def resolved(path):
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise CaptureError("cannot resolve path {0}: {1}".format(path, exc))


def require_within(path, root, label):
    candidate = str(resolved(path))
    base = str(resolved(root))
    try:
        common = os.path.commonpath((candidate, base))
    except ValueError:
        common = ""
    if common != base:
        raise CaptureError("{0} escapes {1}: {2}".format(label, root, path))


def git_environment(extra=None):
    """Return a deterministic Git environment without inherited redirection."""

    config = (
        ("core.fsmonitor", "false"),
        ("core.hooksPath", os.devnull),
        ("core.attributesFile", os.devnull),
        ("core.pager", "cat"),
        ("pager.status", "false"),
        ("protocol.ext.allow", "never"),
        ("core.sshCommand", "/bin/false"),
    )
    environment = {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": str(len(config)),
        "GIT_GRAFT_FILE": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.devnull,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    for index, (key, value) in enumerate(config):
        environment["GIT_CONFIG_KEY_{0}".format(index)] = key
        environment["GIT_CONFIG_VALUE_{0}".format(index)] = value
    if extra:
        if set(extra) != {"GIT_CEILING_DIRECTORIES"}:
            raise CaptureError("unsupported trusted Git environment override")
        environment.update(extra)
    return environment


def run_git(repo, arguments, label, input_data=None):
    try:
        completed = subprocess.run(
            [GIT_EXECUTABLE] + list(arguments),
            cwd=str(repo),
            check=False,
            env=git_environment(),
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("cannot {0}: {1}".format(label, exc))
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise CaptureError("cannot {0}: {1}".format(label, detail or "git failed"))
    return completed.stdout


def validate_relative_authority_path(value, label):
    if not isinstance(value, str) or not value or "\0" in value:
        raise CaptureError("{0} is malformed".format(label))
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise CaptureError("{0} is not a normalized relative path: {1}".format(label, value))
    if str(path) != value:
        raise CaptureError("{0} is not canonical: {1}".format(label, value))
    return value


def read_authority_snapshot(root, relative, label):
    """Read one regular file through no-follow descriptors and retain identity."""

    relative = validate_relative_authority_path(relative, label)
    root = resolved(root)
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise CaptureError("no-follow authority traversal is unavailable")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
        file_flags |= os.O_CLOEXEC
    directory_fd = None
    file_fd = None
    try:
        directory_fd = os.open(str(root), directory_flags)
        parts = Path(relative).parts
        for component in parts[:-1]:
            try:
                next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            except OSError as exc:
                raise CaptureError(
                    "{0} has a symlink or non-directory ancestor: {1}".format(
                        label, relative
                    )
                ) from exc
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
        except OSError as exc:
            raise CaptureError(
                "{0} is missing, non-regular, or a symlink: {1}".format(
                    label, relative
                )
            ) from exc
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise CaptureError("{0} is not a regular file: {1}".format(label, relative))
        if before.st_size < 0 or before.st_size > MAX_AUTHORITY_FILE_BYTES:
            raise CaptureError("{0} has an invalid size: {1}".format(label, relative))
        chunks = []
        remaining = MAX_AUTHORITY_FILE_BYTES + 1
        while remaining:
            chunk = os.read(file_fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(file_fd)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if identity_before != identity_after or len(data) != before.st_size:
            raise CaptureError("{0} changed while being read: {1}".format(label, relative))
        return {
            "data": data,
            "identity": identity_after,
            "mode": stat.S_IMODE(after.st_mode),
            "path": relative,
            "sha256": sha256_bytes(data),
        }
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def read_symlink_snapshot(root, relative, label):
    relative = validate_relative_authority_path(relative, label)
    root = resolved(root)
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise CaptureError("no-follow authority traversal is unavailable")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
    directory_fd = None
    try:
        directory_fd = os.open(str(root), directory_flags)
        parts = Path(relative).parts
        for component in parts[:-1]:
            try:
                next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            except OSError as exc:
                raise CaptureError(
                    "{0} has a symlink or non-directory ancestor: {1}".format(
                        label, relative
                    )
                ) from exc
            os.close(directory_fd)
            directory_fd = next_fd
        before = os.stat(parts[-1], dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISLNK(before.st_mode):
            raise CaptureError("{0} is not a symlink: {1}".format(label, relative))
        target = os.readlink(parts[-1], dir_fd=directory_fd)
        after = os.stat(parts[-1], dir_fd=directory_fd, follow_symlinks=False)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        data = os.fsencode(target)
        if identity_before != identity_after or len(data) != before.st_size:
            raise CaptureError("{0} changed while being read: {1}".format(label, relative))
        return {
            "data": data,
            "identity": identity_after,
            "mode": stat.S_IMODE(after.st_mode),
            "path": relative,
            "sha256": sha256_bytes(data),
        }
    except OSError as exc:
        raise CaptureError("cannot read {0} {1}: {2}".format(label, relative, exc))
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def parse_tree_entries(data, label):
    entries = {}
    for raw in data.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, path_data = raw.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            path = path_data.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise CaptureError("{0} contains a malformed tree row".format(label)) from exc
        validate_relative_authority_path(path, label + " path")
        if path in entries:
            raise CaptureError("{0} repeats path {1}".format(label, path))
        entries[path] = (mode, object_type, object_id)
    return entries


def parse_index_entries(data, label):
    entries = {}
    for raw in data.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, path_data = raw.split(b"\t", 1)
            mode, object_id, stage = metadata.decode("ascii").split(" ")
            path = path_data.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise CaptureError("{0} contains a malformed index row".format(label)) from exc
        validate_relative_authority_path(path, label + " path")
        if stage != "0" or path in entries:
            raise CaptureError("{0} has an unmerged or duplicate path {1}".format(label, path))
        entries[path] = (mode, object_id)
    return entries


def git_tree_entries(repo, commit):
    return parse_tree_entries(
        run_git(repo, ["ls-tree", "-r", "-z", commit], "read committed tree"),
        "committed tree",
    )


def git_index_entries(repo):
    return parse_index_entries(
        run_git(repo, ["ls-files", "--stage", "-z"], "read repository index"),
        "repository index",
    )


def git_blob_bytes(repo, object_ids):
    ordered = list(object_ids)
    request = b"".join((value + "\n").encode("ascii") for value in ordered)
    output = run_git(repo, ["cat-file", "--batch"], "read committed blobs", request)
    position = 0
    values = []
    for expected in ordered:
        newline = output.find(b"\n", position)
        if newline < 0:
            raise CaptureError("committed blob batch is truncated")
        try:
            header = output[position:newline].decode("ascii").split(" ")
            object_id, object_type, size_text = header
            size = int(size_text)
        except (UnicodeDecodeError, ValueError) as exc:
            raise CaptureError("committed blob batch header is malformed") from exc
        start = newline + 1
        end = start + size
        if object_id != expected or object_type != "blob" or end >= len(output):
            raise CaptureError("committed blob batch identity is malformed")
        if output[end : end + 1] != b"\n":
            raise CaptureError("committed blob batch delimiter is malformed")
        values.append(output[start:end])
        position = end + 1
    if position != len(output):
        raise CaptureError("committed blob batch has trailing bytes")
    return values


def authority_main_paths():
    paths = set(FRESH_MAIN_AUTHORITY_PATHS)
    for _, _, source, _ in EXPECTED_SOURCES:
        if not source.startswith("ihk/"):
            paths.add(source)
    return tuple(sorted(paths))


def list_main_worktree_files(repo, gitlinks):
    files = set()
    stack = [(Path(repo), "")]
    while stack:
        directory, prefix = stack.pop()
        try:
            entries = list(os.scandir(str(directory)))
        except OSError as exc:
            raise CaptureError("cannot inspect main worktree: {0}".format(exc))
        for entry in entries:
            relative = entry.name if not prefix else prefix + "/" + entry.name
            if not prefix and entry.name in (".git", "evidence"):
                continue
            if relative in gitlinks:
                continue
            try:
                if entry.is_symlink():
                    files.add(relative)
                elif entry.is_dir(follow_symlinks=False):
                    stack.append((Path(entry.path), relative))
                elif entry.is_file(follow_symlinks=False):
                    files.add(relative)
                else:
                    raise CaptureError(
                        "main worktree contains a special file: {0}".format(relative)
                    )
            except OSError as exc:
                raise CaptureError(
                    "cannot inspect main worktree path {0}: {1}".format(relative, exc)
                )
    return files


def snapshot_committed_main_authority(repo, head, tree, index):
    expected_index = {
        path: (entry[0], entry[2])
        for path, entry in tree.items()
    }
    if index != expected_index:
        raise CaptureError("main repository index differs from {0}".format(head))
    for path in authority_main_paths():
        entry = tree.get(path)
        if entry is None or entry[0] not in ("100644", "100755") or entry[1] != "blob":
            raise CaptureError("main authority path is not a committed regular file: {0}".format(path))
    blob_paths = sorted(
        path for path, entry in tree.items() if entry[1] == "blob"
    )
    gitlinks = {
        path for path, entry in tree.items() if entry[1] == "commit"
    }
    if any(
        entry[1] not in ("blob", "commit")
        for entry in tree.values()
    ):
        raise CaptureError("main committed tree contains an unsupported object type")
    actual_paths = list_main_worktree_files(repo, gitlinks)
    if actual_paths != set(blob_paths):
        unexpected = sorted(actual_paths - set(blob_paths))
        missing = sorted(set(blob_paths) - actual_paths)
        raise CaptureError(
            "main worktree file closure differs; unexpected={0}, missing={1}".format(
                unexpected[:5], missing[:5]
            )
        )
    object_ids = [tree[path][2] for path in blob_paths]
    blobs = git_blob_bytes(repo, object_ids)
    snapshots = {}
    for path, blob in zip(blob_paths, blobs):
        mode = tree[path][0]
        if mode in ("100644", "100755"):
            snapshot = read_authority_snapshot(repo, path, "main authority")
            expected_mode = 0o755 if mode == "100755" else 0o644
            mode_matches = snapshot["mode"] & 0o111 == expected_mode & 0o111
        elif mode == "120000":
            snapshot = read_symlink_snapshot(repo, path, "main authority")
            mode_matches = True
        else:
            raise CaptureError("main committed tree has an unsupported mode: {0}".format(path))
        if snapshot["data"] != blob or not mode_matches:
            raise CaptureError("main authority worktree differs from HEAD: {0}".format(path))
        snapshots[path] = snapshot
    return snapshots


def parse_overlay_paths(overlay_bytes):
    with tempfile.TemporaryDirectory(prefix="host-module-overlay-list.") as temporary:
        patch_path = Path(temporary) / "overlay.patch"
        patch_path.write_bytes(overlay_bytes)
        environment = git_environment(
            {"GIT_CEILING_DIRECTORIES": str(Path(temporary).parent)}
        )
        try:
            completed = subprocess.run(
                [GIT_EXECUTABLE, "apply", "--numstat", "-z", str(patch_path)],
                cwd=temporary,
                check=False,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CaptureError("cannot inspect compatibility overlay: {0}".format(exc))
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise CaptureError("compatibility overlay is malformed: {0}".format(detail))
        paths = []
        for raw in completed.stdout.split(b"\0"):
            if not raw:
                continue
            try:
                additions, deletions, path_data = raw.split(b"\t", 2)
                path = path_data.decode("utf-8")
            except (UnicodeDecodeError, ValueError) as exc:
                raise CaptureError("compatibility overlay numstat is malformed") from exc
            if not additions.isdigit() or not deletions.isdigit():
                raise CaptureError("binary compatibility overlays are forbidden")
            validate_relative_authority_path(path, "compatibility overlay path")
            if path in paths:
                raise CaptureError("compatibility overlay repeats path {0}".format(path))
            paths.append(path)
        if not paths:
            raise CaptureError("compatibility overlay changes no files")
        return tuple(sorted(paths))


def apply_overlay_to_committed_blobs(tree, blobs, overlay_bytes):
    with tempfile.TemporaryDirectory(prefix="host-module-overlay-authority.") as temporary:
        root = Path(temporary)
        patch_path = root / "overlay.patch"
        patch_path.write_bytes(overlay_bytes)
        affected = parse_overlay_paths(overlay_bytes)
        for path in affected:
            entry = tree.get(path)
            if entry is None or entry[0] not in ("100644", "100755") or entry[1] != "blob":
                raise CaptureError(
                    "compatibility overlay may only modify committed regular files: {0}".format(path)
                )
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blobs[path])
            destination.chmod(0o755 if entry[0] == "100755" else 0o644)
        environment = git_environment(
            {"GIT_CEILING_DIRECTORIES": str(root.parent)}
        )
        for arguments, label in (
            ([GIT_EXECUTABLE, "apply", "--check", str(patch_path)], "validate compatibility overlay"),
            ([GIT_EXECUTABLE, "apply", str(patch_path)], "apply compatibility overlay"),
        ):
            try:
                completed = subprocess.run(
                    arguments,
                    cwd=str(root),
                    check=False,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise CaptureError("cannot {0}: {1}".format(label, exc))
            if completed.returncode != 0:
                detail = completed.stderr.decode("utf-8", errors="replace").strip()
                raise CaptureError("cannot {0}: {1}".format(label, detail or "git apply failed"))
        expected = dict(blobs)
        for path in affected:
            expected[path] = (root / path).read_bytes()
        return expected, set(affected)


def list_worktree_files(root):
    files = set()
    stack = [(Path(root), "")]
    while stack:
        directory, prefix = stack.pop()
        try:
            entries = list(os.scandir(str(directory)))
        except OSError as exc:
            raise CaptureError("cannot inspect IHK worktree: {0}".format(exc))
        for entry in entries:
            relative = entry.name if not prefix else prefix + "/" + entry.name
            if not prefix and entry.name == ".git":
                continue
            try:
                if entry.is_symlink():
                    raise CaptureError("IHK worktree contains a symlink: {0}".format(relative))
                if entry.is_dir(follow_symlinks=False):
                    stack.append((Path(entry.path), relative))
                elif entry.is_file(follow_symlinks=False):
                    files.add(relative)
                else:
                    raise CaptureError("IHK worktree contains a special file: {0}".format(relative))
            except OSError as exc:
                raise CaptureError("cannot inspect IHK worktree path {0}: {1}".format(relative, exc))
    return files


def snapshot_exact_ihk_overlay(repo, ihk_head, overlay_snapshot):
    ihk = repo / "ihk"
    tree = git_tree_entries(ihk, ihk_head)
    index = git_index_entries(ihk)
    expected_index = {
        path: (entry[0], entry[2])
        for path, entry in tree.items()
    }
    if index != expected_index:
        raise CaptureError("IHK index differs from its recorded submodule commit")
    for path, entry in tree.items():
        if entry[0] not in ("100644", "100755") or entry[1] != "blob":
            raise CaptureError("IHK authority tree has a non-regular entry: {0}".format(path))
    object_ids = [tree[path][2] for path in sorted(tree)]
    contents = git_blob_bytes(ihk, object_ids)
    committed = {path: data for path, data in zip(sorted(tree), contents)}
    expected, affected = apply_overlay_to_committed_blobs(
        tree, committed, overlay_snapshot["data"]
    )
    actual_paths = list_worktree_files(ihk)
    if actual_paths != set(tree):
        unexpected = sorted(actual_paths - set(tree))
        missing = sorted(set(tree) - actual_paths)
        raise CaptureError(
            "IHK worktree file closure differs; unexpected={0}, missing={1}".format(
                unexpected[:5], missing[:5]
            )
        )
    snapshots = {}
    changed = set()
    for path in sorted(tree):
        snapshot = read_authority_snapshot(ihk, path, "IHK authority")
        expected_mode = 0o755 if tree[path][0] == "100755" else 0o644
        if snapshot["mode"] & 0o111 != expected_mode & 0o111:
            raise CaptureError("IHK worktree mode differs from commit: {0}".format(path))
        if snapshot["data"] != expected[path]:
            raise CaptureError(
                "IHK worktree is not the recorded commit plus exact overlay: {0}".format(path)
            )
        if snapshot["data"] != committed[path]:
            changed.add(path)
        snapshots[path] = snapshot
    if changed != affected:
        raise CaptureError(
            "IHK worktree changed-path set differs from exact overlay; actual={0}, expected={1}".format(
                sorted(changed), sorted(affected)
            )
        )
    return snapshots


def exact_expected_head(expected_head):
    if not isinstance(expected_head, str) or not re.match(
        r"^[0-9a-f]{40}$", expected_head
    ):
        raise CaptureError("repository authority expected HEAD is not an exact commit")
    return expected_head


def capture_repository_authority(repo, expected_head=None):
    """Snapshot exact fresh authority for HEAD plus the one allowed IHK overlay."""

    repo = resolved(repo)
    if not repo.is_dir() or not (repo / "ihk").is_dir():
        raise CaptureError("fresh repository authority requires the main and IHK repositories")
    try:
        ihk_root_metadata = os.lstat(str(repo / "ihk"))
    except OSError as exc:
        raise CaptureError("cannot inspect IHK worktree root: {0}".format(exc))
    if not stat.S_ISDIR(ihk_root_metadata.st_mode):
        raise CaptureError("IHK worktree root must be a real directory")
    if expected_head is None:
        expected_head = git_head(repo)
    expected_head = exact_expected_head(expected_head)
    main_head = git_head(repo)
    if main_head != expected_head:
        raise CaptureError(
            "repository HEAD differs from bootstrap expected commit"
        )
    ihk_head = git_head(repo / "ihk")
    main_tree = git_tree_entries(repo, main_head)
    main_index = git_index_entries(repo)
    gitlink = main_tree.get("ihk")
    if gitlink is None or gitlink[0] != "160000" or gitlink[1] != "commit":
        raise CaptureError("main repository does not record the IHK submodule")
    if main_index.get("ihk") != (gitlink[0], gitlink[2]):
        raise CaptureError("main index records a different IHK submodule commit")
    if gitlink[2] != ihk_head:
        raise CaptureError("IHK HEAD differs from the main repository gitlink")
    main_snapshots = snapshot_committed_main_authority(
        repo, main_head, main_tree, main_index
    )
    overlay = main_snapshots.get("scripts/patches/ihk-linux-compat.patch")
    if overlay is None:
        raise CaptureError("committed compatibility overlay is outside authority closure")
    ihk_snapshots = snapshot_exact_ihk_overlay(repo, ihk_head, overlay)
    if git_head(repo) != expected_head or git_head(repo / "ihk") != ihk_head:
        raise CaptureError("repository HEAD changed during authority snapshot")
    return {
        "ihk_head": ihk_head,
        "ihk_snapshots": ihk_snapshots,
        "main_head": main_head,
        "main_snapshots": main_snapshots,
        "repo": str(repo),
    }


def recheck_repository_authority(repo, authority):
    if not isinstance(authority, dict) or set(authority) != {
        "ihk_head", "ihk_snapshots", "main_head", "main_snapshots", "repo"
    }:
        raise CaptureError("fresh repository authority snapshot is malformed")
    repo = resolved(repo)
    if authority.get("repo") != str(repo):
        raise CaptureError("fresh repository authority belongs to another checkout")
    try:
        current = capture_repository_authority(
            repo, expected_head=authority["main_head"]
        )
    except CaptureError as exc:
        raise CaptureError(
            "repository authority changed during fresh replay: {0}".format(exc)
        )
    if current != authority:
        raise CaptureError("repository authority changed during fresh replay")


def _module_origin_is_stdlib(name, module):
    # Rocky 8's Python 3.6 starts the built-in ``sys`` module before importlib
    # has attached a ModuleSpec.  It consequently has neither a trustworthy
    # origin nor a ``__file__`` even under ``python -I -S``.  Bind that one
    # legacy case to the interpreter entry module captured before any other
    # imports; an object substituted into ``sys.modules`` still fails.
    if name == "sys":
        return module is _fp0006_entry_sys
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    if origin in ("built-in", "frozen"):
        return True
    filename = getattr(module, "__file__", None)
    if not isinstance(filename, str) or not filename:
        return False
    candidate = os.path.realpath(filename)
    if "{0}site-packages{0}".format(os.sep) in candidate:
        return False
    if "{0}dist-packages{0}".format(os.sep) in candidate:
        return False
    for prefix in (sys.base_prefix, sys.exec_prefix):
        prefix = os.path.realpath(prefix)
        try:
            if os.path.commonpath((candidate, prefix)) == prefix:
                return True
        except ValueError:
            continue
    return False


def reject_untrusted_inherited_modules():
    for name in AUTHORITY_STDLIB_MODULES:
        module = sys.modules.get(name)
        if module is not None and not _module_origin_is_stdlib(name, module):
            raise CaptureError(
                "authority bootstrap inherited an untrusted {0} module".format(name)
            )


def require_isolated_authority_runtime(repo):
    """Reject inherited import state before any captured module is loaded."""

    if not sys.flags.isolated or not sys.flags.no_site:
        raise CaptureError(
            "authority bootstrap requires isolated Python with site disabled"
        )
    repo = resolved(repo)
    for entry in sys.path:
        if not isinstance(entry, str) or not entry:
            raise CaptureError("isolated Python exposes an unsafe empty import path")
        candidate = os.path.realpath(entry)
        try:
            if os.path.commonpath((candidate, str(repo))) == str(repo):
                raise CaptureError(
                    "isolated Python exposes the repository on its import path"
                )
        except ValueError:
            pass
    reject_untrusted_inherited_modules()


class _AuthoritySnapshotLoader:
    def __init__(self, fullname, path, snapshot, repo):
        self.fullname = fullname
        self.path = path
        self.snapshot = snapshot
        self.filename = str(Path(repo) / path)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        data = self.snapshot.get("data")
        if not isinstance(data, bytes) or b"\0" in data:
            raise ImportError(
                "captured module bytes are malformed: {0}".format(self.path)
            )
        module.__file__ = self.filename
        module.__cached__ = None
        code = compile(data, self.filename, "exec", dont_inherit=True)
        exec(code, module.__dict__)


class _AuthoritySnapshotFinder:
    def __init__(self, snapshots, repo):
        self.snapshots = snapshots
        self.repo = repo

    def find_spec(self, fullname, path=None, target=None):
        relative = AUTHORITY_MODULE_PATHS.get(fullname)
        if relative is None:
            return None
        snapshot = self.snapshots.get(relative)
        if snapshot is None:
            raise ImportError(
                "authority snapshot omits module {0}".format(relative)
            )
        loader = _AuthoritySnapshotLoader(fullname, relative, snapshot, self.repo)
        return importlib.util.spec_from_loader(
            fullname, loader, origin=str(Path(self.repo) / relative)
        )


class _AuthoritySysPath(list):
    """Keep PathFinder away from repository bytes after authority capture."""

    def __init__(self, values, repo):
        super().__init__(values)
        self.repo = str(resolved(repo))

    def _is_repository_path(self, value):
        if not isinstance(value, str):
            return False
        candidate = os.path.realpath(value)
        try:
            return os.path.commonpath((candidate, self.repo)) == self.repo
        except ValueError:
            return False

    def insert(self, index, value):
        if self._is_repository_path(value):
            return
        raise CaptureError("authority-loaded code attempted to extend sys.path")

    def append(self, value):
        return self.insert(len(self), value)

    def extend(self, values):
        for value in values:
            self.insert(len(self), value)

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __setitem__(self, key, value):
        raise CaptureError("authority-loaded code attempted to replace sys.path")


def _namespace_module(name):
    module = types.ModuleType(name)
    module.__package__ = name
    module.__path__ = []
    module.__file__ = None
    return module


def _prepare_authority_imports(repo, snapshots):
    current = sys.modules[__name__]
    existing_sites = sys.modules.get("host_module_failure_sites")
    if existing_sites not in (None, current):
        raise CaptureError("an untrusted host_module_failure_sites module is preloaded")
    for name in AUTHORITY_MODULE_PATHS:
        if name in sys.modules:
            raise CaptureError("an authority target module is already loaded: {0}".format(name))
    for name in ("scripts", "scripts.tests"):
        if name in sys.modules:
            raise CaptureError("an authority namespace is already loaded: {0}".format(name))
    sys.modules["host_module_failure_sites"] = current
    sys.modules["scripts"] = _namespace_module("scripts")
    sys.modules["scripts.tests"] = _namespace_module("scripts.tests")
    finder = _AuthoritySnapshotFinder(snapshots, repo)
    original_path = sys.path
    sys.path = _AuthoritySysPath(original_path, repo)
    sys.meta_path.insert(0, finder)
    return finder, original_path


def _restore_authority_imports(finder, original_path):
    try:
        sys.meta_path.remove(finder)
    except ValueError:
        pass
    sys.path = original_path


def _load_authority_module(name):
    __import__(name)
    module = sys.modules.get(name)
    if module is None:
        raise CaptureError("authority module did not load: {0}".format(name))
    return module


def committed_authority_module_snapshots(repo, expected_head):
    """Read only allowlisted Python modules from the current committed tree."""

    repo = resolved(repo)
    head = exact_expected_head(expected_head)
    if git_head(repo) != head:
        raise CaptureError(
            "repository HEAD differs from bootstrap expected commit"
        )
    tree = git_tree_entries(repo, head)
    paths = sorted(set(AUTHORITY_MODULE_PATHS.values()) | {
        "scripts/host_module_failure_sites.py"
    })
    object_ids = []
    for path in paths:
        entry = tree.get(path)
        if entry is None or entry[0] not in ("100644", "100755") or entry[1] != "blob":
            raise CaptureError(
                "committed authority module is missing or non-regular: {0}".format(path)
            )
        object_ids.append(entry[2])
    blobs = git_blob_bytes(repo, object_ids)
    snapshots = {}
    for path, data in zip(paths, blobs):
        snapshots[path] = {
            "data": data,
            "path": path,
            "sha256": sha256_bytes(data),
        }
    launcher = read_authority_snapshot(
        repo, "scripts/host_module_failure_sites.py", "historical authority launcher"
    )
    if launcher["data"] != snapshots["scripts/host_module_failure_sites.py"]["data"]:
        raise CaptureError("historical authority launcher differs from current HEAD")
    if git_head(repo) != head:
        raise CaptureError("repository HEAD changed during historical snapshot")
    return head, snapshots


def _run_authority_tests(module_names):
    import unittest

    if not module_names:
        raise CaptureError("authority unittest target requires at least one module")
    suites = []
    for name in module_names:
        if name not in AUTHORITY_TEST_MODULES:
            raise CaptureError("unapproved authority unittest module: {0}".format(name))
        module = _load_authority_module(name)
        suites.append(unittest.defaultTestLoader.loadTestsFromModule(module))
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
    return 0 if result.wasSuccessful() else 1


def _run_authority_target(target, target_argv, repository_authority):
    context = {
        "mode": "historical" if repository_authority is None else "fresh",
        "repository_authority": repository_authority,
    }
    setattr(sys, AUTHORITY_CONTEXT_ATTRIBUTE, context)
    if target == "failure-sites":
        return main(target_argv, repository_authority=repository_authority)
    if target == "unittest":
        return _run_authority_tests(target_argv)
    module_name = AUTHORITY_TARGET_MODULES.get(target)
    if module_name is None:
        raise CaptureError("unknown authority target: {0}".format(target))
    module = _load_authority_module(module_name)
    if target in (
        "failure-flows-v2",
        "failure-contract-review-v2",
        "failure-semantics-v3",
        "failure-contract-review-v3",
    ):
        return module.main(
            target_argv, repository_authority=repository_authority
        )
    return module.main(target_argv)


def _repository_from_arguments(arguments):
    for index, value in enumerate(arguments):
        if value == "--repo":
            if index + 1 >= len(arguments):
                raise CaptureError("--repo requires a value")
            return Path(arguments[index + 1])
        if value.startswith("--repo="):
            return Path(value.split("=", 1)[1])
    return Path(__file__).resolve().parents[1]


def parse_authority_entry_arguments(argv):
    values = list(argv)
    if "--" in values:
        boundary = values.index("--")
        launcher = values[:boundary]
        target_argv = values[boundary + 1 :]
    else:
        launcher = values
        target_argv = None
    target = "failure-sites"
    historical = False
    cleaned = []
    index = 0
    while index < len(launcher):
        value = launcher[index]
        if value == "--authority-target":
            if index + 1 >= len(launcher):
                raise CaptureError("--authority-target requires a value")
            target = launcher[index + 1]
            index += 2
            continue
        if value == "--authority-historical":
            historical = True
            index += 1
            continue
        cleaned.append(value)
        index += 1
    if target not in set(AUTHORITY_TARGET_MODULES) | {"failure-sites", "unittest"}:
        raise CaptureError("unknown authority target: {0}".format(target))
    if target_argv is None:
        if target != "failure-sites" or historical:
            raise CaptureError("non-default authority targets require a -- boundary")
        target_argv = cleaned
    repo = _repository_from_arguments(cleaned if cleaned else target_argv)
    if target != "failure-sites" and "--repo" not in cleaned and not any(
        value.startswith("--repo=") for value in cleaned
    ):
        raise CaptureError("non-default authority targets require launcher --repo")
    if historical:
        if target not in (
            "failure-flows-v2",
            "failure-contract-review-v2",
            "failure-semantics-v3",
            "failure-contract-review-v3",
        ):
            raise CaptureError(
                "historical authority mode is limited to v2/v3 replay targets"
            )
        if "--historical-ef58" not in target_argv:
            raise CaptureError("historical authority target omits --historical-ef58")
    return repo, target, target_argv, historical


def isolated_authority_main(argv=None, expected_head=None):
    """Validate origins, then execute one checker or test from captured bytes."""

    trusted_type = type
    trusted_int_type = int
    try:
        repo, target, target_argv, historical = parse_authority_entry_arguments(
            argv or sys.argv[1:]
        )
        repo = resolved(repo)
        expected_head = exact_expected_head(expected_head)
        require_isolated_authority_runtime(repo)
        if git_head(repo) != expected_head:
            raise CaptureError(
                "repository HEAD differs from bootstrap expected commit"
            )
        if historical:
            historical_head, snapshots = committed_authority_module_snapshots(
                repo, expected_head
            )
            repository_authority = None
        else:
            repository_authority = capture_repository_authority(
                repo, expected_head=expected_head
            )
            historical_head = None
            snapshots = repository_authority["main_snapshots"]
        finder, original_path = _prepare_authority_imports(repo, snapshots)
        try:
            result = _run_authority_target(
                target, target_argv, repository_authority
            )
            if (
                trusted_type(result) is not trusted_int_type
                or result < 0
                or result > 255
            ):
                raise CaptureError("authority target returned an invalid exit status")
        finally:
            _restore_authority_imports(finder, original_path)
            if repository_authority is not None:
                recheck_repository_authority(repo, repository_authority)
            elif git_head(repo) != historical_head or historical_head != expected_head:
                raise CaptureError("repository HEAD changed during historical replay")
        return result
    except CaptureError as exc:
        print("host-module authority bootstrap failed: {0}".format(exc), file=sys.stderr)
        return 2


def authority_source_snapshot(authority, source_rel):
    if source_rel.startswith("ihk/"):
        snapshot = authority["ihk_snapshots"].get(source_rel[len("ihk/") :])
    else:
        snapshot = authority["main_snapshots"].get(source_rel)
    if snapshot is None:
        raise CaptureError("effective source is outside fresh authority: {0}".format(source_rel))
    return snapshot


def unfold_make_lines(text):
    # Kbuild writes physical continuations with a backslash immediately before
    # the newline.  Preserve all other backslashes for shlex to interpret.
    return re.sub(r"\\\r?\n[ \t]*", " ", text)


def reject_shell_expansion(value, label):
    if "\x00" in value or "\n" in value or "\r" in value:
        raise CaptureError("{0} contains a control character".format(label))
    for spelling in ("`", "$(", "${", "<(", ">("):
        if spelling in value:
            raise CaptureError("{0} contains forbidden shell expansion {1!r}".format(label, spelling))
    if "$" in value:
        raise CaptureError("{0} contains an unresolved shell variable".format(label))


def shell_words(value, label):
    reject_shell_expansion(value, label)
    try:
        lexer = shlex.shlex(value, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError as exc:
        raise CaptureError("cannot parse {0}: {1}".format(label, exc))


def parse_kbuild_cmd_bytes(data, display_path="<memory>"):
    """Return one safely tokenized compiler command and declared source."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CaptureError("{0} is not UTF-8: {1}".format(display_path, exc))
    if len(data) > 4 * 1024 * 1024:
        raise CaptureError("{0} is implausibly large".format(display_path))

    assignments = {"cmd": {}, "source": {}}
    for line in unfold_make_lines(text).splitlines():
        match = ASSIGNMENT_PATTERN.match(line)
        if not match:
            continue
        kind = match.group("kind")
        key = match.group("key").strip()
        if key in assignments[kind]:
            raise CaptureError("duplicate {0}_{1} assignment in {2}".format(kind, key, display_path))
        assignments[kind][key] = match.group("value").strip()

    if len(assignments["cmd"]) != 1:
        raise CaptureError("{0} must contain exactly one cmd_ assignment".format(display_path))
    key, command_text = next(iter(assignments["cmd"].items()))
    if key not in assignments["source"]:
        raise CaptureError("{0} has no source_ assignment matching cmd_{1}".format(display_path, key))
    if len(assignments["source"]) != 1:
        raise CaptureError("{0} must contain exactly one source_ assignment".format(display_path))

    source_words = shell_words(assignments["source"][key], "source_ assignment")
    if len(source_words) != 1 or source_words[0] in CONTROL_TOKENS:
        raise CaptureError("{0} source_ assignment is not one literal path".format(display_path))

    all_words = shell_words(command_text, "cmd_ assignment")
    if not all_words:
        raise CaptureError("{0} has an empty cmd_ assignment".format(display_path))
    split_at = len(all_words)
    separator = None
    for index, word in enumerate(all_words):
        if word in COMPILE_SEPARATORS:
            split_at = index
            separator = word
            break
        if word in CONTROL_TOKENS:
            raise CaptureError("compiler command in {0} contains redirection".format(display_path))
    if separator not in (None, ";"):
        raise CaptureError("compiler command in {0} is joined with {1!r}".format(display_path, separator))
    compiler_argv = all_words[:split_at]
    suffix = all_words[split_at:]
    if len(compiler_argv) < 2:
        raise CaptureError("compiler command in {0} is incomplete".format(display_path))
    if compiler_argv[0].startswith("-") or "=" in compiler_argv[0]:
        raise CaptureError("compiler executable in {0} is not literal".format(display_path))
    for word in compiler_argv:
        if word.startswith("@"):
            raise CaptureError("compiler response files are not captured: {0}".format(word))

    return {
        "assignment_key": key,
        "command_text_sha256": sha256_bytes(command_text.encode("utf-8")),
        "compile_argv": compiler_argv,
        "declared_source": source_words[0],
        "post_compile_token_count": len(suffix),
        "post_compile_tokens_sha256": sha256_bytes(canonical_bytes(suffix)),
    }


def parse_recorded_compile_argv_bytes(data, display_path="<memory>"):
    """Parse the exact argv recorded for the custom Rust compilation."""

    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CaptureError(
            "cannot parse recorded compiler argv {0}: {1}".format(display_path, exc)
        )
    if not isinstance(value, list) or len(value) < 2:
        raise CaptureError(
            "{0} must contain one non-empty compiler argv array".format(display_path)
        )
    for index, word in enumerate(value):
        if not isinstance(word, str) or not word or "\x00" in word:
            raise CaptureError(
                "{0} has an invalid argv element at {1}".format(display_path, index)
            )
        if word in CONTROL_TOKENS:
            raise CaptureError("{0} contains a shell control token".format(display_path))
    return value


def parse_kbuild_cmd(path):
    digest, data = file_digest(path)
    parsed = parse_kbuild_cmd_bytes(data, str(path))
    parsed["file"] = digest
    return parsed


def path_from_command(value, cwd):
    path = Path(value)
    if not path.is_absolute():
        path = cwd / path
    return resolved(path)


def verify_command_source(command, expected_source, cwd, display_path):
    declared = path_from_command(command["declared_source"], cwd)
    expected = resolved(expected_source)
    if declared != expected:
        raise CaptureError(
            "source_ assignment in {0} names {1}, expected {2}".format(display_path, declared, expected)
        )

    matches = []
    for index, word in enumerate(command["compile_argv"][1:], 1):
        if word.startswith("-"):
            continue
        try:
            candidate = path_from_command(word, cwd)
        except CaptureError:
            continue
        if candidate == expected:
            matches.append(index)
    if len(matches) != 1:
        raise CaptureError(
            "compiler command in {0} contains the effective source {1} times".format(
                display_path, len(matches)
            )
        )
    return matches[0]


def compiler_provenance(executable, environment=None):
    environment = environment or os.environ
    if os.path.isabs(executable):
        invoked = Path(executable)
    else:
        found = shutil.which(executable, path=environment.get("PATH"))
        if not found:
            raise CaptureError("compiler executable is unavailable: {0}".format(executable))
        invoked = Path(found)
    launcher = resolved(invoked)
    if not launcher.is_file():
        raise CaptureError("compiler executable is not a regular file: {0}".format(launcher))
    actual = launcher
    version_first_line = None
    version_stderr_sha256 = None
    version_stdout_sha256 = None
    if invoked.name == "rustc":
        try:
            sysroot_result = subprocess.run(
                [str(invoked), "--print", "sysroot"],
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            version_result = subprocess.run(
                [str(invoked), "-Vv"],
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CaptureError("cannot resolve rustc provenance: {0}".format(exc))
        if sysroot_result.returncode != 0 or version_result.returncode != 0:
            raise CaptureError("recorded rustc cannot report its sysroot and version")
        sysroot_text = sysroot_result.stdout.decode("utf-8", errors="strict").strip()
        if not sysroot_text or "\n" in sysroot_text or "\r" in sysroot_text:
            raise CaptureError("recorded rustc returned an invalid sysroot")
        actual = resolved(Path(sysroot_text) / "bin/rustc")
        if not actual.is_file():
            raise CaptureError("rustc sysroot compiler is missing: {0}".format(actual))
        version_lines = version_result.stdout.decode("utf-8", errors="replace").splitlines()
        if not version_lines:
            raise CaptureError("recorded rustc returned no version output")
        version_first_line = version_lines[0]
        version_stdout_sha256 = sha256_bytes(version_result.stdout)
        version_stderr_sha256 = sha256_bytes(version_result.stderr)
    else:
        try:
            version_result = subprocess.run(
                [str(launcher), "--version"],
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CaptureError("cannot capture compiler version: {0}".format(exc))
        version_lines = version_result.stdout.decode("utf-8", errors="replace").splitlines()
        if version_result.returncode != 0 or not version_lines:
            raise CaptureError("recorded compiler cannot report its version")
        version_first_line = version_lines[0]
        version_stdout_sha256 = sha256_bytes(version_result.stdout)
        version_stderr_sha256 = sha256_bytes(version_result.stderr)

    digest, _ = file_digest(actual)
    result = {
        "invoked_as": executable,
        "resolved_path": str(actual),
        "bytes": digest["bytes"],
        "sha256": digest["sha256"],
        "version_first_line": version_first_line,
        "version_stderr_sha256": version_stderr_sha256,
        "version_stdout_sha256": version_stdout_sha256,
    }
    if launcher != actual:
        launcher_digest, _ = file_digest(launcher)
        result["launcher"] = {
            "bytes": launcher_digest["bytes"],
            "resolved_path": str(launcher),
            "sha256": launcher_digest["sha256"],
        }
    return result


def reconstruct_preprocess_argv(command, source_index):
    """Turn the recorded compilation argv into a read-only preprocessing argv."""

    original = command["compile_argv"]
    result = [original[0]]
    source_word = original[source_index]
    index = 1
    while index < len(original):
        word = original[index]
        if index == source_index:
            index += 1
            continue
        if word in ("-c", "-S", "-E", "-fdirectives-only") or word in DEPENDENCY_FLAGS:
            index += 1
            continue
        if word in DEPENDENCY_VALUE_FLAGS or word in OUTPUT_VALUE_FLAGS:
            if index + 1 >= len(original):
                raise CaptureError("compiler flag {0} lacks its value".format(word))
            index += 2
            continue
        if any(word.startswith(flag) and word != flag for flag in DEPENDENCY_VALUE_FLAGS):
            index += 1
            continue
        if word.startswith("-o") and word != "-o":
            index += 1
            continue
        if word.startswith("--output="):
            index += 1
            continue
        if word.startswith("-Wp,-MD,") or word.startswith("-Wp,-MMD,"):
            index += 1
            continue
        result.append(word)
        index += 1

    result.extend(("-E", "-fdirectives-only", source_word))
    if result.count("-E") != 1 or result.count("-fdirectives-only") != 1:
        raise CaptureError("preprocessing mode reconstruction is ambiguous")
    for forbidden in ("-c", "-S", "-o", "--output"):
        if forbidden in result:
            raise CaptureError("preprocessing argv retains output flag {0}".format(forbidden))
    return result


def run_preprocessor(argv, cwd, environment=None):
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("preprocessor invocation failed: {0}".format(exc))
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        raise CaptureError(
            "preprocessor exited {0}: {1}".format(completed.returncode, stderr.strip())
        )
    if not completed.stdout:
        raise CaptureError("preprocessor produced no output")
    if len(completed.stdout) > 256 * 1024 * 1024:
        raise CaptureError("preprocessor output exceeds 256 MiB")
    return completed.stdout, completed.stderr


def unescape_marker_filename(value):
    output = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            following = value[index + 1]
            if following in ('"', "\\"):
                output.append(following)
                index += 2
                continue
        output.append(value[index])
        index += 1
    return "".join(output)


def marker_path(filename, cwd):
    if filename.startswith("<") and filename.endswith(">"):
        return None
    path = Path(filename)
    if not path.is_absolute():
        path = cwd / path
    return resolved(path)


def filter_target_lines(preprocessed, target_source, cwd):
    """Return ``(source line, emitted text)`` rows for one effective source."""

    text = preprocessed.decode("utf-8", errors="surrogateescape")
    target = resolved(target_source)
    current_path = None
    current_line = 1
    seen_marker = False
    rows = []
    for output_line in text.splitlines(keepends=True):
        marker = LINE_MARKER_PATTERN.match(output_line.rstrip("\r\n"))
        if marker:
            current_line = int(marker.group("line"))
            filename = unescape_marker_filename(marker.group("file"))
            current_path = marker_path(filename, cwd)
            if current_path == target:
                seen_marker = True
            continue
        if current_path == target:
            rows.append((current_line, output_line))
        current_line += 1
    if not seen_marker:
        raise CaptureError("preprocessor output has no line marker for {0}".format(target))
    if not rows:
        raise CaptureError("preprocessor emitted no active target lines for {0}".format(target))
    return rows


def mask_non_code(text, language):
    """Blank comments and literals while preserving byte positions/newlines."""

    chars = list(text)
    length = len(text)

    def blank(start, end):
        for offset in range(start, end):
            if chars[offset] not in ("\n", "\r"):
                chars[offset] = " "

    index = 0
    while index < length:
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            if end < 0:
                end = length
            blank(index, end)
            index = end
            continue
        if text.startswith("/*", index):
            depth = 1
            end = index + 2
            while end < length and depth:
                if language == "rust" and text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            if depth:
                raise CaptureError("unterminated block comment in {0} input".format(language))
            blank(index, end)
            index = end
            continue

        if language == "rust":
            raw = re.match(r"(?:br|rb|r)(?P<hashes>#{0,255})\"", text[index:])
            if raw:
                hashes = raw.group("hashes")
                terminator = '"' + hashes
                end = text.find(terminator, index + raw.end())
                if end < 0:
                    raise CaptureError("unterminated Rust raw string")
                end += len(terminator)
                blank(index, end)
                index = end
                continue

        prefix_length = 0
        if language == "rust" and text.startswith('b"', index):
            prefix_length = 1
        if text[index + prefix_length : index + prefix_length + 1] == '"':
            end = index + prefix_length + 1
            escaped = False
            while end < length:
                char = text[end]
                end += 1
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    break
            else:
                raise CaptureError("unterminated string literal in {0} input".format(language))
            blank(index, end)
            index = end
            continue

        if text[index] == "'":
            # Treat a quote as a character literal only when a closing quote is
            # nearby.  This avoids consuming Rust lifetimes such as ``'a``.
            end = index + 1
            escaped = False
            closing = None
            while end < min(length, index + 16) and text[end] not in "\r\n":
                char = text[end]
                end += 1
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == "'":
                    closing = end
                    break
            if closing is not None:
                blank(index, closing)
                index = closing
                continue
        index += 1
    return "".join(chars)


def rows_digest(rows):
    normalized = [
        {"line": line, "text": text}
        for line, text in rows
    ]
    return sha256_bytes(canonical_bytes(normalized))


def resolve_spliced_c_token(text, logical_line, column, expression):
    """Resolve a token in one phase-2 C logical line to physical source.

    GCC's ``-E -fdirectives-only`` output applies backslash-newline splicing.
    Consequently a token physically written on (for example) line 79 of a
    continued macro definition can be reported on logical line 68 at a large
    column.  Keep that compiler identity intact while exposing the physical
    spelling as an alias; callers must not mistake the alias for a macro
    expansion or a unique owning function.
    """

    if not isinstance(text, str):
        raise CaptureError("C source text must be a string")
    if (
        not isinstance(logical_line, int)
        or isinstance(logical_line, bool)
        or logical_line < 1
        or not isinstance(column, int)
        or isinstance(column, bool)
        or column < 1
        or not isinstance(expression, str)
        or not expression
        or "\n" in expression
        or "\r" in expression
    ):
        raise CaptureError("logical C token location is malformed")

    physical_lines = text.splitlines(keepends=True)
    index = 0
    while index < len(physical_lines):
        start_line = index + 1
        logical = []
        physical_positions = []
        while index < len(physical_lines):
            raw = physical_lines[index]
            physical_line = index + 1
            if raw.endswith("\\\r\n"):
                content = raw[:-3]
                continued = True
            elif raw.endswith("\\\n"):
                content = raw[:-2]
                continued = True
            else:
                content = raw.rstrip("\r\n")
                continued = False
            logical.append(content)
            physical_positions.extend(
                (physical_line, physical_column)
                for physical_column in range(1, len(content) + 1)
            )
            index += 1
            if not continued:
                break

        if start_line != logical_line:
            continue
        logical_text = "".join(logical)
        offset = column - 1
        if logical_text[offset : offset + len(expression)] != expression:
            # ``-fdirectives-only`` can normalize whitespace inside a retained
            # directive after phase-2 splicing.  The compiler column is still
            # authoritative for HFS identity, but a unique spelling in the
            # same logical source row is sufficient to bind its physical alias.
            matches = [
                match.start()
                for match in re.finditer(re.escape(expression), logical_text)
            ]
            if len(matches) != 1:
                raise CaptureError(
                    "logical C token does not match a unique source spelling "
                    "at {0}:{1}".format(logical_line, column)
                )
            offset = matches[0]
        if offset + len(expression) > len(physical_positions):
            raise CaptureError("logical C token has no complete physical spelling")
        start = physical_positions[offset]
        end = physical_positions[offset + len(expression) - 1]
        macro = re.match(
            r"^\s*#\s*define\s+([A-Za-z_]\w*)", logical_text
        )
        return {
            "expression": expression,
            "logical_column": column,
            "logical_line": logical_line,
            "macro_name": macro.group(1) if macro else None,
            "physical_column": start[1],
            "physical_end_column": end[1] + 1,
            "physical_line": start[0],
            "source_logical_column": offset + 1,
        }

    raise CaptureError(
        "logical C line {0} is not a source-row boundary".format(logical_line)
    )


def scan_rows(module, language, source_rel, source_sha256, active_sha256, rows):
    combined = "".join(text for _, text in rows)
    masked = mask_non_code(combined, language)
    starts = []
    position = 0
    for _, text in rows:
        starts.append(position)
        position += len(text)

    sites = []
    for match in ERRNO_PATTERN.finditer(masked):
        row_index = bisect.bisect_right(starts, match.start()) - 1
        if row_index < 0:
            raise CaptureError("cannot map failure-site offset to source line")
        line_number, line_text = rows[row_index]
        column = match.start() - starts[row_index] + 1
        errno = match.group(1)
        identity = {
            "column": column,
            "errno": errno,
            "language": language,
            "line": line_number,
            "module": module,
            "source": source_rel,
            "source_sha256": source_sha256,
        }
        identity_sha256 = sha256_bytes(canonical_bytes(identity))
        sites.append(
            {
                "active_source_sha256": active_sha256,
                "classification": "explicit_negative_errno_token",
                "column": column,
                "end_column": column + (match.end() - match.start()),
                "errno": errno,
                "expression": combined[match.start() : match.end()],
                "id": "HFS-" + identity_sha256[:24].upper(),
                "identity_sha256": identity_sha256,
                "language": language,
                "line": line_number,
                "line_sha256": sha256_bytes(line_text.encode("utf-8", errors="surrogateescape")),
                "module": module,
                "source": source_rel,
                "source_sha256": source_sha256,
            }
        )
    ids = [site["id"] for site in sites]
    if len(ids) != len(set(ids)):
        raise CaptureError("duplicate stable failure-site identity in {0}".format(source_rel))
    return sites


def config_provenance(kernel_dir, explicit_config=None):
    primary = explicit_config or (kernel_dir / ".config")
    primary = resolved(primary)
    if not primary.is_file():
        raise CaptureError("kernel configuration is missing: {0}".format(primary))
    generated = resolved(kernel_dir / "include/generated/autoconf.h")
    if not generated.is_file():
        raise CaptureError("generated kernel configuration is missing: {0}".format(generated))

    paths = [primary, generated]
    optional = resolved(kernel_dir / "include/config/auto.conf")
    if optional.is_file():
        paths.append(optional)
    records = []
    for path in paths:
        digest, _ = file_digest(path)
        try:
            name = str(path.relative_to(resolved(kernel_dir)))
        except ValueError:
            name = str(path)
        records.append({"path": name, "bytes": digest["bytes"], "sha256": digest["sha256"]})
    records.sort(key=lambda item: item["path"])
    return {
        "files": records,
        "primary_sha256": file_digest(primary)[0]["sha256"],
        "sha256": sha256_bytes(canonical_bytes(records)),
    }


def capture_c_source(
    module,
    source_rel,
    cmd_rel,
    repo,
    build_dir,
    kernel_dir,
    config,
    environment=None,
    source_snapshot=None,
):
    source = repo / source_rel
    command_path = build_dir / cmd_rel
    require_within(source, repo, "effective source")
    require_within(command_path, build_dir, "Kbuild command file")
    if command_path.is_symlink() or not command_path.is_file():
        raise CaptureError("required Kbuild command file is missing or not regular: {0}".format(command_path))
    if source_snapshot is None:
        source_digest, _ = file_digest(source)
    else:
        if source_snapshot.get("path") not in (source_rel, source_rel[len("ihk/") :] if source_rel.startswith("ihk/") else source_rel):
            raise CaptureError("fresh C source snapshot path differs: {0}".format(source_rel))
        source_digest = {
            "bytes": len(source_snapshot["data"]),
            "sha256": source_snapshot["sha256"],
        }
    command = parse_kbuild_cmd(command_path)
    source_index = verify_command_source(command, source, kernel_dir, command_path)
    preprocess_argv = reconstruct_preprocess_argv(command, source_index)
    compiler = compiler_provenance(preprocess_argv[0], environment)
    output, stderr = run_preprocessor(preprocess_argv, kernel_dir, environment)
    rows = filter_target_lines(output, source, kernel_dir)
    active_sha256 = rows_digest(rows)
    sites = scan_rows(module, "c", source_rel, source_digest["sha256"], active_sha256, rows)

    record = {
        "active_target_line_count": len(rows),
        "command_file": cmd_rel,
        "compile_argv": command["compile_argv"],
        "digests": {
            "command_file_sha256": command["file"]["sha256"],
            "compiler_sha256": compiler["sha256"],
            "config_sha256": config["sha256"],
            "effective_source_sha256": source_digest["sha256"],
            "preprocessed_sha256": sha256_bytes(output),
            "preprocessor_stderr_sha256": sha256_bytes(stderr),
            "preprocessing_argv_sha256": sha256_bytes(canonical_bytes(preprocess_argv)),
            "target_preprocessed_sha256": active_sha256,
        },
        "failure_site_count": len(sites),
        "language": "c",
        "module": module,
        "post_compile_token_count": command["post_compile_token_count"],
        "post_compile_tokens_sha256": command["post_compile_tokens_sha256"],
        "preprocess_argv": preprocess_argv,
        "preprocessor": compiler,
        "source": source_rel,
    }
    return record, sites


def capture_rust_source(
    module,
    source_rel,
    cmd_rel,
    repo,
    build_dir,
    kernel_dir,
    config,
    environment=None,
    source_snapshot=None,
):
    source = repo / source_rel
    command_path = build_dir / cmd_rel
    require_within(source, repo, "effective Rust source")
    require_within(command_path, build_dir, "Rust command file")
    if command_path.is_symlink() or not command_path.is_file():
        raise CaptureError("required Rust command file is missing or not regular: {0}".format(command_path))
    if source_snapshot is None:
        source_digest, source_data = file_digest(source)
    else:
        if source_snapshot.get("path") not in (source_rel, source_rel[len("ihk/") :] if source_rel.startswith("ihk/") else source_rel):
            raise CaptureError("fresh Rust source snapshot path differs: {0}".format(source_rel))
        source_data = source_snapshot["data"]
        source_digest = {
            "bytes": len(source_data),
            "sha256": source_snapshot["sha256"],
        }
    try:
        source_text = source_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CaptureError("Rust helper is not UTF-8: {0}".format(exc))
    if re.search(r"#\s*\[\s*cfg\b|\bcfg!\s*\(", source_text):
        raise CaptureError(
            "Rust helper contains conditional compilation; capture expanded Rust input first"
        )
    command = parse_kbuild_cmd(command_path)
    verify_command_source(command, source, kernel_dir, command_path)
    recorded_argv_path = command_path.with_name(command_path.name + ".argv.json")
    if recorded_argv_path.is_symlink() or not recorded_argv_path.is_file():
        raise CaptureError(
            "exact Rust compiler argv capture is missing or not regular: {0}".format(
                recorded_argv_path
            )
        )
    recorded_argv_digest, recorded_argv_data = file_digest(recorded_argv_path)
    recorded_argv = parse_recorded_compile_argv_bytes(
        recorded_argv_data, str(recorded_argv_path)
    )
    source_indexes = [
        index
        for index, word in enumerate(recorded_argv)
        if path_from_command(word, kernel_dir) == resolved(source)
    ]
    if len(source_indexes) != 1:
        raise CaptureError(
            "recorded Rust compiler argv contains the effective source {0} times".format(
                len(source_indexes)
            )
        )
    command_compiler = compiler_provenance(command["compile_argv"][0], environment)
    compiler = compiler_provenance(recorded_argv[0], environment)
    for field in ("resolved_path", "sha256"):
        if command_compiler[field] != compiler[field]:
            raise CaptureError(
                "Rust .cmd and exact argv name different compiler identities"
            )
    rows = list(enumerate(source_text.splitlines(keepends=True), 1))
    if not rows:
        raise CaptureError("Rust helper source is empty")
    active_sha256 = rows_digest(rows)
    sites = scan_rows(module, "rust", source_rel, source_digest["sha256"], active_sha256, rows)
    record = {
        "active_target_line_count": len(rows),
        "command_file": cmd_rel,
        "compile_argv": recorded_argv,
        "digests": {
            "command_file_sha256": command["file"]["sha256"],
            "compiler_sha256": compiler["sha256"],
            "config_sha256": config["sha256"],
            "effective_source_sha256": source_digest["sha256"],
            "preprocessed_sha256": source_digest["sha256"],
            "preprocessing_argv_sha256": sha256_bytes(canonical_bytes([])),
            "recorded_compile_argv_file_sha256": recorded_argv_digest["sha256"],
            "recorded_compile_argv_sha256": sha256_bytes(canonical_bytes(recorded_argv)),
            "target_preprocessed_sha256": active_sha256,
        },
        "failure_site_count": len(sites),
        "language": "rust",
        "module": module,
        "post_compile_token_count": command["post_compile_token_count"],
        "post_compile_tokens_sha256": command["post_compile_tokens_sha256"],
        "preprocess_argv": [],
        "preprocessing_mode": "exact Rust source; no C preprocessing",
        "recorded_compile_argv_file": str(
            Path(cmd_rel).with_name(Path(cmd_rel).name + ".argv.json")
        ),
        "recorded_compiler": compiler,
        "simplified_command_compiler": command_compiler,
        "source": source_rel,
    }
    return record, sites


def git_head(repo):
    value = run_git(repo, ["rev-parse", "HEAD"], "resolve repository commit")
    value = value.decode("ascii", errors="replace").strip()
    if not re.match(r"^[0-9a-f]{40}$", value):
        raise CaptureError("cannot resolve exact repository commit")
    return value


def build_capture(
    repo,
    build_dir,
    kernel_dir,
    explicit_config=None,
    environment=None,
    repository_authority=None,
):
    repo = resolved(repo)
    build_dir = resolved(build_dir)
    kernel_dir = resolved(kernel_dir)
    if not repo.is_dir() or not build_dir.is_dir() or not kernel_dir.is_dir():
        raise CaptureError("repo, build directory, and kernel directory must exist")
    authority = repository_authority or capture_repository_authority(repo)
    if authority.get("repo") != str(repo):
        raise CaptureError("fresh repository authority belongs to another checkout")
    if git_head(repo) != authority.get("main_head") or git_head(repo / "ihk") != authority.get("ihk_head"):
        raise CaptureError("repository HEAD differs from fresh authority snapshot")
    config = config_provenance(kernel_dir, explicit_config)
    overlay_path = repo / "scripts/patches/ihk-linux-compat.patch"
    inventory_path = repo / "host-kernel/reference/legacy-host-modules-f2eb7352.json"
    overlay_snapshot = authority["main_snapshots"].get(
        "scripts/patches/ihk-linux-compat.patch"
    )
    inventory_snapshot = authority["main_snapshots"].get(
        "host-kernel/reference/legacy-host-modules-f2eb7352.json"
    )
    if overlay_snapshot is None or inventory_snapshot is None:
        raise CaptureError("fresh authority omits overlay or inventory")
    sources = []
    sites = []
    for module, language, source_rel, cmd_rel in EXPECTED_SOURCES:
        source_snapshot = authority_source_snapshot(authority, source_rel)
        if language == "c":
            record, found = capture_c_source(
                module,
                source_rel,
                cmd_rel,
                repo,
                build_dir,
                kernel_dir,
                config,
                environment,
                source_snapshot,
            )
        else:
            record, found = capture_rust_source(
                module,
                source_rel,
                cmd_rel,
                repo,
                build_dir,
                kernel_dir,
                config,
                environment,
                source_snapshot,
            )
        sources.append(record)
        sites.extend(found)

    sites.sort(key=lambda item: (item["module"], item["source"], item["line"], item["column"], item["errno"]))
    ids = [site["id"] for site in sites]
    if len(ids) != len(set(ids)):
        raise CaptureError("stable failure-site IDs collide across sources")
    expected_modules = {entry[0] for entry in EXPECTED_SOURCES}
    observed_modules = {site["module"] for site in sites}
    if observed_modules != expected_modules:
        raise CaptureError(
            "failure-site capture lost a module: observed={0}, expected={1}".format(
                sorted(observed_modules), sorted(expected_modules)
            )
        )

    by_module = {}
    by_language = {}
    by_errno = {}
    for site in sites:
        by_module[site["module"]] = by_module.get(site["module"], 0) + 1
        by_language[site["language"]] = by_language.get(site["language"], 0) + 1
        by_errno[site["errno"]] = by_errno.get(site["errno"], 0) + 1
    capture = {
        "coverage": {
            "by_errno": dict(sorted(by_errno.items())),
            "by_language": dict(sorted(by_language.items())),
            "by_module": dict(sorted(by_module.items())),
            "failure_site_count": len(sites),
            "source_count": len(sources),
        },
        "failure_sites": sites,
        "generator": "scripts/host_module_failure_sites.py",
        "kernel_configuration": config,
        "profile": PROFILE,
        "provenance": {
            "compatibility_overlay": {
                "path": str(overlay_path.relative_to(repo)),
                "sha256": overlay_snapshot["sha256"],
            },
            "frozen_inventory": {
                "path": str(inventory_path.relative_to(repo)),
                "sha256": inventory_snapshot["sha256"],
            },
            "ihk_commit": authority["ihk_head"],
            "repository_commit": authority["main_head"],
        },
        "schema_version": SCHEMA_VERSION,
        "sources": sources,
    }
    recheck_repository_authority(repo, authority)
    return capture


def write_capture(path, capture):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(capture, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, str(path))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--kernel-dir", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--check-repository-authority",
        action="store_true",
        help="verify HEAD plus the exact committed IHK compatibility overlay",
    )
    args = parser.parse_args(argv)
    if not args.check_repository_authority and (
        args.build_dir is None or args.kernel_dir is None or args.output is None
    ):
        parser.error("--build-dir, --kernel-dir, and --output are required for capture")
    return args


def main(argv=None, repository_authority=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        if repository_authority is None:
            raise CaptureError(
                "fresh CLI requires the isolated repository-authority bootstrap"
            )
        if args.check_repository_authority:
            recheck_repository_authority(args.repo, repository_authority)
            print(
                "verified fresh repository authority at {0} with IHK {1} plus exact overlay".format(
                    repository_authority["main_head"],
                    repository_authority["ihk_head"],
                )
            )
            return 0
        capture = build_capture(
            args.repo,
            args.build_dir,
            args.kernel_dir,
            args.config,
            repository_authority=repository_authority,
        )
        write_capture(args.output, capture)
    except CaptureError as exc:
        print("host-module failure-site capture failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(
        "captured {0} active failure sites from {1} host-module sources".format(
            capture["coverage"]["failure_site_count"], capture["coverage"]["source_count"]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(isolated_authority_main())
