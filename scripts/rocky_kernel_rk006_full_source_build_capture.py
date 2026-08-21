#!/usr/bin/env python3
"""Capture a non-crediting full-source RK-006 replay and exact-build binding."""

from __future__ import print_function

import argparse
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile


CONTRACT_PATH = "host-kernel/rocky/evidence/rk006-full-source-build-capture-contract-v1.json"
AUTHORITY_PATH = "host-kernel/rocky/rk006-patch-authority-v1.json"
CAPTURE_SCRIPT_PATH = "scripts/rocky_kernel_rk006_full_source_build_capture.py"
CAPTURE_TEST_PATH = "scripts/tests/test_rocky_kernel_rk006_full_source_build_capture.py"
WORKFLOW_PATH = ".github/workflows/native-rust-host-modules-exact-build.yml"
WORKFLOW_TEST_PATH = "scripts/tests/test_native_rust_exact_build_workflow.py"
CAPTURE_MEMBER_MODE = 0o644
FULL_SOURCE_CLOSURE_ALGORITHM = "sha256-canonical-json-ordered-full-source-tree-rows-v1"

CONTAINER_IMAGE = (
    "rockylinux/rockylinux:10.2@sha256:"
    "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
)
CAPTURE_MEMBERS = [
    "SHA256SUMS",
    "build-binding.json",
    "capture.json",
    "patch-apply.log",
    "postimages.tar.xz",
    "preimages.tar.xz",
    "repository-inputs.tar.xz",
    "second-application.log",
    "tool-probes.json",
    "workflow-state",
]
REQUIRED_BUILD_MEMBERS = [
    "SHA256SUMS",
    "build-log.exit-code",
    "build.commands",
    "build.exit-code",
    "build.log",
    "build.phase",
    "built-module-artifacts.txt",
    "bzImage",
    "commit.sha",
    "ihk-smp-x86_64.ko",
    "ihk.ko",
    "kbuild-link-closure.json",
    "kconfig-solver-matrix.json",
    "kernel.release",
    "mcctrl.ko",
    "module-targets.txt",
    "resolved.config",
    "stage-lock.json",
    "workflow-state",
]
FALSE_CLAIMS = {
    "credit_eligible": False,
    "durable_archive": False,
    "external_replay_reviewed": False,
    "gate_complete": False,
    "independent_authorship_review_complete": False,
    "independent_license_review_complete": False,
    "independent_provenance_review_complete": False,
    "production_build_reviewed": False,
    "tracker_credit": False,
}
FALSE_GATE = {
    "credit_eligible": False,
    "gate_id": "RK-006",
    "points_awarded": 0,
    "status": "TODO",
    "tracker_credit": False,
}
REMAINING_BLOCKERS = [
    "This capture is machine-generated and has not received independent patch authorship, license, provenance, or semantic review.",
    "The patch authority still records unresolved authorship and license questions for repository overlays.",
    "GitHub Actions retains both referenced artifacts for only 30 days; neither is a durable immutable archive.",
    "A successful current-head build and capture do not themselves authorize RK-006, tracker credit, or any PASS transition.",
    "An independently reviewed result authority must bind the outer artifact digests before the gate can change.",
]
PARENT_FILES = [
    {
        "path": "drivers/misc/Kconfig",
        "postimage_sha256": "ed57d452061fb74e62d5dce3aa3680aec0b70811b87b57a25554dc4dd4c33e4a",
        "preimage_sha256": "679b6c945aebec04f936c184b724f1b0d6daa6d760ec3bb4d6b56db905c19683",
    },
    {
        "path": "drivers/misc/Makefile",
        "postimage_sha256": "548e7eed491c9287908870a4783be57c15a360f03ecc68a4c4856e7c5c51a74f",
        "preimage_sha256": "3f998f3c28cae01f8cb6e3b283f25175635ff2510ba40ce60235a3c059a9a238",
    },
]

LOCKED_PROBES = {
    "bindgen": {
        "command": ["bindgen", "--version", "workaround-for-0.69.0"],
        "owner": "bindgen-cli-0:0.72.1-1.el10.x86_64",
        "path": "/usr/bin/bindgen",
        "sha256": "55880234cb76e4fd13f7401308c61db687301624be48adfd23c3c2cd0797b37c",
        "stdout_sha256": "c68f981ca03a0733ae2e550a898e2f08d334fd8ece4e9e3b99ea6fa3b8ba21c4",
    },
    "clang": {
        "command": ["clang", "--version"],
        "owner": "clang-0:21.1.8-1.el10.x86_64",
        "path": "/usr/bin/clang",
        "sha256": "48271e3fbb759560a54e6f0a13e05a4a0b768eea2ffd6aa2f1e14b8cbb76fb7f",
        "stdout_sha256": "082de0cf4ec79ce11472d754e6f9508fdc811c2d5c585e90fedcb0ef985b037a",
        "symlink_hops": [
            {"path": "/usr/bin/clang", "target": "clang-21"},
        ],
    },
    "lld": {
        "command": ["ld.lld", "--version"],
        "owner": "lld-0:21.1.8-1.el10.x86_64",
        "path": "/usr/bin/ld.lld",
        "sha256": "52029c7d731c74ab72a2eca8126d578547242b3192ba74e27c94c1b51be001f9",
        "stdout_sha256": "418d72df86baf70c88b9a96a9118e3cdc66be0537a58f66a6879df0479f9a78f",
        "symlink_hops": [
            {"path": "/usr/bin/ld.lld", "target": "lld"},
        ],
    },
    "llvm": {
        "command": ["llvm-config", "--version"],
        "owner": "llvm-devel-0:21.1.8-1.el10.x86_64",
        "path": "/usr/bin/llvm-config",
        "sha256": "bdf82677530a0997abccadea0d9ce6aa3146d5d542ded5b589a095e4121b3cf0",
        "stdout_sha256": "2aa7a88c6265f7d12bbbda0d91c617c37977ebba04971007a6ba09f16130f58c",
        "symlink_hops": [
            {
                "path": "/usr/bin/llvm-config",
                "target": "/etc/alternatives/llvm-config",
            },
            {
                "path": "/etc/alternatives/llvm-config",
                "target": "/usr/lib64/llvm21/bin/llvm-config",
            },
        ],
    },
    "pahole": {
        "command": ["pahole", "--version"],
        "owner": "dwarves-0:1.31-1.el10.x86_64",
        "path": "/usr/bin/pahole",
        "sha256": "099aa2c9d0f4d22cad3cf65a1dab89bfc11b500f568497a276eec0052b65398b",
        "stdout_sha256": "d68d5c09201c3f36d4d324c921c79161351a8ea4dc6e25b4d161ff40bae293e2",
    },
    "rustc": {
        "command": ["rustc", "--version", "--verbose"],
        "owner": "rust-0:1.92.0-1.el10.x86_64",
        "path": "/usr/bin/rustc",
        "sha256": "38eeb1652fb59753cb7736e354ec1579a543da9a2eb8a68be102a41e88eb5dc6",
        "stdout_sha256": "a8dc7b68607a44774c48c2a1fab52da313610a1573a160e87c480d386fdedc64",
    },
}
RUST_SRC_CORE = {
    "owner": "rust-src-0:1.92.0-1.el10.noarch",
    "path": "/usr/lib/rustlib/src/rust/library/core/src/lib.rs",
    "sha256": "38ed9003ea2427f8803317e3e040d69f988d88534468bb28cbf83f27e2b51080",
    "stdout_sha256": "c1b4ac7ed462cd01c076c33de7d01ddef7f39a4bed73b12b2d769babf57204e9",
}

CAPTURE_ENV = {
    "HOME": "/tmp/rk006-capture-home",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "TZ": "UTC",
}
CAPTURE_TOOL_PROBES = {
    "patch": {
        "command": ["patch", "--version"],
        "owner_regex": r"patch-[0-9]+:[0-9A-Za-z.+_~^]+-[0-9A-Za-z.+_~^]+\.x86_64",
        "path": "/usr/bin/patch",
        "resolved_path": "/usr/bin/patch",
        "version_regex": (
            r"GNU patch [0-9]+(?:\.[0-9]+)+(?:[^\r\n]*)?\n"
            r"(?:[^\x00\r]*\n)*"
        ),
    },
    "python3": {
        "command": ["python3", "--version"],
        "owner_regex": (
            r"python3-[0-9]+:3\.[0-9A-Za-z.+_~^]+-"
            r"[0-9A-Za-z.+_~^]+\.x86_64"
        ),
        "path": "/usr/bin/python3",
        "resolved_path": "/usr/bin/python3.12",
        "version_regex": (
            r"Python 3\.[0-9]+(?:\.[0-9]+)?(?:[0-9A-Za-z.+_~^-]*)?\n"
        ),
    },
}


class CaptureError(RuntimeError):
    """Raised when any capture boundary fails closed."""


def _reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise CaptureError("duplicate JSON key: {}".format(key))
        value[key] = item
    return value


def _load_json_bytes(data, label):
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except CaptureError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise CaptureError("{} is not canonical UTF-8 JSON: {}".format(label, exc))


def _canonical_json(value):
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _safe_relative(value, label):
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise CaptureError("{} is not a safe POSIX path".format(label))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise CaptureError("{} is not repository-relative".format(label))
    if str(path) != value:
        raise CaptureError("{} is not normalized".format(label))
    return path


def _safe_directory(path, label, create=False):
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw or "\x00" in raw or "\\" in raw:
        raise CaptureError("{} path is unsafe".format(label))
    requested = Path(os.path.abspath(raw))
    if create and not requested.exists():
        try:
            requested.mkdir(parents=True, mode=0o755)
        except OSError as exc:
            raise CaptureError("cannot create {}: {}".format(label, exc))
    current = Path(requested.anchor)
    for part in requested.parts[1:]:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise CaptureError("cannot inspect {}: {}".format(label, exc))
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise CaptureError("{} must traverse real directories".format(label))
    return requested


def _read_rooted(root, relative, label, allow_hardlink=False):
    rel = _safe_relative(relative, label)
    root = _safe_directory(root, label + " root")
    root_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        root_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        root_flags |= os.O_NOFOLLOW
    descriptors = []
    try:
        descriptor = os.open(str(root), root_flags)
        descriptors.append(descriptor)
        for part in rel.parts[:-1]:
            flags = os.O_RDONLY
            if hasattr(os, "O_DIRECTORY"):
                flags |= os.O_DIRECTORY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(part, flags, dir_fd=descriptor)
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                raise CaptureError("{} traverses a non-directory".format(label))
            descriptors.append(descriptor)
        flags = os.O_RDONLY
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(rel.parts[-1], flags, dir_fd=descriptors[-1])
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise CaptureError("{} is not a regular file".format(label))
        if not allow_hardlink and before.st_nlink != 1:
            raise CaptureError("{} is hard-linked".format(label))
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        identity = lambda item: (
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_nlink,
            item.st_size,
            getattr(item, "st_mtime_ns", int(item.st_mtime * 1000000000)),
            getattr(item, "st_ctime_ns", int(item.st_ctime * 1000000000)),
        )
        if identity(before) != identity(after):
            raise CaptureError("{} changed while it was read".format(label))
        data = b"".join(chunks)
        if len(data) != before.st_size:
            raise CaptureError("{} size changed while it was read".format(label))
        return data, before
    except CaptureError:
        raise
    except OSError as exc:
        raise CaptureError("cannot read {}: {}".format(label, exc))
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _read_explicit_file(path, label, allow_hardlink=False):
    candidate = Path(os.path.abspath(os.fspath(path)))
    if candidate.name in ("", ".", ".."):
        raise CaptureError("{} path is unsafe".format(label))
    return _read_rooted(candidate.parent, candidate.name, label, allow_hardlink)


def _metadata_identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
    )


def _locked_probe_absolute_path(value, label):
    if (
        type(value) is not str
        or not value
        or not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or "\x00" in value
    ):
        raise CaptureError("{} is not a safe absolute path".format(label))
    path = PurePosixPath(value)
    if (
        not path.is_absolute()
        or str(path) != value
        or len(path.parts) < 2
        or any(part in ("", ".", "..") for part in path.parts[1:])
    ):
        raise CaptureError("{} is not a normalized absolute path".format(label))
    return Path(value)


def _locked_probe_target_path(alias_path, target, label):
    if type(target) is not str or not target or "\\" in target or "\x00" in target:
        raise CaptureError("{} is unsafe".format(label))
    if target.startswith("/"):
        return _locked_probe_absolute_path(target, label)
    path = PurePosixPath(target)
    if (
        path.is_absolute()
        or str(path) != target
        or len(path.parts) != 1
        or path.parts[0] in ("", ".", "..")
    ):
        raise CaptureError("{} is not a safe basename".format(label))
    return alias_path.parent / target


def _locked_probe_hops(candidate, expected, label):
    if "symlink_target" in expected:
        raise CaptureError("{} uses the obsolete single-link policy".format(label))
    raw_hops = expected.get("symlink_hops")
    if raw_hops is None:
        if "symlink_hops" in expected:
            raise CaptureError("{} symlink-hop policy is invalid".format(label))
        return [], candidate
    if type(raw_hops) is not list or not raw_hops or len(raw_hops) > 8:
        raise CaptureError("{} symlink-hop policy is invalid".format(label))
    current = candidate
    seen = {str(candidate)}
    hops = []
    for index, raw_hop in enumerate(raw_hops):
        hop_label = "{} symlink hop {}".format(label, index)
        if type(raw_hop) is not dict or set(raw_hop) != {"path", "target"}:
            raise CaptureError("{} policy is invalid".format(hop_label))
        hop_path = _locked_probe_absolute_path(raw_hop["path"], hop_label + " path")
        if str(hop_path) != str(current):
            raise CaptureError("{} path is disconnected".format(hop_label))
        target_path = _locked_probe_target_path(
            hop_path, raw_hop["target"], hop_label + " target"
        )
        if str(target_path) in seen:
            raise CaptureError("{} forms a loop".format(hop_label))
        seen.add(str(target_path))
        hops.append(
            {
                "path": hop_path,
                "target": raw_hop["target"],
                "target_path": target_path,
            }
        )
        current = target_path
    return hops, current


def _open_locked_probe_parent(path, label):
    parent = _safe_directory(path, label)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = None
    try:
        named = parent.lstat()
        descriptor = os.open(str(parent), flags)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or _metadata_identity(opened) != _metadata_identity(named)
        ):
            raise CaptureError("{} identity differs".format(label))
        return {
            "fd": descriptor,
            "identity": _metadata_identity(opened),
            "path": str(parent),
        }
    except Exception:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _close_locked_probe(session):
    for key in ("target_fd", "target_parent_fd"):
        descriptor = session.get(key)
        session[key] = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    for hop in reversed(session.get("hops", [])):
        for key in ("alias_fd", "parent_fd"):
            descriptor = hop.get(key)
            hop[key] = None
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _open_locked_probe(path, expected, label):
    if (
        not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_PATH")
    ):
        raise CaptureError("no-follow locked-tool capture is unavailable")
    candidate = Path(os.path.abspath(os.fspath(path)))
    if candidate.name in ("", ".", ".."):
        raise CaptureError("{} path is unsafe".format(label))
    expected_hops, target_path = _locked_probe_hops(candidate, expected, label)
    session = {
        "hops": [],
        "target_fd": None,
        "target_parent_fd": None,
    }
    alias_flags = os.O_PATH | os.O_NOFOLLOW
    target_flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        alias_flags |= os.O_CLOEXEC
        target_flags |= os.O_CLOEXEC
    if hasattr(os, "O_BINARY"):
        target_flags |= os.O_BINARY
    try:
        for index, expected_hop in enumerate(expected_hops):
            hop_label = "{} symlink hop {}".format(label, index)
            parent = _open_locked_probe_parent(
                expected_hop["path"].parent, hop_label + " parent"
            )
            hop = {
                "alias_fd": None,
                "alias_identity": None,
                "alias_name": expected_hop["path"].name,
                "parent_fd": parent["fd"],
                "parent_identity": parent["identity"],
                "parent_path": parent["path"],
                "target": expected_hop["target"],
            }
            session["hops"].append(hop)
            alias_before = os.stat(
                hop["alias_name"], dir_fd=hop["parent_fd"], follow_symlinks=False
            )
            hop["alias_fd"] = os.open(
                hop["alias_name"], alias_flags, dir_fd=hop["parent_fd"]
            )
            alias_open = os.fstat(hop["alias_fd"])
            link_target = os.readlink(hop["alias_name"], dir_fd=hop["parent_fd"])
            alias_after = os.stat(
                hop["alias_name"], dir_fd=hop["parent_fd"], follow_symlinks=False
            )
            if (
                not stat.S_ISLNK(alias_open.st_mode)
                or _metadata_identity(alias_before) != _metadata_identity(alias_open)
                or _metadata_identity(alias_after) != _metadata_identity(alias_open)
                or link_target != hop["target"]
                or _metadata_identity(alias_before) != _metadata_identity(alias_after)
                or len(os.fsencode(link_target)) != alias_before.st_size
            ):
                raise CaptureError(
                    "{} target differs or changed".format(hop_label)
                )
            hop["alias_identity"] = _metadata_identity(alias_open)

        target_parent = _open_locked_probe_parent(
            target_path.parent, label + " target parent"
        )
        session["target_parent_fd"] = target_parent["fd"]
        session["target_parent_identity"] = target_parent["identity"]
        session["target_parent_path"] = target_parent["path"]
        session["target_name"] = target_path.name
        target_named_before = os.stat(
            session["target_name"],
            dir_fd=session["target_parent_fd"],
            follow_symlinks=False,
        )
        if stat.S_ISLNK(target_named_before.st_mode):
            raise CaptureError("{} has an unlisted symlink hop".format(label))
        if not stat.S_ISREG(target_named_before.st_mode):
            if expected_hops:
                raise CaptureError("{} target is not a regular file".format(label))
            raise CaptureError("{} logical path is not a regular file".format(label))
        session["target_fd"] = os.open(
            session["target_name"],
            target_flags,
            dir_fd=session["target_parent_fd"],
        )
        target_before = os.fstat(session["target_fd"])
        target_named_after = os.stat(
            session["target_name"],
            dir_fd=session["target_parent_fd"],
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(target_before.st_mode)
            or _metadata_identity(target_named_before) != _metadata_identity(target_before)
            or _metadata_identity(target_named_after) != _metadata_identity(target_before)
        ):
            raise CaptureError("{} target identity differs".format(label))
        chunks = []
        while True:
            chunk = os.read(session["target_fd"], 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        target_after = os.fstat(session["target_fd"])
        if _metadata_identity(target_after) != _metadata_identity(target_before):
            raise CaptureError("{} target changed while it was read".format(label))
        data = b"".join(chunks)
        if len(data) != target_before.st_size:
            raise CaptureError("{} target size changed while it was read".format(label))
        session.update(
            {
                "command_name": expected["command"][0],
                "data": data,
                "label": label,
                "logical_path": str(candidate),
                "target_identity": _metadata_identity(target_before),
            }
        )
        _recheck_locked_probe(session)
        return session
    except CaptureError:
        _close_locked_probe(session)
        raise
    except (KeyError, OSError) as exc:
        _close_locked_probe(session)
        raise CaptureError("cannot open {}: {}".format(label, exc))


def _recheck_locked_probe(session):
    label = session["label"]
    try:
        for index, hop in enumerate(session["hops"]):
            parent_open = os.fstat(hop["parent_fd"])
            parent_named = _safe_directory(
                hop["parent_path"],
                "{} symlink hop {} parent recheck".format(label, index),
            ).lstat()
            alias_open = os.fstat(hop["alias_fd"])
            alias_named = os.stat(
                hop["alias_name"],
                dir_fd=hop["parent_fd"],
                follow_symlinks=False,
            )
            link_target = os.readlink(
                hop["alias_name"], dir_fd=hop["parent_fd"]
            )
            if (
                _metadata_identity(parent_open) != hop["parent_identity"]
                or _metadata_identity(parent_named) != hop["parent_identity"]
                or _metadata_identity(alias_open) != hop["alias_identity"]
                or _metadata_identity(alias_named) != hop["alias_identity"]
                or link_target != hop["target"]
                or len(os.fsencode(link_target)) != alias_open.st_size
            ):
                raise CaptureError("{} path identity changed".format(label))
        target_parent_open = os.fstat(session["target_parent_fd"])
        target_parent_named = _safe_directory(
            session["target_parent_path"], label + " target parent recheck"
        ).lstat()
        target_open = os.fstat(session["target_fd"])
        target_named = os.stat(
            session["target_name"],
            dir_fd=session["target_parent_fd"],
            follow_symlinks=False,
        )
    except CaptureError:
        raise
    except (KeyError, OSError) as exc:
        raise CaptureError("cannot recheck {}: {}".format(label, exc))
    if (
        _metadata_identity(target_parent_open) != session["target_parent_identity"]
        or _metadata_identity(target_parent_named) != session["target_parent_identity"]
        or _metadata_identity(target_open) != session["target_identity"]
        or _metadata_identity(target_named) != session["target_identity"]
    ):
        raise CaptureError("{} path identity changed".format(label))
    resolved = shutil.which(session["command_name"], path=CAPTURE_ENV["PATH"])
    if resolved != session["logical_path"]:
        raise CaptureError("{} PATH resolution changed".format(label))


def _run_locked_probe(session, arguments):
    if (
        not arguments
        or not all(type(item) is str and item for item in arguments)
        or arguments[0] != session["command_name"]
    ):
        raise CaptureError("locked-tool command arguments are invalid")
    executable = "/proc/self/fd/{}".format(session["target_fd"])
    if not os.path.isdir("/proc/self/fd"):
        raise CaptureError("descriptor-bound execution is unavailable")
    try:
        os.lseek(session["target_fd"], 0, os.SEEK_SET)
        completed = subprocess.run(
            list(arguments),
            executable=executable,
            pass_fds=(session["target_fd"],),
            env=dict(CAPTURE_ENV),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1800,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("locked-tool command failed to execute: {}".format(exc))
    if completed.returncode:
        raise CaptureError(
            "locked-tool command failed ({}): {}".format(
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace")[-2000:],
            )
        )
    return completed


def _capture_locked_probe(path, expected, label):
    session = _open_locked_probe(path, expected, label)
    try:
        owner, owner_command = _rpm_owner(path)
        _recheck_locked_probe(session)
        completed = _run_locked_probe(session, expected["command"])
        _recheck_locked_probe(session)
        return {
            "binary_data": session["data"],
            "completed": completed,
            "owner": owner,
            "owner_command": owner_command,
        }
    finally:
        _close_locked_probe(session)


def _write_atomic(directory, name, data, mode=CAPTURE_MEMBER_MODE):
    _safe_relative(name, "output member")
    directory = _safe_directory(directory, "capture output")
    descriptor, temporary = tempfile.mkstemp(prefix=".rk006-", dir=str(directory))
    try:
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, str(directory / name))
    except OSError as exc:
        raise CaptureError("cannot publish {}: {}".format(name, exc))
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            if os.path.exists(temporary):
                os.unlink(temporary)
        except OSError:
            pass


def _strict_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _strict_equal(actual[key], expected[key]) for key in expected
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _strict_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _require_exact(actual, expected, label):
    if not _strict_equal(actual, expected):
        raise CaptureError("{} differs from the frozen contract".format(label))


def _require_keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise CaptureError("{} has a non-canonical schema".format(label))


def _input_record(path, data):
    return {"path": path, "sha256": _sha256(data), "size": len(data)}


def _run(arguments, cwd=None, allow_failure=False):
    if not arguments or not all(type(item) is str and item for item in arguments):
        raise CaptureError("command arguments are invalid")
    try:
        completed = subprocess.run(
            list(arguments),
            cwd=str(cwd) if cwd is not None else None,
            env=dict(CAPTURE_ENV),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1800,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CaptureError("command failed to execute: {}".format(exc))
    if completed.returncode and not allow_failure:
        raise CaptureError(
            "command failed ({}): {}".format(
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace")[-2000:],
            )
        )
    return completed


def _validate_contract_structure(contract):
    _require_keys(
        contract,
        {
            "artifact_policy",
            "build_binding_policy",
            "capture_contract_id",
            "capture_policy",
            "claims",
            "gate",
            "inputs",
            "parent_files",
            "remaining_blockers",
            "runtime",
            "schema_version",
            "tool_probe_policy",
        },
        "capture contract",
    )
    if contract["schema_version"] != 1:
        raise CaptureError("unsupported capture contract schema")
    if contract["capture_contract_id"] != "rk-006-full-source-build-capture-v1":
        raise CaptureError("capture contract identity differs")
    _require_exact(contract["claims"], FALSE_CLAIMS, "capture claims")
    _require_exact(contract["gate"], FALSE_GATE, "capture gate")
    _require_exact(contract["parent_files"], PARENT_FILES, "full parent hashes")
    artifact = contract["artifact_policy"]
    _require_keys(
        artifact,
        {
            "actions_retention_days",
            "artifact_is_durable",
            "checksum_manifest",
            "member_mode",
            "output_members",
        },
        "artifact policy",
    )
    _require_exact(
        artifact,
        {
            "actions_retention_days": 30,
            "artifact_is_durable": False,
            "checksum_manifest": "SHA256SUMS",
            "member_mode": "0644",
            "output_members": CAPTURE_MEMBERS,
        },
        "artifact policy",
    )
    build = contract["build_binding_policy"]
    _require_keys(
        build,
        {
            "build_artifact_is_durable",
            "build_evidence_checksum_manifest",
            "build_evidence_required_members",
            "copy_build_payload_into_capture",
            "require_commit_sha_match",
            "require_complete_build_phase",
            "require_zero_exit_codes",
        },
        "build binding policy",
    )
    _require_exact(
        build,
        {
            "build_artifact_is_durable": False,
            "build_evidence_checksum_manifest": "SHA256SUMS",
            "build_evidence_required_members": REQUIRED_BUILD_MEMBERS,
            "copy_build_payload_into_capture": False,
            "require_commit_sha_match": True,
            "require_complete_build_phase": True,
            "require_zero_exit_codes": True,
        },
        "build binding policy",
    )
    capture = contract["capture_policy"]
    _require_keys(
        capture,
        {
            "external_closure_algorithm",
            "full_source_closure_algorithm",
            "full_external_parent_preimages_required",
            "patch_apply_command",
            "patch_count",
            "patch_order_source",
            "reject_backup_and_reject_files",
            "second_application_command_addition",
            "second_application_must_fail_for_every_patch",
            "snapshot_archive_format",
            "snapshot_member_mode",
            "snapshot_mtime",
            "source_archive_extraction_owned_by_capture",
            "symlinks_followed",
        },
        "capture policy",
    )
    _require_exact(
        capture,
        {
            "external_closure_algorithm": "sha256-canonical-json-ordered-path-state-rows-v1",
            "full_source_closure_algorithm": FULL_SOURCE_CLOSURE_ALGORITHM,
            "full_external_parent_preimages_required": True,
            "patch_apply_command": [
                "patch",
                "-p1",
                "--batch",
                "--forward",
                "--fuzz=0",
                "--no-backup-if-mismatch",
            ],
            "patch_count": 25,
            "patch_order_source": AUTHORITY_PATH,
            "reject_backup_and_reject_files": True,
            "second_application_command_addition": ["--dry-run"],
            "second_application_must_fail_for_every_patch": True,
            "snapshot_archive_format": "tar+xz",
            "snapshot_member_mode": "0444",
            "snapshot_mtime": 0,
            "source_archive_extraction_owned_by_capture": True,
            "symlinks_followed": False,
        },
        "capture policy",
    )
    _require_exact(
        contract["runtime"],
        {
            "architecture": "x86_64",
            "container_image": CONTAINER_IMAGE,
            "distribution_id": "rocky",
            "distribution_version": "10.2",
        },
        "capture runtime",
    )
    _require_exact(
        contract["tool_probe_policy"],
        {
            "capture_tools": [["patch", "--version"], ["python3", "--version"]],
            "locked_tools": [
                ["bindgen", "--version", "workaround-for-0.69.0"],
                ["clang", "--version"],
                ["ld.lld", "--version"],
                ["llvm-config", "--version"],
                ["pahole", "--version"],
                ["rustc", "--version", "--verbose"],
            ],
            "record_binary_sha256": True,
            "record_command_stream_sha256": True,
            "record_rpm_nevra_owner": True,
            "rust_src_core_required": True,
        },
        "tool probe policy",
    )
    _require_exact(contract["remaining_blockers"], REMAINING_BLOCKERS, "remaining blockers")


def validate_contract(repo, run_authority=True):
    repo = _safe_directory(repo, "repository")
    contract_data, _ = _read_rooted(repo, CONTRACT_PATH, "capture contract")
    contract = _load_json_bytes(contract_data, "capture contract")
    _validate_contract_structure(contract)
    expected_inputs = {
        "parent_integration_authority": ("host-kernel/kbuild/parent-integration-v1.json", "c806e6cda3be3e6f4b92cef35a0d5369738bae5b87e32ed4f486489d3435db2f", 2076),
        "patch_authority": (AUTHORITY_PATH, "ebc3e4c69ecbdb3891f92018a89f5fc3dae43fa070628fda8b22f881f02c67a1", 19681),
        "patch_authority_checker": ("scripts/rocky_kernel_rk006_patch_authority.py", "c23969ba2716db96f02a0564d6815b7342036a58c258ce22319b0185693cfddd", 48959),
        "patch_authority_tests": ("scripts/tests/test_rocky_kernel_rk006_patch_authority.py", "719d1e87b4d66944abf3bad0c03dc7cc86dddb97fa36e3fe32736c29ea549b39", 27957),
        "source_lock": ("host-kernel/rocky/source-lock.json", "707ee40466ac0bb0cd0600383bba0b13fc1146e7080034786bf5668a95b27682", 18236),
        "toolchain_lock": ("host-kernel/rocky/toolchain-lock.json", "fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802", 28867),
    }
    inputs = contract["inputs"]
    if set(inputs) != set(expected_inputs) | {"source_archive", "source_rpm", "vendor_patch"}:
        raise CaptureError("capture input schema differs")
    for key, expected in sorted(expected_inputs.items()):
        record = inputs.get(key)
        _require_exact(
            record,
            {"path": expected[0], "sha256": expected[1], "size": expected[2]},
            key,
        )
        data, _ = _read_rooted(repo, expected[0], key)
        if len(data) != expected[2] or _sha256(data) != expected[1]:
            raise CaptureError("{} bytes differ".format(key))
    _require_exact(
        inputs["source_archive"],
        {
            "filename": "linux-6.12.0-211.44.1.el10_2.tar.xz",
            "root": "linux-6.12.0-211.44.1.el10_2",
            "sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
            "size": 153374592,
        },
        "source archive",
    )
    _require_exact(
        inputs["source_rpm"],
        {
            "filename": "kernel-6.12.0-211.44.1.el10_2.src.rpm",
            "sha256": "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb",
            "size": 159328372,
        },
        "source RPM",
    )
    _require_exact(
        inputs["vendor_patch"],
        {
            "filename": "1000-debrand-some-messages.patch",
            "sha256": "080bbc72a543eed6b71daee1b3236b59f3a0f8b3ad20815d962444d3b106b144",
            "size": 928,
        },
        "vendor patch",
    )
    authority_data, _ = _read_rooted(repo, AUTHORITY_PATH, "RK-006 authority")
    authority = _load_json_bytes(authority_data, "RK-006 authority")
    if len(authority.get("patches", [])) != 25:
        raise CaptureError("RK-006 authority does not contain 25 patches")
    if [row.get("order") for row in authority["patches"]] != list(range(1, 26)):
        raise CaptureError("RK-006 authority patch order differs")
    for row in authority["patches"]:
        patch_data, _ = _read_rooted(repo, row["path"], "authority patch")
        if _sha256(patch_data) != row["sha256"]:
            raise CaptureError("authority patch bytes differ: {}".format(row["path"]))
    parent_data, _ = _read_rooted(repo, inputs["parent_integration_authority"]["path"], "parent authority")
    parent = _load_json_bytes(parent_data, "parent authority")
    parent_rows = sorted(
        [
            {
                "path": row["path"],
                "postimage_sha256": row["postimage_sha256"],
                "preimage_sha256": row["preimage_sha256"],
            }
            for row in parent.get("parent_files", [])
        ],
        key=lambda row: row["path"],
    )
    _require_exact(parent_rows, PARENT_FILES, "parent authority hashes")
    source_data, _ = _read_rooted(repo, inputs["source_lock"]["path"], "source lock")
    source = _load_json_bytes(source_data, "source lock")
    source_archive = [
        row for row in source.get("embedded_objects", [])
        if row.get("role") == "Rocky-derived Linux source archive"
    ]
    if (
        len(source_archive) != 1
        or source_archive[0].get("sha256") != inputs["source_archive"]["sha256"]
        or source.get("source_rpm", {}).get("sha256") != inputs["source_rpm"]["sha256"]
    ):
        raise CaptureError("source lock and capture inputs diverge")
    toolchain_data, _ = _read_rooted(repo, inputs["toolchain_lock"]["path"], "toolchain lock")
    toolchain = _load_json_bytes(toolchain_data, "toolchain lock")
    if (
        toolchain.get("source_lock", {}).get("source_archive_sha256") != inputs["source_archive"]["sha256"]
        or toolchain.get("source_lock", {}).get("source_rpm_sha256") != inputs["source_rpm"]["sha256"]
    ):
        raise CaptureError("toolchain lock and source inputs diverge")
    if run_authority:
        checker = repo / inputs["patch_authority_checker"]["path"]
        completed = subprocess.run(
            [sys.executable, str(checker), "--repo", str(repo)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode:
            raise CaptureError(
                "RK-006 authority checker failed: {}".format(
                    completed.stderr.decode("utf-8", errors="replace")[-2000:]
                )
            )
    return contract, authority


def _verify_exact_external(path, record, label):
    data, metadata = _read_explicit_file(path, label)
    if Path(path).name != record["filename"]:
        raise CaptureError("{} filename differs".format(label))
    if len(data) != record["size"] or _sha256(data) != record["sha256"]:
        raise CaptureError("{} bytes differ from the source lock".format(label))
    return data, metadata


def _path_state(root, relative):
    candidate = Path(root) / relative
    try:
        metadata = candidate.lstat()
    except FileNotFoundError:
        return {"path": relative, "sha256": None, "size": None, "type": "absent"}, None
    except OSError as exc:
        raise CaptureError("cannot inspect source path {}: {}".format(relative, exc))
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise CaptureError("source path is not regular or absent: {}".format(relative))
    data, checked = _read_rooted(root, relative, "source path")
    return {
        "mode": "{:04o}".format(stat.S_IMODE(checked.st_mode)),
        "path": relative,
        "sha256": _sha256(data),
        "size": len(data),
        "type": "regular",
    }, data


def _closure(root, paths):
    rows = []
    for relative in sorted(set(paths)):
        row, _ = _path_state(root, relative)
        rows.append(row)
    return {"algorithm": "sha256-canonical-json-ordered-path-state-rows-v1", "row_count": len(rows), "sha256": _sha256(_canonical_json(rows))}, rows


def _tar_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(entries.items()):
            _safe_relative(name, "tar member")
            member = tarfile.TarInfo(name=name)
            member.size = len(data)
            member.mode = 0o444
            member.mtime = 0
            member.uid = 0
            member.gid = 0
            member.uname = ""
            member.gname = ""
            archive.addfile(member, io.BytesIO(data))
    return output.getvalue()


def _inspect_tar(data, label):
    records = []
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as archive:
            for member in archive.getmembers():
                _safe_relative(member.name, label + " member")
                if not member.isreg() or member.issym() or member.islnk():
                    raise CaptureError("{} contains a non-regular member".format(label))
                if member.mode != 0o444 or member.mtime != 0 or member.uid != 0 or member.gid != 0:
                    raise CaptureError("{} member metadata differs".format(label))
                handle = archive.extractfile(member)
                if handle is None:
                    raise CaptureError("{} member is unreadable".format(label))
                payload = handle.read()
                if len(payload) != member.size:
                    raise CaptureError("{} member size differs".format(label))
                records.append({"path": member.name, "sha256": _sha256(payload), "size": len(payload)})
    except (tarfile.TarError, lzma.LZMAError, OSError) as exc:
        raise CaptureError("cannot inspect {}: {}".format(label, exc))
    paths = [row["path"] for row in records]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise CaptureError("{} member order or uniqueness differs".format(label))
    return records


def _archive_member_path(name, expected_root):
    if type(name) is not str or not name or "\\" in name or "\x00" in name:
        raise CaptureError("source archive member path is unsafe")
    normalized = name[:-1] if name.endswith("/") else name
    path = _safe_relative(normalized, "source archive member")
    if path.parts[0] != expected_root:
        raise CaptureError("source archive member escapes the exact root")
    relative = "/".join(path.parts[1:])
    if relative:
        _safe_relative(relative, "source archive relative member")
    return str(path), relative


def _validate_archive_link_target(relative, target):
    if type(target) is not str or not target or "\\" in target or "\x00" in target:
        raise CaptureError("source archive symlink target is unsafe")
    link = PurePosixPath(target)
    if link.is_absolute():
        raise CaptureError("source archive symlink target is absolute")
    resolved = list(PurePosixPath(relative).parent.parts)
    for part in link.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not resolved:
                raise CaptureError("source archive symlink target escapes the root")
            resolved.pop()
        else:
            resolved.append(part)


def _extract_locked_source_archive(data, source_root, expected_root):
    source_root = Path(os.path.abspath(os.fspath(source_root)))
    if source_root.name != expected_root:
        raise CaptureError("external source root name differs")
    parent = _safe_directory(source_root.parent, "external source parent")
    source_root = parent / source_root.name
    if os.path.lexists(str(source_root)):
        raise CaptureError("external source root must not preexist")

    created = False
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as archive:
            members = archive.getmembers()
            if not members:
                raise CaptureError("source archive is empty")
            entries = {}
            directory_modes = {}
            regular_members = []
            symlink_members = []
            rows = {}
            root_mode = None
            for member in members:
                full, relative = _archive_member_path(member.name, expected_root)
                if full in entries:
                    raise CaptureError("source archive contains duplicate members")
                mode = stat.S_IMODE(member.mode)
                if member.isdir():
                    kind = "directory"
                    if relative:
                        directory_modes[relative] = mode
                    else:
                        root_mode = mode
                    rows[full] = {
                        "mode": "{:04o}".format(mode),
                        "path": full,
                        "type": kind,
                    }
                elif not relative:
                    raise CaptureError("source archive root is not a directory")
                elif member.isreg():
                    kind = "regular"
                    regular_members.append((member, full, relative, mode))
                elif member.issym():
                    kind = "symlink"
                    _validate_archive_link_target(relative, member.linkname)
                    symlink_members.append((member, full, relative, mode))
                    rows[full] = {
                        "mode": "{:04o}".format(mode),
                        "path": full,
                        "target": member.linkname,
                        "type": kind,
                    }
                else:
                    raise CaptureError("source archive contains an unsupported member type")
                entries[full] = kind
            if root_mode is None or entries.get(expected_root) != "directory":
                raise CaptureError("source archive lacks its exact root directory")
            for full, kind in entries.items():
                if full == expected_root:
                    continue
                relative = full[len(expected_root) + 1:]
                parts = PurePosixPath(relative).parts
                for index in range(1, len(parts)):
                    ancestor = expected_root + "/" + "/".join(parts[:index])
                    if entries.get(ancestor) != "directory":
                        raise CaptureError(
                            "source archive member traverses a missing or non-directory parent"
                        )

            source_root.mkdir(mode=0o755)
            created = True
            for relative in sorted(directory_modes, key=lambda value: (len(PurePosixPath(value).parts), value)):
                (source_root / relative).mkdir(mode=0o755)
            for member, full, relative, mode in regular_members:
                handle = archive.extractfile(member)
                if handle is None:
                    raise CaptureError("source archive regular member is unreadable")
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_BINARY"):
                    flags |= os.O_BINARY
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                descriptor = os.open(str(source_root / relative), flags, mode)
                digest = hashlib.sha256()
                size = 0
                try:
                    while True:
                        chunk = handle.read(1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                        size += len(chunk)
                        offset = 0
                        while offset < len(chunk):
                            offset += os.write(descriptor, chunk[offset:])
                    os.fchmod(descriptor, mode)
                finally:
                    os.close(descriptor)
                    handle.close()
                if size != member.size:
                    raise CaptureError("source archive regular member size differs")
                rows[full] = {
                    "mode": "{:04o}".format(mode),
                    "path": full,
                    "sha256": digest.hexdigest(),
                    "size": size,
                    "type": "regular",
                }
            for member, full, relative, mode in symlink_members:
                os.symlink(member.linkname, str(source_root / relative))
            for relative in sorted(
                directory_modes,
                key=lambda value: (len(PurePosixPath(value).parts), value),
                reverse=True,
            ):
                os.chmod(str(source_root / relative), directory_modes[relative])
            os.chmod(str(source_root), root_mode)
    except CaptureError:
        if created:
            shutil.rmtree(str(source_root))
        raise
    except (tarfile.TarError, lzma.LZMAError, OSError) as exc:
        if created:
            shutil.rmtree(str(source_root))
        raise CaptureError("cannot safely extract locked source archive: {}".format(exc))

    ordered = [rows[path] for path in sorted(rows)]
    return {
        "algorithm": FULL_SOURCE_CLOSURE_ALGORITHM,
        "row_count": len(ordered),
        "sha256": _sha256(_canonical_json(ordered)),
    }


def _log_record(kind, identifier, command, completed):
    return {
        "command": command,
        "id": identifier,
        "kind": kind,
        "returncode": completed.returncode,
        "stderr": completed.stderr.decode("utf-8", errors="replace"),
        "stderr_sha256": _sha256(completed.stderr),
        "stdout": completed.stdout.decode("utf-8", errors="replace"),
        "stdout_sha256": _sha256(completed.stdout),
    }


def _patch_command(patch_program, patch_path, dry_run=False):
    command = [
        patch_program,
        "-p1",
        "--batch",
        "--forward",
        "--fuzz=0",
        "--no-backup-if-mismatch",
    ]
    if dry_run:
        command.append("--dry-run")
    command.extend(["-i", str(patch_path)])
    return command


def _validate_parent(root, field):
    for row in PARENT_FILES:
        state, _ = _path_state(root, row["path"])
        if state["type"] != "regular" or state["sha256"] != row[field]:
            raise CaptureError("full parent {} mismatch: {}".format(field, row["path"]))


def _replay_patch_series(repo, source_root, authority, enforce_parent_hashes=True):
    patch_program = shutil.which("patch", path=CAPTURE_ENV["PATH"])
    if patch_program is None:
        raise CaptureError("GNU patch is unavailable")
    source_root = _safe_directory(source_root, "external source root")
    touched_all = sorted({path for row in authority["patches"] for path in row["touched_paths"]})
    initial_closure, _ = _closure(source_root, touched_all)
    pre_entries = {}
    post_entries = {}
    patch_records = []
    apply_logs = []
    parent_patch = [row for row in authority["patches"] if row["id"] == "parent-001"]
    if len(parent_patch) != 1:
        raise CaptureError("parent patch identity is ambiguous")
    for row in authority["patches"]:
        if row["id"] == "parent-001" and enforce_parent_hashes:
            _validate_parent(source_root, "preimage_sha256")
        before, before_rows = _closure(source_root, row["touched_paths"])
        before_states = []
        for relative in row["touched_paths"]:
            state, data = _path_state(source_root, relative)
            archive_member = None
            if data is not None:
                archive_member = "patches/{:04d}/{}/{}".format(row["order"], row["id"], relative)
                pre_entries[archive_member] = data
            before_states.append({"archive_member": archive_member, "state": state})
        patch_path = repo / row["path"]
        command = _patch_command(patch_program, patch_path)
        completed = _run(command, cwd=source_root, allow_failure=True)
        apply_logs.append(_log_record("apply", row["id"], command, completed))
        if completed.returncode != 0:
            raise CaptureError("{} failed exact external replay".format(row["id"]))
        if row["id"] == "parent-001" and enforce_parent_hashes:
            _validate_parent(source_root, "postimage_sha256")
        after, after_rows = _closure(source_root, row["touched_paths"])
        after_states = []
        for relative in row["touched_paths"]:
            state, data = _path_state(source_root, relative)
            archive_member = None
            if data is not None:
                archive_member = "patches/{:04d}/{}/{}".format(row["order"], row["id"], relative)
                post_entries[archive_member] = data
            after_states.append({"archive_member": archive_member, "state": state})
        patch_records.append(
            {
                "after": after,
                "after_states": after_states,
                "before": before,
                "before_states": before_states,
                "id": row["id"],
                "layer": row["layer"],
                "order": row["order"],
                "patch_path": row["path"],
                "patch_sha256": row["sha256"],
            }
        )
    second_logs = []
    for row in authority["patches"]:
        patch_path = repo / row["path"]
        command = _patch_command(patch_program, patch_path, dry_run=True)
        completed = _run(command, cwd=source_root, allow_failure=True)
        second_logs.append(_log_record("second-application", row["id"], command, completed))
        if completed.returncode == 0:
            raise CaptureError("{} unexpectedly applies a second time".format(row["id"]))
    leftovers = sorted(
        str(path.relative_to(source_root))
        for path in source_root.rglob("*")
        if path.name.endswith((".orig", ".rej"))
    )
    if leftovers:
        raise CaptureError("patch replay left reject/backup files: {}".format(leftovers))
    final_closure, _ = _closure(source_root, touched_all)
    return {
        "apply_log": b"".join(_canonical_json(row) for row in apply_logs),
        "external_final_closure": final_closure,
        "external_initial_closure": initial_closure,
        "patch_records": patch_records,
        "postimages": _tar_bytes(post_entries),
        "preimages": _tar_bytes(pre_entries),
        "second_log": b"".join(_canonical_json(row) for row in second_logs),
        "touched_path_count": len(touched_all),
    }


def _rpm_owner(path):
    command = [
        "rpm",
        "-qf",
        "--qf",
        "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
        str(path),
    ]
    completed = _run(command)
    if completed.stderr:
        raise CaptureError("RPM owner query wrote stderr")
    rows = completed.stdout.decode("utf-8", errors="strict").splitlines()
    if len(rows) != 1:
        raise CaptureError("RPM owner query is ambiguous")
    return rows[0], command


def _probe_tools():
    results = {}
    for probe_id, expected in sorted(LOCKED_PROBES.items()):
        binary = shutil.which(expected["command"][0], path=CAPTURE_ENV["PATH"])
        if binary != expected["path"]:
            raise CaptureError("{} binary path differs".format(probe_id))
        capture = _capture_locked_probe(binary, expected, probe_id + " binary")
        binary_data = capture["binary_data"]
        owner = capture["owner"]
        owner_command = capture["owner_command"]
        completed = capture["completed"]
        result = {
            "binary_path": binary,
            "binary_sha256": _sha256(binary_data),
            "command": expected["command"],
            "owner_command": owner_command,
            "package_nevra": owner,
            "stderr_sha256": _sha256(completed.stderr),
            "stdout_sha256": _sha256(completed.stdout),
            "text": (completed.stdout + completed.stderr).decode("utf-8", errors="strict"),
        }
        if (
            result["binary_sha256"] != expected["sha256"]
            or result["package_nevra"] != expected["owner"]
            or result["stdout_sha256"] != expected["stdout_sha256"]
        ):
            raise CaptureError("{} exact identity differs".format(probe_id))
        results[probe_id] = result
    sysroot = _run(["rustc", "--print", "sysroot"])
    if sysroot.stderr:
        raise CaptureError("rustc sysroot probe wrote stderr")
    sysroot_rows = sysroot.stdout.decode("utf-8", errors="strict").splitlines()
    if len(sysroot_rows) != 1:
        raise CaptureError("rustc sysroot probe is ambiguous")
    core_path = Path(sysroot_rows[0]) / "lib/rustlib/src/rust/library/core/src/lib.rs"
    if str(core_path) != RUST_SRC_CORE["path"]:
        raise CaptureError("rust-src core path differs")
    core_data, _ = _read_explicit_file(core_path, "rust-src core", allow_hardlink=True)
    owner, owner_command = _rpm_owner(core_path)
    if (
        _sha256(core_data) != RUST_SRC_CORE["sha256"]
        or owner != RUST_SRC_CORE["owner"]
        or _sha256(sysroot.stdout) != RUST_SRC_CORE["stdout_sha256"]
    ):
        raise CaptureError("rust-src core exact identity differs")
    results["rust_src_core"] = {
        "command": ["rustc", "--print", "sysroot"],
        "file_path": str(core_path),
        "file_sha256": _sha256(core_data),
        "owner_command": owner_command,
        "package_nevra": owner,
        "stderr_sha256": _sha256(sysroot.stderr),
        "stdout_sha256": _sha256(sysroot.stdout),
    }
    for probe_id, identity in sorted(CAPTURE_TOOL_PROBES.items()):
        command = identity["command"]
        binary = shutil.which(command[0], path=CAPTURE_ENV["PATH"])
        if binary != identity["path"]:
            raise CaptureError("{} capture tool path differs".format(probe_id))
        resolved = str(Path(binary).resolve())
        if resolved != identity["resolved_path"]:
            raise CaptureError("{} capture tool resolved path differs".format(probe_id))
        binary_data, _ = _read_explicit_file(resolved, probe_id + " binary", allow_hardlink=True)
        owner, owner_command = _rpm_owner(binary)
        completed = _run(command)
        results[probe_id] = {
            "binary_path": binary,
            "binary_resolved_path": resolved,
            "binary_sha256": _sha256(binary_data),
            "command": command,
            "owner_command": owner_command,
            "package_nevra": owner,
            "stderr_sha256": _sha256(completed.stderr),
            "stdout_sha256": _sha256(completed.stdout),
            "text": (completed.stdout + completed.stderr).decode("utf-8", errors="strict"),
        }
    return {
        "claims": dict(FALSE_CLAIMS),
        "environment": dict(CAPTURE_ENV),
        "probe_count": len(results),
        "probes": results,
        "schema_version": 1,
    }


def _repository_input_paths(authority):
    fixed = [
        CONTRACT_PATH,
        AUTHORITY_PATH,
        "scripts/rocky_kernel_rk006_patch_authority.py",
        "scripts/tests/test_rocky_kernel_rk006_patch_authority.py",
        "host-kernel/kbuild/parent-integration-v1.json",
        "host-kernel/rocky/source-lock.json",
        "host-kernel/rocky/toolchain-lock.json",
        "host-kernel/rocky/patches/series.json",
        "scripts/rocky_kernel_source_lock.py",
        "scripts/tests/test_rocky_kernel_source_lock.py",
        CAPTURE_SCRIPT_PATH,
        CAPTURE_TEST_PATH,
        WORKFLOW_PATH,
        WORKFLOW_TEST_PATH,
        "scripts/native_rust_runtime_evidence.py",
        "scripts/tests/test_native_rust_runtime_evidence.py",
    ]
    return sorted(set(fixed + [row["path"] for row in authority["patches"]]))


def _repository_inputs(repo, authority):
    paths = _repository_input_paths(authority)
    entries = {}
    rows = []
    for relative in paths:
        data, metadata = _read_rooted(repo, relative, "repository input")
        entries[relative] = data
        rows.append(
            {
                "mode": "{:04o}".format(stat.S_IMODE(metadata.st_mode)),
                "path": relative,
                "sha256": _sha256(data),
                "size": len(data),
            }
        )
    archive = _tar_bytes(entries)
    return archive, rows


def _validate_repository_input_membership(rows, authority):
    if type(rows) is not list or any(type(row) is not dict for row in rows):
        raise CaptureError("captured repository input rows differ")
    paths = [row.get("path") for row in rows]
    if paths != _repository_input_paths(authority):
        raise CaptureError("repository input membership differs from the exact capture closure")


def _check_git_identity(repo, head_sha):
    if re.fullmatch(r"[0-9a-f]{40}", head_sha or "") is None:
        raise CaptureError("GitHub head SHA must be exact lowercase 40-hex")
    completed = subprocess.run(
        ["git", "-c", "safe.directory={}".format(repo), "-C", str(repo), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode or completed.stdout.decode("ascii", errors="strict").strip() != head_sha:
        raise CaptureError("checked-out HEAD differs from requested capture identity")
    status = subprocess.run(
        ["git", "-c", "safe.directory={}".format(repo), "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if status.returncode or status.stdout:
        raise CaptureError("tracked repository worktree is not clean")


def _write_manifest(directory):
    rows = []
    for name in CAPTURE_MEMBERS:
        if name == "SHA256SUMS":
            continue
        data, metadata = _read_rooted(directory, name, "capture member")
        if stat.S_IMODE(metadata.st_mode) != CAPTURE_MEMBER_MODE:
            raise CaptureError("capture member mode differs: {}".format(name))
        rows.append("{}  {}\n".format(_sha256(data), name))
    _write_atomic(directory, "SHA256SUMS", "".join(rows).encode("ascii"))


def capture(args):
    repo = _safe_directory(args.repo, "repository")
    contract, authority = validate_contract(repo)
    _safe_directory(CAPTURE_ENV["HOME"], "capture HOME", create=True)
    _check_git_identity(repo, args.github_head_sha)
    if not str(args.github_run_id).isdigit() or int(args.github_run_id) <= 0:
        raise CaptureError("GitHub run ID is invalid")
    if not str(args.github_run_attempt).isdigit() or int(args.github_run_attempt) <= 0:
        raise CaptureError("GitHub run attempt is invalid")
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.github_repository or "") is None:
        raise CaptureError("GitHub repository identity is invalid")
    if args.container_image != CONTAINER_IMAGE:
        raise CaptureError("container image differs from the contract")
    archive_data, _ = _verify_exact_external(args.source_archive, contract["inputs"]["source_archive"], "source archive")
    srpm_data, _ = _verify_exact_external(args.source_rpm, contract["inputs"]["source_rpm"], "source RPM")
    vendor_data, _ = _verify_exact_external(args.vendor_patch, contract["inputs"]["vendor_patch"], "vendor patch")
    output = _safe_directory(args.output_dir, "capture output", create=True)
    existing = sorted(path.name for path in output.iterdir() if path.name != "workflow-state")
    if existing:
        raise CaptureError("capture output is not empty: {}".format(existing))
    source_root = Path(os.path.abspath(os.fspath(args.source_root)))
    full_source_closure = _extract_locked_source_archive(
        archive_data,
        source_root,
        contract["inputs"]["source_archive"]["root"],
    )
    source_root = _safe_directory(source_root, "external source root")
    vendor_command = [
        shutil.which("patch", path=CAPTURE_ENV["PATH"]),
        "-p1",
        "--batch",
        "--forward",
        "--fuzz=0",
        "--no-backup-if-mismatch",
        "-i",
        str(Path(args.vendor_patch).resolve()),
    ]
    if vendor_command[0] is None:
        raise CaptureError("GNU patch is unavailable")
    vendor_result = _run(vendor_command, cwd=source_root, allow_failure=True)
    if vendor_result.returncode:
        raise CaptureError("Rocky vendor patch failed exact replay")
    replay = _replay_patch_series(repo, source_root, authority, enforce_parent_hashes=True)
    vendor_log = _log_record("vendor-apply", "rocky-vendor-1000", vendor_command, vendor_result)
    replay["apply_log"] = _canonical_json(vendor_log) + replay["apply_log"]
    tool_probes = _probe_tools()
    repository_archive, repository_rows = _repository_inputs(repo, authority)
    source_inputs = {
        "source_archive": {
            "filename": Path(args.source_archive).name,
            "sha256": _sha256(archive_data),
            "size": len(archive_data),
        },
        "source_rpm": {
            "filename": Path(args.source_rpm).name,
            "sha256": _sha256(srpm_data),
            "size": len(srpm_data),
        },
        "vendor_patch": {
            "filename": Path(args.vendor_patch).name,
            "sha256": _sha256(vendor_data),
            "size": len(vendor_data),
        },
    }
    capture_document = {
        "artifacts": {
            "patch_apply_log_sha256": _sha256(replay["apply_log"]),
            "postimages_sha256": _sha256(replay["postimages"]),
            "preimages_sha256": _sha256(replay["preimages"]),
            "repository_inputs_sha256": _sha256(repository_archive),
            "second_application_log_sha256": _sha256(replay["second_log"]),
            "tool_probes_sha256": _sha256(_canonical_json(tool_probes)),
        },
        "build_binding": {
            "build_binding_sha256": None,
            "status": "required-pending",
        },
        "capture_contract_id": contract["capture_contract_id"],
        "claims": dict(FALSE_CLAIMS),
        "external_final_closure": replay["external_final_closure"],
        "external_initial_closure": replay["external_initial_closure"],
        "full_source_pre_vendor_closure": full_source_closure,
        "gate": dict(FALSE_GATE),
        "github": {
            "head_sha": args.github_head_sha,
            "repository": args.github_repository,
            "run_attempt": int(args.github_run_attempt),
            "run_id": int(args.github_run_id),
        },
        "parent_files": list(PARENT_FILES),
        "patch_count": len(replay["patch_records"]),
        "patch_replay": replay["patch_records"],
        "repository_inputs": repository_rows,
        "runtime": dict(contract["runtime"]),
        "schema_version": 1,
        "source_inputs": source_inputs,
        "state": "source-capture-complete",
        "touched_path_count": replay["touched_path_count"],
    }
    pending_build = {
        "build_artifact": {
            "durable": False,
            "name": "native-rust-exact-build-{}-{}".format(args.github_run_id, args.github_run_attempt),
            "outer_artifact_sha256": None,
            "retention_days": 30,
        },
        "claims": dict(FALSE_CLAIMS),
        "schema_version": 1,
        "status": "required-pending",
    }
    for name, data in (
        ("repository-inputs.tar.xz", repository_archive),
        ("preimages.tar.xz", replay["preimages"]),
        ("postimages.tar.xz", replay["postimages"]),
        ("patch-apply.log", replay["apply_log"]),
        ("second-application.log", replay["second_log"]),
        ("tool-probes.json", _canonical_json(tool_probes)),
        ("build-binding.json", _canonical_json(pending_build)),
        ("capture.json", _canonical_json(capture_document)),
        ("workflow-state", b"source-capture-complete\n"),
    ):
        _write_atomic(output, name, data)
    _write_manifest(output)
    verify_capture(repo, output)
    return capture_document


def _parse_checksum_manifest(data, label):
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise CaptureError("{} is not ASCII: {}".format(label, exc))
    rows = {}
    ordered_names = []
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\x00\r\n]+)", line)
        if match is None:
            raise CaptureError("{} contains a malformed row".format(label))
        name = match.group(2)
        _safe_relative(name, label + " path")
        if "/" in name or name in rows:
            raise CaptureError("{} contains duplicate or nested paths".format(label))
        rows[name] = match.group(1)
        ordered_names.append(name)
    if not rows:
        raise CaptureError("{} is empty".format(label))
    if ordered_names != sorted(ordered_names):
        raise CaptureError("{} paths are not canonical-order sorted".format(label))
    return rows


def _build_binding(build_dir, capture_document):
    build_dir = _safe_directory(build_dir, "build evidence")
    manifest_data, manifest_metadata = _read_rooted(
        build_dir, "SHA256SUMS", "build checksum manifest"
    )
    if (
        stat.S_IMODE(manifest_metadata.st_mode) != 0o644
        or manifest_metadata.st_nlink != 1
        or manifest_metadata.st_size != len(manifest_data)
    ):
        raise CaptureError("build checksum manifest identity or mode differs")
    manifest = _parse_checksum_manifest(manifest_data, "build checksum manifest")
    actual_names = sorted(
        path.name for path in build_dir.iterdir()
        if path.name != "SHA256SUMS"
    )
    if actual_names != sorted(manifest):
        raise CaptureError("build evidence member set differs from SHA256SUMS")
    for required in REQUIRED_BUILD_MEMBERS:
        if required != "SHA256SUMS" and required not in manifest:
            raise CaptureError("required build evidence is missing: {}".format(required))
    rows = []
    for name in sorted(manifest):
        data, metadata = _read_rooted(build_dir, name, "build evidence member")
        if stat.S_IMODE(metadata.st_mode) != 0o644:
            raise CaptureError("build evidence mode differs: {}".format(name))
        digest = _sha256(data)
        if digest != manifest[name]:
            raise CaptureError("build evidence checksum differs: {}".format(name))
        rows.append({"path": name, "sha256": digest, "size": len(data)})
    expected_head = capture_document["github"]["head_sha"] + "\n"
    commit_data, _ = _read_rooted(build_dir, "commit.sha", "build commit")
    if commit_data.decode("ascii", errors="strict") != expected_head:
        raise CaptureError("build commit differs from source capture")
    for name, expected in (
        ("build.phase", b"complete\n"),
        ("build.exit-code", b"0\n"),
        ("build-log.exit-code", b"0\n"),
        ("workflow-state", b"bootstrap-complete\n"),
    ):
        data, _ = _read_rooted(build_dir, name, "build status")
        if data != expected:
            raise CaptureError("build status differs: {}".format(name))
    return {
        "build_artifact": {
            "content_closure_algorithm": "sha256-canonical-json-build-evidence-rows-v1",
            "content_closure_sha256": _sha256(_canonical_json(rows)),
            "durable": False,
            "file_count": len(rows) + 1,
            "name": "native-rust-exact-build-{}-{}".format(
                capture_document["github"]["run_id"], capture_document["github"]["run_attempt"]
            ),
            "outer_artifact_sha256": None,
            "retention_days": 30,
            "sha256sums_sha256": _sha256(manifest_data),
        },
        "build_evidence": rows,
        "claims": dict(FALSE_CLAIMS),
        "schema_version": 1,
        "status": "technical-build-bound-unreviewed",
    }


def finalize_build(repo, capture_dir, build_dir):
    repo = _safe_directory(repo, "repository")
    validate_contract(repo)
    capture_dir = _safe_directory(capture_dir, "capture output")
    capture_data, _ = _read_rooted(capture_dir, "capture.json", "capture document")
    document = _load_json_bytes(capture_data, "capture document")
    _validate_capture_document(document, allow_pending=True)
    if document["state"] != "source-capture-complete":
        raise CaptureError("capture is not ready for one-time build finalization")
    binding = _build_binding(build_dir, document)
    binding_data = _canonical_json(binding)
    document["build_binding"] = {
        "build_binding_sha256": _sha256(binding_data),
        "status": "technical-build-bound-unreviewed",
    }
    document["state"] = "technical-build-bound-unreviewed"
    _write_atomic(capture_dir, "build-binding.json", binding_data)
    _write_atomic(capture_dir, "capture.json", _canonical_json(document))
    _write_atomic(capture_dir, "workflow-state", b"technical-build-bound-unreviewed\n")
    _write_manifest(capture_dir)
    verify_capture(repo, capture_dir)
    return binding


def _validate_capture_document(document, allow_pending=False):
    _require_keys(
        document,
        {
            "artifacts",
            "build_binding",
            "capture_contract_id",
            "claims",
            "external_final_closure",
            "external_initial_closure",
            "full_source_pre_vendor_closure",
            "gate",
            "github",
            "parent_files",
            "patch_count",
            "patch_replay",
            "repository_inputs",
            "runtime",
            "schema_version",
            "source_inputs",
            "state",
            "touched_path_count",
        },
        "capture document",
    )
    if document["schema_version"] != 1 or document["capture_contract_id"] != "rk-006-full-source-build-capture-v1":
        raise CaptureError("capture document identity differs")
    _require_exact(document["claims"], FALSE_CLAIMS, "capture document claims")
    _require_exact(document["gate"], FALSE_GATE, "capture document gate")
    _require_exact(document["parent_files"], PARENT_FILES, "capture parent hashes")
    if document["patch_count"] != 25 or len(document["patch_replay"]) != 25:
        raise CaptureError("capture does not bind all 25 patches")
    if [row.get("order") for row in document["patch_replay"]] != list(range(1, 26)):
        raise CaptureError("captured patch order differs")
    _require_exact(
        document["runtime"],
        {
            "architecture": "x86_64",
            "container_image": CONTAINER_IMAGE,
            "distribution_id": "rocky",
            "distribution_version": "10.2",
        },
        "captured runtime",
    )
    if (
        type(document["github"]) is not dict
        or type(document["github"].get("head_sha")) is not str
        or re.fullmatch(r"[0-9a-f]{40}", document["github"].get("head_sha", "")) is None
    ):
        raise CaptureError("captured head identity differs")
    _require_keys(
        document["github"],
        {"head_sha", "repository", "run_attempt", "run_id"},
        "captured GitHub identity",
    )
    if (
        type(document["github"]["run_id"]) is not int
        or document["github"]["run_id"] <= 0
        or type(document["github"]["run_attempt"]) is not int
        or document["github"]["run_attempt"] <= 0
        or type(document["github"]["repository"]) is not str
        or re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
            document["github"]["repository"],
        ) is None
    ):
        raise CaptureError("captured GitHub identity fields differ")
    for name in ("external_initial_closure", "external_final_closure"):
        closure = document[name]
        _require_keys(closure, {"algorithm", "row_count", "sha256"}, name)
        if (
            closure["algorithm"]
            != "sha256-canonical-json-ordered-path-state-rows-v1"
            or type(closure["row_count"]) is not int
            or closure["row_count"] <= 0
            or type(closure["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", closure["sha256"]) is None
        ):
            raise CaptureError("{} differs".format(name))
    full_source = document["full_source_pre_vendor_closure"]
    _require_keys(
        full_source,
        {"algorithm", "row_count", "sha256"},
        "full source pre-vendor closure",
    )
    if (
        full_source["algorithm"] != FULL_SOURCE_CLOSURE_ALGORITHM
        or type(full_source["row_count"]) is not int
        or full_source["row_count"] <= 0
        or type(full_source["sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", full_source["sha256"]) is None
    ):
        raise CaptureError("full source pre-vendor closure differs")
    if (
        type(document["touched_path_count"]) is not int
        or document["touched_path_count"] <= 0
        or document["external_initial_closure"]["row_count"]
        != document["touched_path_count"]
        or document["external_final_closure"]["row_count"]
        != document["touched_path_count"]
    ):
        raise CaptureError("external touched-path closure count differs")
    allowed = ["technical-build-bound-unreviewed"]
    if allow_pending:
        allowed.append("source-capture-complete")
    if document["state"] not in allowed:
        raise CaptureError("capture state is invalid")


def _state_rows_closure(states):
    rows = sorted(states, key=lambda row: row["path"])
    return {
        "algorithm": "sha256-canonical-json-ordered-path-state-rows-v1",
        "row_count": len(rows),
        "sha256": _sha256(_canonical_json(rows)),
    }


def _validate_replay_relationships(document, authority, enforce_parent_hashes=True):
    initial = {}
    latest = {}
    parent_before = None
    parent_after = None
    expected_paths = sorted(
        {relative for patch in authority["patches"] for relative in patch["touched_paths"]}
    )
    for captured, expected in zip(document["patch_replay"], authority["patches"]):
        before = {
            entry["state"]["path"]: entry["state"]
            for entry in captured["before_states"]
        }
        after = {
            entry["state"]["path"]: entry["state"]
            for entry in captured["after_states"]
        }
        if (
            sorted(before) != sorted(expected["touched_paths"])
            or sorted(after) != sorted(expected["touched_paths"])
        ):
            raise CaptureError("captured patch state membership differs")
        _require_exact(
            captured["before"],
            _state_rows_closure(list(before.values())),
            "captured patch preimage closure",
        )
        _require_exact(
            captured["after"],
            _state_rows_closure(list(after.values())),
            "captured patch postimage closure",
        )
        for relative in expected["touched_paths"]:
            if relative not in initial:
                initial[relative] = before[relative]
            elif not _strict_equal(latest[relative], before[relative]):
                raise CaptureError("captured patch state continuity differs: {}".format(relative))
            latest[relative] = after[relative]
        if expected["id"] == "parent-001":
            parent_before = before
            parent_after = after
    if sorted(initial) != expected_paths or sorted(latest) != expected_paths:
        raise CaptureError("captured global path-state closure membership differs")
    if document["touched_path_count"] != len(expected_paths):
        raise CaptureError("captured touched-path count differs from authority")
    _require_exact(
        document["external_initial_closure"],
        _state_rows_closure(list(initial.values())),
        "captured external initial closure",
    )
    _require_exact(
        document["external_final_closure"],
        _state_rows_closure(list(latest.values())),
        "captured external final closure",
    )
    if enforce_parent_hashes:
        if parent_before is None or parent_after is None:
            raise CaptureError("captured parent patch states are missing")
        for row in PARENT_FILES:
            before = parent_before.get(row["path"], {})
            after = parent_after.get(row["path"], {})
            if (
                before.get("type") != "regular"
                or before.get("sha256") != row["preimage_sha256"]
                or after.get("type") != "regular"
                or after.get("sha256") != row["postimage_sha256"]
            ):
                raise CaptureError("captured full parent bytes differ: {}".format(row["path"]))


def _validate_patch_log_row(row, kind, identifier, command, require_success):
    _require_keys(
        row,
        {
            "command",
            "id",
            "kind",
            "returncode",
            "stderr",
            "stderr_sha256",
            "stdout",
            "stdout_sha256",
        },
        "patch log row",
    )
    if (
        row["kind"] != kind
        or row["id"] != identifier
        or not _strict_equal(row["command"], command)
        or type(row["returncode"]) is not int
        or type(row["stdout"]) is not str
        or type(row["stderr"]) is not str
        or row["stdout_sha256"] != _sha256(row["stdout"].encode("utf-8"))
        or row["stderr_sha256"] != _sha256(row["stderr"].encode("utf-8"))
    ):
        raise CaptureError("patch log row semantics differ: {}".format(identifier))
    if require_success and row["returncode"] != 0:
        raise CaptureError("patch apply log contains a failed application")
    if not require_success and row["returncode"] <= 0:
        raise CaptureError("second application log lacks a normal rejection")


def _validate_patch_logs(apply_rows, second_rows, authority, repo, vendor_filename):
    patch_program = shutil.which("patch", path=CAPTURE_ENV["PATH"])
    if patch_program is None:
        raise CaptureError("GNU patch is unavailable while verifying patch logs")
    recorded_vendor_command = apply_rows[0].get("command")
    if type(recorded_vendor_command) is not list or not recorded_vendor_command:
        raise CaptureError("vendor patch log command differs")
    vendor_command = [
        patch_program,
        "-p1",
        "--batch",
        "--forward",
        "--fuzz=0",
        "--no-backup-if-mismatch",
        "-i",
        recorded_vendor_command[-1],
    ]
    vendor_path = vendor_command[-1]
    if (
        type(vendor_path) is not str
        or not Path(vendor_path).is_absolute()
        or Path(vendor_path).name != vendor_filename
    ):
        raise CaptureError("vendor patch log path differs")
    _validate_patch_log_row(
        apply_rows[0], "vendor-apply", "rocky-vendor-1000", vendor_command, True
    )
    for apply_row, second_row, expected in zip(
        apply_rows[1:], second_rows, authority["patches"]
    ):
        patch_path = repo / expected["path"]
        _validate_patch_log_row(
            apply_row,
            "apply",
            expected["id"],
            _patch_command(patch_program, patch_path),
            True,
        )
        _validate_patch_log_row(
            second_row,
            "second-application",
            expected["id"],
            _patch_command(patch_program, patch_path, dry_run=True),
            False,
        )


def _validate_tool_probe_document(document, expected=None):
    if expected is None:
        expected = _probe_tools()
    _require_keys(
        document,
        {"claims", "environment", "probe_count", "probes", "schema_version"},
        "tool probe document",
    )
    _require_exact(document["schema_version"], 1, "tool probe schema version")
    _require_exact(document["claims"], FALSE_CLAIMS, "tool probe claims")
    _require_exact(document["environment"], CAPTURE_ENV, "tool probe environment")
    probe_ids = set(LOCKED_PROBES) | {"rust_src_core"} | set(CAPTURE_TOOL_PROBES)
    _require_keys(document["probes"], probe_ids, "tool probe identities")
    _require_exact(document["probe_count"], len(probe_ids), "tool probe count")
    empty_digest = _sha256(b"")
    owner_prefix = [
        "rpm",
        "-qf",
        "--qf",
        "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
    ]
    for probe_id, identity in sorted(LOCKED_PROBES.items()):
        probe = document["probes"][probe_id]
        _require_keys(
            probe,
            {
                "binary_path",
                "binary_sha256",
                "command",
                "owner_command",
                "package_nevra",
                "stderr_sha256",
                "stdout_sha256",
                "text",
            },
            "{} locked-tool probe".format(probe_id),
        )
        if (
            probe["binary_path"] != identity["path"]
            or probe["binary_sha256"] != identity["sha256"]
            or probe["command"] != identity["command"]
            or probe["owner_command"] != owner_prefix + [identity["path"]]
            or probe["package_nevra"] != identity["owner"]
            or probe["stderr_sha256"] != empty_digest
            or probe["stdout_sha256"] != identity["stdout_sha256"]
            or type(probe["text"]) is not str
            or not probe["text"].strip()
            or "\x00" in probe["text"]
        ):
            raise CaptureError("{} locked-tool identity differs".format(probe_id))

    rust_src = document["probes"]["rust_src_core"]
    _require_keys(
        rust_src,
        {
            "command",
            "file_path",
            "file_sha256",
            "owner_command",
            "package_nevra",
            "stderr_sha256",
            "stdout_sha256",
        },
        "rust-src core probe",
    )
    if (
        rust_src["command"] != ["rustc", "--print", "sysroot"]
        or rust_src["file_path"] != RUST_SRC_CORE["path"]
        or rust_src["file_sha256"] != RUST_SRC_CORE["sha256"]
        or rust_src["owner_command"] != owner_prefix + [RUST_SRC_CORE["path"]]
        or rust_src["package_nevra"] != RUST_SRC_CORE["owner"]
        or rust_src["stderr_sha256"] != empty_digest
        or rust_src["stdout_sha256"] != RUST_SRC_CORE["stdout_sha256"]
    ):
        raise CaptureError("rust-src core identity differs")

    for probe_id, identity in sorted(CAPTURE_TOOL_PROBES.items()):
        probe = document["probes"][probe_id]
        _require_keys(
            probe,
            {
                "binary_path",
                "binary_resolved_path",
                "binary_sha256",
                "command",
                "owner_command",
                "package_nevra",
                "stderr_sha256",
                "stdout_sha256",
                "text",
            },
            "{} capture-tool probe".format(probe_id),
        )
        if (
            probe["binary_path"] != identity["path"]
            or probe["binary_resolved_path"] != identity["resolved_path"]
            or probe["command"] != identity["command"]
            or type(probe["package_nevra"]) is not str
            or re.fullmatch(identity["owner_regex"], probe["package_nevra"] or "")
            is None
            or re.fullmatch(r"[0-9a-f]{64}", probe["binary_sha256"] or "") is None
            or probe["stderr_sha256"] != empty_digest
            or type(probe["text"]) is not str
            or not probe["text"].strip()
            or "\x00" in probe["text"]
            or re.fullmatch(identity["version_regex"], probe["text"]) is None
            or probe["stdout_sha256"] == empty_digest
            or probe["stdout_sha256"] != _sha256(probe["text"].encode("utf-8"))
            or probe["owner_command"] != owner_prefix + [identity["path"]]
        ):
            raise CaptureError("{} capture-tool identity differs".format(probe_id))
    _require_exact(document, expected, "tool probe evidence in the exact capture runtime")


def verify_capture(repo, capture_dir):
    repo = _safe_directory(repo, "repository")
    contract, authority = validate_contract(repo)
    capture_dir = _safe_directory(capture_dir, "capture output")
    names = sorted(path.name for path in capture_dir.iterdir())
    if names != sorted(CAPTURE_MEMBERS):
        raise CaptureError("capture artifact member set differs")
    manifest_data, manifest_metadata = _read_rooted(capture_dir, "SHA256SUMS", "capture checksum manifest")
    if stat.S_IMODE(manifest_metadata.st_mode) != CAPTURE_MEMBER_MODE:
        raise CaptureError("capture checksum mode differs")
    manifest = _parse_checksum_manifest(manifest_data, "capture checksum manifest")
    if sorted(manifest) != sorted(name for name in CAPTURE_MEMBERS if name != "SHA256SUMS"):
        raise CaptureError("capture checksum member set differs")
    member_data = {}
    for name in sorted(manifest):
        data, metadata = _read_rooted(capture_dir, name, "capture member")
        if stat.S_IMODE(metadata.st_mode) != CAPTURE_MEMBER_MODE or _sha256(data) != manifest[name]:
            raise CaptureError("capture member checksum or mode differs: {}".format(name))
        member_data[name] = data
    document = _load_json_bytes(member_data["capture.json"], "capture document")
    if member_data["capture.json"] != _canonical_json(document):
        raise CaptureError("capture document is not canonical JSON")
    _validate_capture_document(document, allow_pending=True)
    for captured, expected in zip(document["patch_replay"], authority["patches"]):
        _require_keys(
            captured,
            {
                "after",
                "after_states",
                "before",
                "before_states",
                "id",
                "layer",
                "order",
                "patch_path",
                "patch_sha256",
            },
            "captured patch replay",
        )
        _require_exact(
            {
                "id": captured["id"],
                "layer": captured["layer"],
                "order": captured["order"],
                "patch_path": captured["patch_path"],
                "patch_sha256": captured["patch_sha256"],
            },
            {
                "id": expected["id"],
                "layer": expected["layer"],
                "order": expected["order"],
                "patch_path": expected["path"],
                "patch_sha256": expected["sha256"],
            },
            "captured authority patch identity",
        )
        for closure_name in ("before", "after"):
            closure = captured[closure_name]
            _require_keys(
                closure, {"algorithm", "row_count", "sha256"}, "patch closure"
            )
            if (
                closure["algorithm"]
                != "sha256-canonical-json-ordered-path-state-rows-v1"
                or closure["row_count"] != len(expected["touched_paths"])
                or type(closure["sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", closure["sha256"]) is None
            ):
                raise CaptureError("captured patch closure differs")
        for state_name in ("before_states", "after_states"):
            states = captured[state_name]
            if type(states) is not list or len(states) != len(expected["touched_paths"]):
                raise CaptureError("captured patch state count differs")
            for entry, relative in zip(states, expected["touched_paths"]):
                _require_keys(entry, {"archive_member", "state"}, "captured path state")
                state = entry["state"]
                if type(state) is not dict:
                    raise CaptureError("captured path state is not an object")
                if state.get("path") != relative or state.get("type") not in ("absent", "regular"):
                    raise CaptureError("captured path state identity differs")
                if state["type"] == "absent":
                    _require_exact(
                        state,
                        {"path": relative, "sha256": None, "size": None, "type": "absent"},
                        "absent path state",
                    )
                    if entry["archive_member"] is not None:
                        raise CaptureError("absent path has an archive member")
                else:
                    _require_keys(
                        state, {"mode", "path", "sha256", "size", "type"}, "regular path state"
                    )
                    if (
                        type(state["mode"]) is not str
                        or re.fullmatch(r"[0-7]{4}", state["mode"]) is None
                        or type(state["sha256"]) is not str
                        or re.fullmatch(r"[0-9a-f]{64}", state["sha256"]) is None
                        or type(state["size"]) is not int
                        or state["size"] < 0
                    ):
                        raise CaptureError("regular path state metadata differs")
                    expected_member = "patches/{:04d}/{}/{}".format(
                        expected["order"], expected["id"], relative
                    )
                    if entry["archive_member"] != expected_member:
                        raise CaptureError("path snapshot archive member differs")
    _validate_replay_relationships(document, authority, enforce_parent_hashes=True)
    source_expected = {
        key: {field: value for field, value in record.items() if field != "root"}
        for key, record in (
            ("source_archive", contract["inputs"]["source_archive"]),
            ("source_rpm", contract["inputs"]["source_rpm"]),
            ("vendor_patch", contract["inputs"]["vendor_patch"]),
        )
    }
    _require_exact(document["source_inputs"], source_expected, "captured source inputs")
    artifact_map = document["artifacts"]
    expected_artifacts = {
        "patch_apply_log_sha256": _sha256(member_data["patch-apply.log"]),
        "postimages_sha256": _sha256(member_data["postimages.tar.xz"]),
        "preimages_sha256": _sha256(member_data["preimages.tar.xz"]),
        "repository_inputs_sha256": _sha256(member_data["repository-inputs.tar.xz"]),
        "second_application_log_sha256": _sha256(member_data["second-application.log"]),
        "tool_probes_sha256": _sha256(member_data["tool-probes.json"]),
    }
    _require_exact(artifact_map, expected_artifacts, "captured artifact digests")
    if (
        type(document["repository_inputs"]) is not list
        or not document["repository_inputs"]
        or any(type(row) is not dict for row in document["repository_inputs"])
    ):
        raise CaptureError("captured repository input rows differ")
    repository_paths = []
    for row in document["repository_inputs"]:
        _require_keys(row, {"mode", "path", "sha256", "size"}, "repository input row")
        _safe_relative(row["path"], "repository input path")
        if (
            type(row["mode"]) is not str
            or re.fullmatch(r"[0-7]{4}", row["mode"]) is None
            or type(row["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
            or type(row["size"]) is not int
            or row["size"] < 0
        ):
            raise CaptureError("repository input row metadata differs")
        repository_paths.append(row["path"])
    if repository_paths != sorted(repository_paths) or len(repository_paths) != len(set(repository_paths)):
        raise CaptureError("repository input path set differs")
    _validate_repository_input_membership(document["repository_inputs"], authority)
    repository_tar_rows = _inspect_tar(member_data["repository-inputs.tar.xz"], "repository inputs")
    captured_repo_rows = [
        {"path": row["path"], "sha256": row["sha256"], "size": row["size"]}
        for row in document["repository_inputs"]
    ]
    _require_exact(repository_tar_rows, captured_repo_rows, "repository input archive")
    for row in document["repository_inputs"]:
        data, metadata = _read_rooted(repo, row["path"], "captured repository input")
        if (
            len(data) != row["size"]
            or _sha256(data) != row["sha256"]
            or "{:04o}".format(stat.S_IMODE(metadata.st_mode)) != row["mode"]
        ):
            raise CaptureError("captured repository input changed: {}".format(row["path"]))
    pre_rows = _inspect_tar(member_data["preimages.tar.xz"], "preimage archive")
    post_rows = _inspect_tar(member_data["postimages.tar.xz"], "postimage archive")
    expected_pre = sorted(
        [
            {"path": state["archive_member"], "sha256": state["state"]["sha256"], "size": state["state"]["size"]}
            for patch in document["patch_replay"]
            for state in patch["before_states"]
            if state["archive_member"] is not None
        ],
        key=lambda row: row["path"],
    )
    expected_post = sorted(
        [
            {"path": state["archive_member"], "sha256": state["state"]["sha256"], "size": state["state"]["size"]}
            for patch in document["patch_replay"]
            for state in patch["after_states"]
            if state["archive_member"] is not None
        ],
        key=lambda row: row["path"],
    )
    _require_exact(pre_rows, expected_pre, "preimage archive rows")
    _require_exact(post_rows, expected_post, "postimage archive rows")
    apply_rows = [
        _load_json_bytes((line + b"\n"), "patch apply log row")
        for line in member_data["patch-apply.log"].splitlines()
    ]
    second_rows = [
        _load_json_bytes((line + b"\n"), "second apply log row")
        for line in member_data["second-application.log"].splitlines()
    ]
    if member_data["patch-apply.log"] != b"".join(
        _canonical_json(row) for row in apply_rows
    ):
        raise CaptureError("patch apply log is not canonical JSONL")
    if member_data["second-application.log"] != b"".join(
        _canonical_json(row) for row in second_rows
    ):
        raise CaptureError("second application log is not canonical JSONL")
    if (
        len(apply_rows) != 26
        or any(type(row) is not dict for row in apply_rows)
        or apply_rows[0].get("kind") != "vendor-apply"
    ):
        raise CaptureError("patch apply log does not bind vendor plus 25 authority patches")
    if (
        len(second_rows) != 25
        or any(type(row) is not dict for row in second_rows)
        or any(row.get("returncode") == 0 for row in second_rows)
    ):
        raise CaptureError("second application rejection evidence differs")
    expected_ids = [row["id"] for row in authority["patches"]]
    if [row.get("id") for row in apply_rows[1:]] != expected_ids:
        raise CaptureError("patch apply log order differs")
    if [row.get("id") for row in second_rows] != expected_ids:
        raise CaptureError("second application log order differs")
    _validate_patch_logs(
        apply_rows,
        second_rows,
        authority,
        repo,
        contract["inputs"]["vendor_patch"]["filename"],
    )
    tool_probes = _load_json_bytes(member_data["tool-probes.json"], "tool probes")
    if member_data["tool-probes.json"] != _canonical_json(tool_probes):
        raise CaptureError("tool probe document is not canonical JSON")
    _validate_tool_probe_document(tool_probes)
    binding = _load_json_bytes(member_data["build-binding.json"], "build binding")
    if member_data["build-binding.json"] != _canonical_json(binding):
        raise CaptureError("build binding is not canonical JSON")
    _require_exact(binding.get("claims"), FALSE_CLAIMS, "build binding claims")
    if document["state"] == "source-capture-complete":
        expected_pending = {
            "build_artifact": {
                "durable": False,
                "name": "native-rust-exact-build-{}-{}".format(
                    document["github"]["run_id"], document["github"]["run_attempt"]
                ),
                "outer_artifact_sha256": None,
                "retention_days": 30,
            },
            "claims": dict(FALSE_CLAIMS),
            "schema_version": 1,
            "status": "required-pending",
        }
        if not _strict_equal(binding, expected_pending) or document["build_binding"] != {"build_binding_sha256": None, "status": "required-pending"}:
            raise CaptureError("pending build boundary differs")
        if member_data["workflow-state"] != b"source-capture-complete\n":
            raise CaptureError("pending workflow state differs")
    else:
        _require_keys(
            binding,
            {"build_artifact", "build_evidence", "claims", "schema_version", "status"},
            "final build binding",
        )
        artifact = binding["build_artifact"]
        _require_keys(
            artifact,
            {
                "content_closure_algorithm",
                "content_closure_sha256",
                "durable",
                "file_count",
                "name",
                "outer_artifact_sha256",
                "retention_days",
                "sha256sums_sha256",
            },
            "bound build artifact",
        )
        rows = binding["build_evidence"]
        if type(rows) is not list or any(type(row) is not dict for row in rows):
            raise CaptureError("bound build evidence rows differ")
        paths = []
        for row in rows:
            _require_keys(row, {"path", "sha256", "size"}, "bound build evidence row")
            _safe_relative(row["path"], "bound build evidence path")
            if (
                "/" in row["path"]
                or type(row["sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
                or type(row["size"]) is not int
                or row["size"] < 0
            ):
                raise CaptureError("bound build evidence row metadata differs")
            paths.append(row["path"])
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise CaptureError("bound build evidence path set differs")
        if not set(name for name in REQUIRED_BUILD_MEMBERS if name != "SHA256SUMS").issubset(paths):
            raise CaptureError("bound build evidence misses required members")
        expected_name = "native-rust-exact-build-{}-{}".format(
            document["github"]["run_id"], document["github"]["run_attempt"]
        )
        if (
            binding.get("schema_version") != 1
            or binding.get("status") != "technical-build-bound-unreviewed"
            or artifact["content_closure_algorithm"]
            != "sha256-canonical-json-build-evidence-rows-v1"
            or artifact["content_closure_sha256"] != _sha256(_canonical_json(rows))
            or artifact["durable"] is not False
            or artifact["file_count"] != len(rows) + 1
            or artifact["name"] != expected_name
            or artifact["outer_artifact_sha256"] is not None
            or artifact["retention_days"] != 30
            or type(artifact["sha256sums_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", artifact["sha256sums_sha256"]) is None
        ):
            raise CaptureError("final build boundary differs")
        if document["build_binding"] != {"build_binding_sha256": _sha256(member_data["build-binding.json"]), "status": "technical-build-bound-unreviewed"}:
            raise CaptureError("build binding digest differs")
        if member_data["workflow-state"] != b"technical-build-bound-unreviewed\n":
            raise CaptureError("final workflow state differs")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    check = subparsers.add_parser("check-contract")
    check.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--repo", required=True)
    capture_parser.add_argument("--source-root", required=True)
    capture_parser.add_argument("--source-archive", required=True)
    capture_parser.add_argument("--source-rpm", required=True)
    capture_parser.add_argument("--vendor-patch", required=True)
    capture_parser.add_argument("--output-dir", required=True)
    capture_parser.add_argument("--github-head-sha", required=True)
    capture_parser.add_argument("--github-run-id", required=True)
    capture_parser.add_argument("--github-run-attempt", required=True)
    capture_parser.add_argument("--github-repository", required=True)
    capture_parser.add_argument("--container-image", required=True)
    finalize = subparsers.add_parser("finalize-build")
    finalize.add_argument("--repo", required=True)
    finalize.add_argument("--capture-dir", required=True)
    finalize.add_argument("--build-evidence-dir", required=True)
    verify = subparsers.add_parser("verify-capture")
    verify.add_argument("--repo", required=True)
    verify.add_argument("--capture-dir", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check-contract":
            contract, authority = validate_contract(args.repo)
            print(
                "RK-006 full-source/build capture contract: VALID "
                "(non-crediting; {} authority patches)".format(len(authority["patches"]))
            )
        elif args.command == "capture":
            result = capture(args)
            print(
                "RK-006 source capture: COMPLETE (non-crediting; {} patches; build pending)".format(
                    result["patch_count"]
                )
            )
        elif args.command == "finalize-build":
            result = finalize_build(args.repo, args.capture_dir, args.build_evidence_dir)
            print(
                "RK-006 build binding: CAPTURED-UNREVIEWED (non-crediting; {} files)".format(
                    result["build_artifact"]["file_count"]
                )
            )
        elif args.command == "verify-capture":
            result = verify_capture(args.repo, args.capture_dir)
            print("RK-006 capture: VALID {} (credit forbidden)".format(result["state"]))
        else:
            parser.error("a command is required")
    except CaptureError as exc:
        print("RK-006 full-source/build capture: FAIL: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
