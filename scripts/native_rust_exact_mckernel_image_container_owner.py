#!/usr/bin/env python3
"""Reviewed owner for one isolated current-source McKernel image build.

This module is an admission/transport boundary around the offline image
driver.  It does not relocate sources, install software, or perform a guest
operation.  A real invocation creates exactly one private, read-only-root
container under the reviewed 4 CPU/12 GiB lease; tests inject a fake Docker
transport and never contact Docker.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import types
import uuid


REQUEST_SCHEMA = "mckernel.native-exact-mckernel-image-container-request.v1"
RECEIPT_SCHEMA = "mckernel.native-exact-mckernel-image-container-receipt.v1"
OWNER_RECEIPT_NAME = "owner-receipt.json"
EXPECTED_DRIVER_SHA256 = "0535385e0866e20a2d8c6401683e1746453711e9ab14058b6a654faac719a116"
EXPECTED_PROVENANCE_SHA256 = "1993f3ddcf0be925d53a966fad34bed40cb70d4202ac516f1fa6a9b9b81ba388"
EXPECTED_HOST_OWNER_SHA256 = "a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155"
COMMON_EXCLUSION = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-97fb67a7-3.json"
LIMITS = {
    "NanoCpus": 4_000_000_000, "CpusetCpus": "2-5",
    "Memory": 12 * 2**30, "MemorySwap": 12 * 2**30,
    "PidsLimit": 512, "NetworkMode": "none",
}
RESOURCE_ARGS = ("--cpus=4", "--cpuset-cpus=2-5", "--memory=12g",
                 "--memory-swap=12g", "--pids-limit=512")
MAX_TIMEOUT = 19_800
LAUNCHER_AGGREGATE_GIB = "16.2158"
LAUNCHER_AGGREGATE_BYTES = int(Decimal(LAUNCHER_AGGREGATE_GIB) * 2**30)
REQUIRED_TOOLS = ("cmake", "cc", "rustc", "nm", "readelf", "make", "ld",
                  "objcopy", "ar", "ranlib", "git")
SUDO_DOCKER_PREFIX = ("/usr/bin/sudo", "-A", "/usr/bin/docker",
                      "--host=unix:///var/run/docker.sock")


def _load_reviewed_host_owner(path, host_sha256=None, provenance_path=None,
                              provenance_sha256=None):
    """Load reviewed owner/provenance from authenticated source bytes only."""
    path = Path(path)
    provenance_path = (path.with_name("native_rust_exact_build_offline.py")
                       if provenance_path is None else Path(provenance_path))
    def source_bytes(candidate, expected, label):
        if not (candidate.is_absolute() and candidate.is_file() and not candidate.is_symlink()):
            raise RuntimeError(label + " is not a regular source file")
        current = Path(candidate.anchor)
        for component in candidate.parts[1:]:
            current /= component
            if current.is_symlink():
                raise RuntimeError(label + " has symlink parent")
        before = os.lstat(candidate)
        data = candidate.read_bytes()
        after = os.lstat(candidate)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mode) != \
                (after.st_dev, after.st_ino, after.st_size, after.st_mode):
            raise RuntimeError(label + " identity changed during import")
        observed = hashlib.sha256(data).hexdigest()
        if expected is not None:
            if observed != expected:
                raise RuntimeError(label + " hash mismatch")
        return data
    host_bytes = source_bytes(path, host_sha256, "host owner")
    provenance_bytes = source_bytes(provenance_path, provenance_sha256, "host provenance")
    package_name = "_mckernel_reviewed_exact_owner_%d" % os.getpid()
    package = types.ModuleType(package_name)
    package.__path__ = [str(path.parent)]
    package.__package__ = package_name
    sys.modules[package_name] = package
    provenance_name = package_name + ".native_rust_exact_build_offline"
    host_name = package_name + ".native_rust_exact_build_container_owner"
    provenance = types.ModuleType(provenance_name)
    provenance.__package__ = package_name
    provenance.__file__ = str(provenance_path)
    host = types.ModuleType(host_name)
    host.__package__ = package_name
    host.__file__ = str(path)
    sys.modules[provenance_name] = provenance
    sys.modules[host_name] = host
    try:
        exec(compile(provenance_bytes, str(provenance_path), "exec"), provenance.__dict__)
        exec(compile(host_bytes, str(path), "exec"), host.__dict__)
        return host
    finally:
        sys.modules.pop(host_name, None)
        sys.modules.pop(provenance_name, None)
        sys.modules.pop(package_name, None)


_HOST_OWNER_PATH = Path(__file__).with_name("native_rust_exact_build_container_owner.py")
_HOST_OWNER = _load_reviewed_host_owner(
    _HOST_OWNER_PATH, EXPECTED_HOST_OWNER_SHA256,
    _HOST_OWNER_PATH.with_name("native_rust_exact_build_offline.py"),
    EXPECTED_PROVENANCE_SHA256)


class OwnerError(RuntimeError):
    pass


def _fail(condition, message):
    if not condition:
        raise OwnerError(message)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_dir(path):
    fd = os.open(Path(path), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    _fsync_dir(path.parent)


def _exclusive_json(path, value):
    """Publish one receipt without following links or overwriting evidence."""
    path = Path(path)
    _no_symlink_parents(path, "receipt path")
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            _fail(written > 0, "receipt short write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path.parent)


def _exclusive_text(path, text):
    path = Path(path)
    _no_symlink_parents(path, "evidence path")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        payload = text.encode("utf-8", "replace")
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            _fail(written > 0, "evidence short write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(path.parent)


def _canonical(path, label, directory=False):
    path = Path(path)
    _fail(path.is_absolute() and not path.is_symlink() and path.exists(), label + " missing")
    resolved = path.resolve(strict=True)
    _fail(resolved == path, label + " is not canonical")
    if directory:
        _fail(resolved.is_dir(), label + " must be a directory")
    return resolved


def _regular(path, label):
    path = _canonical(path, label)
    _fail(stat.S_ISREG(path.lstat().st_mode), label + " must be regular")
    return path


def _safe_regular(path, label):
    """Validate a regular file without following a leaf or ancestor link."""
    path = Path(path)
    _no_symlink_parents(path, label)
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise OwnerError(label + " missing") from exc
    _fail(stat.S_ISREG(info.st_mode), label + " must be a regular file")
    return path


def _safe_directory(path, label):
    """Validate a directory and every path component without following links."""
    path = Path(path)
    _no_symlink_parents(path, label)
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise OwnerError(label + " missing") from exc
    _fail(stat.S_ISDIR(info.st_mode), label + " must be a directory")
    return path


def _no_symlink_parents(path, label):
    path = Path(path)
    _fail(path.is_absolute(), label + " must be absolute")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        _fail(not current.is_symlink(), label + " has symlink parent")


def _confined_path(path, label):
    """Require an absolute path whose leaf and every ancestor are real."""
    path = Path(path)
    _no_symlink_parents(path, label)
    _fail(path.is_absolute(), label + " must be absolute")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if current == path:
            continue
        _fail(current.exists() and current.is_dir(), label + " has non-directory ancestor")
    if path.exists():
        _fail(path.resolve(strict=True) == path, label + " is not canonical")
    return path


def _disjoint(paths):
    roots = [Path(path).resolve(strict=False) for path in paths]
    for index, left in enumerate(roots):
        for right in roots[index + 1:]:
            _fail(left != right and left not in right.parents and right not in left.parents,
                  "bound roots overlap")


def _load_json(path, label):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OwnerError("malformed " + label) from exc
    _fail(isinstance(value, dict), label + " must be an object")
    return value


def _identity(path):
    info = os.lstat(path)
    return {"path": str(Path(path).resolve(strict=True)), "dev": info.st_dev,
            "inode": info.st_ino, "uid": info.st_uid, "gid": info.st_gid,
            "mode": stat.S_IMODE(info.st_mode), "file_type": stat.S_IFMT(info.st_mode)}


def _tree_inventory(root):
    root = Path(root)
    observed = {}
    for item in sorted(root.rglob("*")):
        st = item.lstat()
        _fail(not stat.S_ISLNK(st.st_mode), "inventory contains symlink")
        _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),
              "inventory contains special file")
        row = {"mode": stat.S_IMODE(st.st_mode),
               "type": "directory" if stat.S_ISDIR(st.st_mode) else "file"}
        if stat.S_ISREG(st.st_mode):
            row.update(size=st.st_size, sha256=_sha256(item))
        observed[str(item.relative_to(root))] = row
    return observed


def _check_identity(path, expected, label, directory=True):
    actual = _identity(path)
    _fail(isinstance(expected, dict), label + " identity missing")
    for key in ("path", "dev", "inode", "uid", "gid", "mode", "file_type"):
        _fail(expected.get(key) == actual[key], label + " identity changed: " + key)
    if directory:
        _fail(actual["file_type"] == stat.S_IFDIR, label + " is not a directory")
    return actual


def _toolchain_roots(request):
    rows = request.get("toolchain_roots")
    _fail(isinstance(rows, list) and rows, "toolchain_roots are required")
    seen = []
    for row in rows:
        _fail(isinstance(row, dict) and set(row) == {"path", "inventory"}, "toolchain root row")
        path = _canonical(row.get("path", ""), "toolchain root", directory=True)
        inventory = row.get("inventory")
        _fail(isinstance(inventory, dict) and inventory, "toolchain root inventory")
        observed = {}
        for item in path.rglob("*"):
            relative = str(item.relative_to(path))
            st = item.lstat()
            _fail(not stat.S_ISLNK(st.st_mode), "toolchain root contains symlink")
            _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),
                  "toolchain root contains special file")
            row_data = {"mode": stat.S_IMODE(st.st_mode),
                        "type": "directory" if stat.S_ISDIR(st.st_mode) else "file"}
            if stat.S_ISREG(st.st_mode):
                row_data.update(size=st.st_size, sha256=_sha256(item))
            observed[relative] = row_data
        _fail(observed == inventory, "toolchain root inventory differs")
        for other in seen:
            _fail(path != other and path not in other.parents and other not in path.parents,
                  "toolchain roots overlap")
        seen.append(path)
    return seen


def _authenticated_provenance(path):
    module_name = "_mckernel_exact_owner_provenance_%d" % os.getpid()
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(module_name, loader=None))
    try:
        exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    except BaseException as exc:
        raise OwnerError("authenticated provenance import failed") from exc
    return module


def _git_factory(tool):
    tool_path = tool["path"]
    def git(root, *args):
        command = [tool_path, "-c", "safe.directory=" + str(root),
                   "-c", "core.fsmonitor=", "-c", "core.hooksPath=/dev/null",
                   "-C", str(root), *args]
        env = {"PATH": str(Path(tool_path).parent), "GIT_OPTIONAL_LOCKS": "0",
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
               "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
               "LANG": "C", "LC_ALL": "C"}
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, timeout=30, check=False)
        _fail(result.returncode == 0 and not result.stderr,
              "authenticated Git command failed")
        return result.stdout
    return git


def _validate_authenticated_source(source, manifest, candidate, ihk, toolchain_doc, provenance_path):
    provenance = _authenticated_provenance(provenance_path)
    git = _git_factory(toolchain_doc["tools"]["git"])
    try:
        _fail(git(source, "rev-parse", "HEAD").decode().strip() == candidate,
              "source HEAD differs from candidate")
        ihk_root = _canonical(source / "ihk", "IHK checkout", directory=True)
        _fail(git(ihk_root, "rev-parse", "HEAD").decode().strip() == ihk,
              "IHK HEAD differs from manifest")
        production = ihk == provenance.REVIEWED_IHK_HEAD
        if production:
            provenance.verify_ihk_overlay(source, git, applied=True)
        files, links = provenance.source_inventory(source, git, allow_ihk_overlay=production)
    except BaseException as exc:
        if isinstance(exc, OwnerError):
            raise
        raise OwnerError("authenticated source admission failed: " + str(exc)) from exc
    _fail(manifest.get("repository_files") == files, "source inventory differs")
    _fail(manifest.get("gitlinks") == links, "source gitlink inventory differs")


def _proc_starttime(pid):
    """Capture the process identity needed by the image common exclusion."""
    return Path("/proc").joinpath(str(pid), "stat").read_text().rsplit(")", 1)[1].split()[19]


def _validate_request(request):
    _fail(isinstance(request, dict) and request.get("schema") == REQUEST_SCHEMA,
          "request schema")
    candidate = request.get("candidate_sha")
    ihk = request.get("ihk_sha")
    _fail(isinstance(candidate, str) and re.fullmatch(r"[0-9a-f]{40}", candidate),
          "candidate identity")
    _fail(isinstance(ihk, str) and re.fullmatch(r"[0-9a-f]{40}", ihk), "IHK identity")
    _fail(isinstance(request.get("image_id"), str) and
          re.fullmatch(r"sha256:[0-9a-f]{64}", request["image_id"]), "image identity")
    _fail(1 <= request.get("jobs", 0) <= 4 and isinstance(request.get("jobs"), int),
          "jobs exceed reviewed bound")
    _fail(1 <= request.get("timeout", 0) <= MAX_TIMEOUT and isinstance(request.get("timeout"), int),
          "timeout exceeds reviewed bound")
    _fail(request.get("launcher_aggregate_memory_gib") == LAUNCHER_AGGREGATE_GIB,
          "launcher aggregate must be exactly 16.2158 GiB")
    memory_effect = request.get("memory_backed_bytes")
    _fail(isinstance(memory_effect, int) and not isinstance(memory_effect, bool) and memory_effect == 0,
          "memory-backed source bytes are not zero")
    aggregate = request.get("aggregate_memory_required")
    _fail(aggregate == LIMITS["Memory"] and aggregate + memory_effect <= LAUNCHER_AGGREGATE_BYTES,
          "aggregate memory admission failed")
    disk_admission = request.get("disk_admission")
    _fail(isinstance(disk_admission, dict), "disk admission manifest missing")
    _fail(disk_admission.get("host_free_floor") == 16 * 2**30 and
          disk_admission.get("scratch_free_floor") == 12 * 2**30,
          "disk admission floors differ")
    host_measure = _canonical(disk_admission.get("host_root", ""), "host measurement root", directory=True)
    scratch_measure = _canonical(disk_admission.get("scratch_root", ""), "scratch measurement root", directory=True)
    _fail(shutil.disk_usage(host_measure).free >= 16 * 2**30, "host disk floor failed")
    _fail(shutil.disk_usage(scratch_measure).free >= 12 * 2**30, "scratch disk floor failed")
    _fail(isinstance(disk_admission.get("host_device"), int) and
          os.stat(host_measure).st_dev == disk_admission["host_device"], "host device changed")
    _fail(isinstance(disk_admission.get("scratch_device"), int) and
          os.stat(scratch_measure).st_dev == disk_admission["scratch_device"], "scratch device changed")
    allocation_roots = request.get("memory_allocation_roots")
    _fail(isinstance(allocation_roots, list) and allocation_roots,
          "memory allocation roots missing")
    allocation_paths = [_canonical(item, "memory allocation root", directory=True)
                        for item in allocation_roots]
    source = _canonical(request.get("source_root", ""), "source root", directory=True)
    _fail(source in allocation_paths and len(set(allocation_paths)) == len(allocation_paths),
          "memory allocation roots do not bind source")
    owner_evidence = _canonical(request.get("owner_evidence_root", ""),
                                "owner evidence root", directory=True)
    _no_symlink_parents(owner_evidence, "owner evidence root")
    _fail(not any(owner_evidence.iterdir()), "owner evidence root must be fresh")
    work_root = _canonical(request.get("work_root", ""), "dedicated work root", directory=True)
    _fail(stat.S_IMODE(work_root.stat().st_mode) == 0o700,
          "dedicated work root must be mode 0700")
    attempt = _confined_path(request.get("attempt_root", ""), "attempt root")
    _fail(not attempt.exists() and attempt.parent == owner_evidence,
          "attempt root must be private and absent")
    receipt_path = _confined_path(owner_evidence / OWNER_RECEIPT_NAME, "owner receipt")
    _fail(not receipt_path.exists() and not receipt_path.is_symlink(),
          "owner receipt must be fresh")
    output = _confined_path(request.get("output_root", ""), "output root")
    evidence = _confined_path(request.get("evidence_root", ""), "evidence root")
    for path, label in ((output, "output root"), (evidence, "evidence root")):
        _fail(not path.exists() and not path.is_symlink(), label + " must be fresh")
        _fail(path.parent.exists() and path.parent.is_dir(), label + " parent missing")
    _fail(not any(work_root.iterdir()), "dedicated work root must be empty")
    _fail(output.parent == work_root and evidence.parent == work_root,
          "output/evidence must be direct children of dedicated work root")
    manifest = _regular(request.get("source_manifest", ""), "source manifest")
    toolchain = _regular(request.get("toolchain_manifest", ""), "toolchain manifest")
    driver = _regular(request.get("driver_path", ""), "offline driver")
    provenance = _regular(request.get("provenance_path", ""), "offline provenance")
    host_owner = _regular(request.get("host_owner_path", ""), "host owner")
    _fail(request.get("driver_sha256") == EXPECTED_DRIVER_SHA256, "offline driver release hash")
    _fail(_sha256(driver) == EXPECTED_DRIVER_SHA256, "offline driver bytes differ")
    _fail(isinstance(request.get("provenance_sha256"), str) and
          re.fullmatch(r"[0-9a-f]{64}", request["provenance_sha256"]),
          "offline provenance hash binding")
    _fail(_sha256(provenance) == request["provenance_sha256"],
          "offline provenance bytes differ")
    _fail(request["provenance_sha256"] == EXPECTED_PROVENANCE_SHA256,
          "offline provenance release hash")
    _fail(isinstance(request.get("host_owner_sha256"), str) and
          re.fullmatch(r"[0-9a-f]{64}", request["host_owner_sha256"]),
          "host owner hash binding")
    _fail(_sha256(host_owner) == request["host_owner_sha256"],
          "host owner bytes differ")
    _fail(request["host_owner_sha256"] == EXPECTED_HOST_OWNER_SHA256,
          "host owner release hash")
    for path, label, key in ((manifest, "source manifest", "source_manifest_sha256"),
                             (toolchain, "toolchain manifest", "toolchain_manifest_sha256")):
        _fail(isinstance(request.get(key), str) and re.fullmatch(r"[0-9a-f]{64}", request[key]),
              label + " hash binding")
        _fail(_sha256(path) == request[key], label + " hash drift")
    source_doc = _load_json(manifest, "source manifest")
    _fail(source_doc.get("candidate_sha") == candidate and source_doc.get("ihk_sha") == ihk,
          "source manifest identity differs")
    _fail(source_doc.get("schema") in ("mckernel.native-exact-mckernel-image-inputs.v1",
                                        "mckernel.native-exact-build-inputs.v1"),
          "source manifest schema")
    _fail(isinstance(request.get("source_identity"), dict), "source identity missing")
    _check_identity(source, request["source_identity"], "source root")
    disk = request.get("disk_identity")
    _fail(isinstance(disk, dict) and disk.get("path") == str(source), "disk identity binding")
    _check_identity(source, disk, "disk candidate")
    roots = _toolchain_roots(request)
    toolchain_doc = _load_json(toolchain, "toolchain manifest")
    _fail(toolchain_doc.get("schema") == "mckernel.native-exact-mckernel-image-toolchain.v1",
          "toolchain manifest schema")
    tools = toolchain_doc.get("tools")
    _fail(isinstance(tools, dict) and all(name in tools for name in REQUIRED_TOOLS),
          "toolchain tools incomplete")
    _fail(isinstance(toolchain_doc.get("kernel_dir"), str), "kernel directory binding")
    kernel_dir = _canonical(toolchain_doc["kernel_dir"], "kernel directory", directory=True)
    for name in REQUIRED_TOOLS:
        descriptor = tools[name]
        _fail(isinstance(descriptor, dict) and isinstance(descriptor.get("path"), str) and
              isinstance(descriptor.get("sha256"), str) and
              re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"]) and
              isinstance(descriptor.get("version"), str) and descriptor["version"],
              "toolchain tool identity incomplete: " + name)
        tool_path = _regular(descriptor["path"], "tool " + name)
        _fail(_sha256(tool_path) == descriptor["sha256"], "tool hash drift: " + name)
    _fail(isinstance(toolchain_doc.get("kernel_inventory"), dict) and
          _tree_inventory(kernel_dir) == toolchain_doc["kernel_inventory"],
          "kernel inventory differs")
    _fail(toolchain_doc.get("toolchain_roots") == request.get("toolchain_roots"),
          "toolchain root manifest differs")
    _fail(toolchain_doc.get("path_dirs") == request.get("path_dirs"),
          "PATH manifest differs")
    _fail(isinstance(toolchain_doc.get("linux_probe"), dict) and
          toolchain_doc["linux_probe"].get("kernel_dir") == str(kernel_dir),
          "Linux probe manifest differs")
    _fail(isinstance(toolchain_doc.get("environment"), dict) and not toolchain_doc["environment"],
          "toolchain environment is not sealed")
    _fail(isinstance(toolchain_doc["tools"].get("rustc"), dict), "toolchain Rust identity")
    rust_version = toolchain_doc["tools"]["rustc"].get("version", "")
    _fail(isinstance(rust_version, str) and "nightly" in rust_version.lower(),
          "toolchain Rust is not nightly")
    _validate_authenticated_source(source, source_doc, candidate, ihk, toolchain_doc, provenance)
    backup_raw = request.get("backup_root", request.get("source_backup_root"))
    backup = _canonical(backup_raw, "source backup", directory=True)
    _check_identity(backup, request.get("backup_identity"), "source backup")
    _fail(isinstance(request.get("backup_inventory"), dict) and request["backup_inventory"],
          "source backup inventory missing")
    _fail(_tree_inventory(backup) == request["backup_inventory"],
          "source backup inventory differs")
    path_dirs = request.get("path_dirs")
    _fail(isinstance(path_dirs, list) and path_dirs, "path_dirs manifest missing")
    for row in path_dirs:
        _fail(isinstance(row, str), "path_dirs row")
        path = _canonical(row, "path_dirs entry", directory=True)
        _fail(any(path == other or other in path.parents for other in roots),
              "PATH directory escapes toolchain roots")
    nightly = request.get("nightly")
    _fail(isinstance(nightly, dict) and isinstance(nightly.get("rustc_version"), str) and
          "nightly" in nightly["rustc_version"].lower(), "nightly manifest")
    _fail(request.get("mounts") == {"source": "/src", "manifest": "/inputs.json",
                                 "toolchain": "/toolchain.json", "driver": "/driver.py",
                                 "provenance": "/native_rust_exact_build_offline.py",
                                 "work": "/work"},
          "mount manifest differs")
    common = request.get("common_exclusion_path")
    _fail(common == COMMON_EXCLUSION, "common exclusion path differs")
    lease = _regular(request.get("lease_path", ""), "lease path") if Path(request.get("lease_path", "")).exists() else Path(request.get("lease_path", ""))
    _no_symlink_parents(lease, "lease path")
    _disjoint((source, manifest, toolchain, driver, provenance, host_owner,
               owner_evidence, work_root, *roots, backup, kernel_dir))
    _fail(work_root != owner_evidence and work_root not in owner_evidence.parents and
          owner_evidence not in work_root.parents, "work/evidence roots overlap")
    try:
        authenticated_host = _load_reviewed_host_owner(
            host_owner, request["host_owner_sha256"], provenance,
            request["provenance_sha256"])
    except (OSError, RuntimeError, SyntaxError) as exc:
        raise OwnerError("authenticated host owner import failed: " + str(exc)) from exc
    try:
        measurement = authenticated_host.measure(
            host_measure, scratch_measure, 16 * 2**30, 12 * 2**30,
            source_root=source, output_root=work_root,
            memory_allocation_roots=allocation_paths)
    except (OSError, RuntimeError, ValueError) as exc:
        raise OwnerError("resource/allocation measurement failed: " + str(exc)) from exc
    _fail(measurement.get("memory_allocation_memory_backed_bytes") == memory_effect,
          "measured memory-backed allocation differs")
    _fail(measurement.get("aggregate_memory_required") == aggregate,
          "measured aggregate memory differs")
    return {"source": source, "manifest": manifest, "toolchain": toolchain,
            "driver": driver, "provenance": provenance, "output": output, "evidence": evidence,
            "owner_evidence": owner_evidence, "attempt": attempt,
            "work": work_root, "backup": backup, "measurement": measurement,
            "host_owner": authenticated_host,
            "host_owner_path": host_owner, "roots": roots, "kernel": kernel_dir,
            "allocation_roots": allocation_paths,
            "path_dirs": [_canonical(row, "PATH directory", directory=True)
                                                                  for row in path_dirs],
            "lease": lease}


class CommonExclusion:
    def __init__(self, path, request):
        self.path = Path(path); self.request = request; self.record = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.record = {"schema": "mckernel.native-exact-operational-exclusion.v1",
                       "pid": os.getpid(), "starttime": _proc_starttime(os.getpid()),
                       "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                       "request_sha256": hashlib.sha256(json.dumps(self.request, sort_keys=True).encode()).hexdigest()}
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise OwnerError("common exclusion exists; reconciliation required") from exc
        identity = os.fstat(fd)
        self.record.update({"dev": identity.st_dev, "inode": identity.st_ino})
        payload = (json.dumps(self.record, sort_keys=True) + "\n").encode()
        offset = 0
        try:
            while offset < len(payload):
                written = os.write(fd, payload[offset:])
                _fail(isinstance(written, int) and written > 0, "common exclusion short write")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_dir(self.path.parent)


def _check_profile(info, image, nonce, mounts=None, command=None, user=None,
                   host_owner=None):
    (host_owner or _HOST_OWNER).check_profile(info, image, nonce)
    config = info.get("Config", {})
    if command is not None:
        _fail(config.get("Entrypoint") == ["/usr/bin/python3"] and config.get("Cmd") == command,
              "effective driver command mismatch")
    if user is not None:
        _fail(config.get("User") == user, "effective container user mismatch")
    if mounts is not None:
        expected = {(str(source), target, not readonly) for source, target, readonly in mounts}
        actual = {(row.get("Source"), row.get("Destination"), row.get("RW"))
                  for row in info.get("Mounts", []) if row.get("Type") == "bind"}
        _fail(actual == expected, "effective bind mounts mismatch")
        _fail(all(row.get("Type") in ("bind", "tmpfs") for row in info.get("Mounts", [])),
              "unexpected effective mount type")
        tmpfs_mounts = [row for row in info.get("Mounts", []) if row.get("Type") == "tmpfs"]
        _fail(not tmpfs_mounts or (len(tmpfs_mounts) == 1 and
              tmpfs_mounts[0].get("Destination") == "/tmp" and
              tmpfs_mounts[0].get("RW") is True), "unexpected effective tmpfs mount")
    tmpfs = config_host = info.get("HostConfig", {}).get("Tmpfs")
    _fail(tmpfs == {"/tmp": "rw,nodev,nosuid,size=256m"},
          "effective tmpfs profile mismatch")


# The accepted host owner supplies the reviewed lease, signal, Docker transport,
# inspection, and retirement semantics.  Image-specific admission remains local.
Lease = _HOST_OWNER.Lease
Docker = _HOST_OWNER.Docker
Signals = _HOST_OWNER.CliSignals
_inspect = _HOST_OWNER.inspect
_retire = _HOST_OWNER.retire


def _validate_driver_result(evidence, output, result, request):
    evidence = _safe_directory(evidence, "driver evidence root")
    output = _safe_directory(output, "driver output root")
    _fail(result.get("status") == "PASS", "driver receipt is not PASS")
    _fail(result.get("candidate_sha") == request["candidate_sha"] and
          result.get("ihk_sha") == request["ihk_sha"], "driver receipt identity differs")
    _fail(result.get("source_manifest_sha256") == request["source_manifest_sha256"] and
          result.get("toolchain_manifest_sha256") == request["toolchain_manifest_sha256"],
          "driver receipt provenance differs")
    inventory = result.get("inventory")
    _fail(isinstance(inventory, dict), "driver evidence inventory missing")
    observed_inventory = {}
    for item in sorted(evidence.rglob("*")):
        st = item.lstat()
        _fail(not stat.S_ISLNK(st.st_mode), "driver evidence contains symlink")
        _fail(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode),
              "driver evidence contains special file")
        if item.is_file() and item.relative_to(evidence) != Path("receipt.json"):
            relative = item.relative_to(evidence)
            _fail(not relative.is_absolute() and ".." not in relative.parts,
                  "driver evidence inventory path escapes root")
            observed_inventory[str(relative)] = {
                "size": item.stat().st_size, "sha256": _sha256(item)}
    for relative, metadata in inventory.items():
        relative_path = Path(relative)
        _fail(not relative_path.is_absolute() and ".." not in relative_path.parts and
              str(relative_path) == relative, "driver evidence inventory path is not canonical")
        path = _safe_regular(evidence / relative_path, "driver evidence member")
        _fail(isinstance(metadata, dict) and metadata.get("size") == path.stat().st_size and
              metadata.get("sha256") == _sha256(path), "driver evidence inventory drift")
    _fail(set(observed_inventory) == set(inventory),
          "driver evidence inventory is incomplete or has unexpected members")
    expected = {"mckernel.img", "mckernel.img.map", "CMakeCache.txt", "compile_commands.json",
                "mckernel_rust.o", "build.make"}
    copied = result.get("evidence_artifacts")
    _fail(isinstance(copied, dict) and set(copied) >= expected,
          "driver artifact inventory incomplete")
    for name in expected:
        relative = {"mckernel.img": "mckernel.img", "mckernel.img.map": "mckernel.img.map",
                    "CMakeCache.txt": "CMakeCache.txt", "compile_commands.json": "compile_commands.json",
                    "mckernel_rust.o": "mckernel_rust.o", "build.make": "build.make"}[name]
        path = evidence / "artifacts" / relative
        row = copied[name]
        _safe_regular(path, "driver evidence artifact")
        _fail(
              str(row.get("path", "")).replace("\\", "/").endswith("/artifacts/" + relative),
              "driver artifact path differs: " + name)
        _fail(row.get("size") == path.stat().st_size and row.get("sha256") == _sha256(path),
              "driver artifact hash differs: " + name)
        _fail(row.get("path") == "/work/evidence/artifacts/" + name,
              "driver artifact path is not canonical: " + name)
    artifacts = result.get("artifacts")
    _fail(isinstance(artifacts, dict) and set(artifacts) >= expected,
          "driver output artifact inventory incomplete")
    output_paths = {"mckernel.img": output / "build/kernel/mckernel.img",
                    "mckernel.img.map": output / "build/kernel/mckernel.img.map",
                    "CMakeCache.txt": output / "build/CMakeCache.txt",
                    "compile_commands.json": output / "build/compile_commands.json",
                    "mckernel_rust.o": output / "build/kernel/rust/mckernel_rust.o",
                    "build.make": output / "build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make"}
    for name, path in output_paths.items():
        row = artifacts[name]
        output_rel = path.relative_to(output)
        _fail(row.get("path") == "/work/output/" + output_rel.as_posix(),
              "driver output artifact path is not canonical: " + name)
        _safe_regular(path, "driver output artifact")
        _fail(row.get("size") == path.stat().st_size and
              row.get("sha256") == _sha256(path), "driver output hash differs: " + name)


def _revalidate_inputs(bound, request):
    _check_identity(bound["source"], request["source_identity"], "source root")
    _check_identity(bound["backup"], request["backup_identity"], "source backup")
    _fail(_tree_inventory(bound["backup"]) == request["backup_inventory"],
          "source backup inventory changed")
    _fail(_sha256(bound["manifest"]) == request["source_manifest_sha256"],
          "source manifest changed")
    _fail(_sha256(bound["toolchain"]) == request["toolchain_manifest_sha256"],
          "toolchain manifest changed")
    _fail(_sha256(bound["driver"]) == EXPECTED_DRIVER_SHA256 and
          _sha256(bound["provenance"]) == EXPECTED_PROVENANCE_SHA256,
          "authenticated helper bytes changed")
    _fail(_sha256(bound["host_owner_path"]) == request["host_owner_sha256"],
          "authenticated host owner changed")
    source_doc = _load_json(bound["manifest"], "source manifest")
    toolchain_doc = _load_json(bound["toolchain"], "toolchain manifest")
    _validate_authenticated_source(bound["source"], source_doc, request["candidate_sha"],
                                   request["ihk_sha"], toolchain_doc, bound["provenance"])


class ImageOwner:
    def __init__(self, request, docker=None, signals=None):
        self.request = dict(request); self.docker = docker; self.signals = signals

    def validate(self):
        self.bound = _validate_request(self.request)
        _fail(os.geteuid() != 0, "owner must be unprivileged")
        return self.bound

    def run(self):
        bound = self.validate(); r = self.request
        evidence = bound["evidence"]
        _revalidate_inputs(bound, r)
        host_owner = bound["host_owner"]
        name = "mckernel-image-" + uuid.uuid4().hex
        nonce = uuid.uuid4().hex
        common = CommonExclusion(r["common_exclusion_path"], r)
        common.acquire()
        # No output/evidence mutation occurs until the shared heavy-build
        # exclusion is durably owned.  A stale common lock therefore fails
        # before creating a misleading fresh output namespace.
        # The driver must see absent output/evidence directories.  Only their
        # already-existing parent is mounted; the driver creates the fresh
        # child roots inside that parent.
        bound["attempt"].mkdir(mode=0o700)
        _fsync_dir(bound["owner_evidence"])
        _fsync_dir(evidence.parent); _fsync_dir(bound["output"].parent)
        lease = host_owner.Lease(bound["lease"], name); lease.acquire()
        docker = self.docker or host_owner.Docker(bound["attempt"] / "docker.log", self.signals, sudo=True)
        receipt = {"schema": RECEIPT_SCHEMA, "status": "FAIL", "candidate_sha": r["candidate_sha"],
                   "ihk_sha": r["ihk_sha"], "container_name": name, "owner_nonce": nonce,
                   "cleanup_separately_required": True, "terminal_container_retained": False}
        attempted = False
        try:
            image = json.loads(docker.call(["image", "inspect", r["image_id"]]).stdout)[0]
            _fail(image.get("Id") == r["image_id"] and image.get("Architecture") == "amd64",
                  "container image identity mismatch")
            mounts = [(bound["source"], "/src", True), (bound["manifest"], "/inputs.json", True),
                      (bound["toolchain"], "/toolchain.json", True), (bound["driver"], "/driver.py", True),
                      (bound["provenance"], "/native_rust_exact_build_offline.py", True),
                      (bound["output"].parent, "/work", False)]
            # Tool and kernel paths remain byte-identical inside the container;
            # the offline driver intentionally records those absolute paths.
            for root in bound["roots"] + [bound["kernel"]]:
                row = (root, str(root), True)
                if row not in mounts: mounts.append(row)
            rw_mounts = [(source, target) for source, target, readonly in mounts if not readonly]
            _fail(rw_mounts == [(bound["work"], "/work")],
                  "dedicated work root is not sole RW mount")
            args = ["create", "--name", name, "--label", "mckernel.owner=" + nonce, "--init",
                    "--network=none", "--ipc=private", *RESOURCE_ARGS, "--user", "%d:%d" % (os.getuid(), os.getgid()),
                    "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
                    "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m"]
            for source, target, readonly in mounts:
                args += ["--mount", "type=bind,src=" + str(source) + ",dst=" + target +
                         (",readonly" if readonly else "")]
            command = ["/driver.py", "--source-root", "/src",
                       "--candidate-sha", r["candidate_sha"], "--ihk-sha", r["ihk_sha"],
                       "--manifest", "/inputs.json", "--toolchain", "/toolchain.json",
                       "--output", "/work/" + bound["output"].name,
                       "--evidence", "/work/" + evidence.name, "--jobs", str(r["jobs"]),
                       "--timeout", str(r["timeout"])]
            args += ["--entrypoint", "/usr/bin/python3", r["image_id"], *command]
            attempted = True
            created = docker.call(args); receipt["container_id"] = created.stdout.strip()
            info = host_owner.inspect(docker, name)
            _check_profile(info, r["image_id"], nonce, mounts=mounts, command=command,
                           user="%d:%d" % (os.getuid(), os.getgid()), host_owner=host_owner)
            # The admission measurement is only a lower bound.  Rebind the
            # lease to a fresh host/scratch measurement immediately before
            # Docker start so a concurrent allocation cannot slip between
            # validation and execution.
            latest = host_owner.measure(
                r["disk_admission"]["host_root"],
                r["disk_admission"]["scratch_root"],
                16 * 2**30, 12 * 2**30, source_root=bound["source"],
                output_root=bound["work"], memory_allocation_roots=bound["allocation_roots"])
            _fail(latest.get("memory_allocation_memory_backed_bytes") ==
                  r["memory_backed_bytes"], "pre-start memory allocation changed")
            _fail(latest.get("aggregate_memory_required") ==
                  r["aggregate_memory_required"], "pre-start aggregate memory changed")
            receipt["pre_start_measurement"] = latest
            docker.call(["start", name]); waited = docker.call(["wait", name], timeout=r["timeout"])
            receipt["exit_code"] = int(waited.stdout.strip())
            _fail(receipt["exit_code"] == 0, "offline image driver failed")
            receipt_path = _safe_regular(evidence / "receipt.json", "driver receipt")
            build_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            _validate_driver_result(evidence, bound["output"], build_receipt, r)
            _revalidate_inputs(bound, r)
            receipt["status"] = "PASS"
        except BaseException as exc:
            receipt["error"] = str(exc)
        finally:
            if self.signals: self.signals.cleaning = True
            if attempted:
                try:
                    receipt["terminal_container_info"] = host_owner.retire(docker, name, nonce)
                    receipt["terminal_container_retained"] = True
                    receipt["retired"] = True
                except BaseException as exc:
                    receipt["status"] = "FAIL"; receipt["retirement_error"] = str(exc); receipt["retired"] = False
                try:
                    logs = docker.call(["logs", name], check=False)
                    _fail(logs.returncode == 0, "Docker logs command failed")
                    _exclusive_text(bound["attempt"] / "container.log", logs.stdout + logs.stderr)
                except BaseException as exc:
                    receipt["status"] = "FAIL"; receipt["capture_error"] = str(exc)
                if getattr(docker, "client_retirement_unproven", False):
                    receipt["status"] = "FAIL"; receipt["retired"] = False
                    receipt["client_retirement_unproven"] = True
            else:
                receipt["retired"] = True
            if self.signals and self.signals.requested is not None:
                receipt["status"] = "FAIL"
                receipt["interrupted_signal"] = self.signals.requested
            receipt["driver_evidence_root"] = str(evidence)
            receipt["owner_evidence_root"] = str(bound["owner_evidence"])
            receipt["attempt_root"] = str(bound["attempt"])
            receipt["common_exclusion_path"] = r["common_exclusion_path"]
            receipt["finished_at"] = time.time()
            _exclusive_json(bound["owner_evidence"] / OWNER_RECEIPT_NAME, receipt)
            if receipt.get("retired"):
                lease.release()
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    args = parser.parse_args(argv)
    with Signals() as signals:
        result = ImageOwner(json.loads(args.request.read_text()), signals=signals).run()
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
