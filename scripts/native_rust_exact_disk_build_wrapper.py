#!/usr/bin/env python3
"""Admission wrapper for one exact disk-backed native Rust build.

This module is intentionally only a policy boundary.  It does not create a
container, acquire a lease, or perform filesystem relocation.  After all
checks pass it delegates exactly once to the reviewed BuildOwner, preserving
that owner's lease and evidence protocol.
"""
import argparse
from decimal import Decimal, InvalidOperation
import importlib.util
import json
import os
from pathlib import Path
import types
import hashlib
import stat


LAUNCHER_AGGREGATE_GIB = "16.2158"
# Decimal GiB is converted by truncation to the greatest admissible integer
# byte budget.  This is deterministic across Python versions and rejects even
# one byte over it.
LAUNCHER_AGGREGATE_BYTES = int(Decimal(LAUNCHER_AGGREGATE_GIB) * (2 ** 30))
EXPECTED_LIMITS = {
    "NanoCpus": 4000000000,
    "CpusetCpus": "2-5",
    "Memory": 12 * 2 ** 30,
    "MemorySwap": 12 * 2 ** 30,
    "PidsLimit": 512,
    "NetworkMode": "none",
}
# The original path is a retained immutable tombstone.  Fresh attempts must
# use the reviewed replacement so a stale exclusion can never be mistaken for
# the current build's lease.
RETIRED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-76ae20b5.json"
# The failed -2, -3, closurefix-4, runtimeclosure-5, offline-cwd-6, and
# memory-map-7, relocated-memory-map-8, mapping-binding-9, and
# lifecycle-binding-10 attempts are retained evidence, never reusable leases.
# Fresh requests are bound to the objtool-binding-11 path below.
REVIEWED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-76ae20b5-2.json"
SUPERSEDED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-97fb67a7-3.json"
CLOSUREFIX_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-closurefix-4.json"
RUNTIMECLOSURE_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-runtimeclosure-5.json"
OFFLINECWD_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-offlinecwd-6.json"
MEMORYMAP_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-memorymap-7.json"
MEMORYMAP_RELOCATED_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-memorymap-relocated-8.json"
MAPPINGBINDING_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-mappingbinding-9.json"
LIFECYCLEBINDING_OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-lifecyclebinding-10.json"
OPERATIONAL_EXCLUSION_PATH = "/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-objtoolbinding-11.json"


class AdmissionError(ValueError):
    pass


def _request_hash(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _starttime(pid):
    return Path("/proc") .joinpath(str(pid), "stat").read_text().rsplit(")", 1)[1].split()[19]


def _acquire_exclusion(request):
    path = Path(request.get("operational_exclusion_path", ""))
    if str(path) != OPERATIONAL_EXCLUSION_PATH:
        raise AdmissionError("operational exclusion path is not the reviewed exact path")
    record = {"schema": "mckernel.native-exact-operational-exclusion.v1",
              "pid": os.getpid(), "starttime": _starttime(os.getpid()),
              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
              "request_sha256": _request_hash(request)}
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise AdmissionError("operational exclusion already exists; reconciliation required")
    try:
        record.update({"device": os.fstat(fd).st_dev, "inode": os.fstat(fd).st_ino})
        data = json.dumps(record, sort_keys=True).encode()
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if not isinstance(written, int) or written <= 0:
                raise AdmissionError("operational exclusion record write made no progress")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    parent_fd = os.open(str(path.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try: os.fsync(parent_fd)
    finally: os.close(parent_fd)
    return path, record


def _release_exclusion(lock, record, result):
    if not (isinstance(result, dict) and result.get("status") == "PASS" and
            result.get("retired") is True and result.get("cleanup_separately_required") is False and
            result.get("terminal_container_info") is None and
            result.get("terminal_container_info_current") is True):
        return False
    try:
        parent_fd = os.open(str(lock.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            fd = os.open(lock.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
            try:
                current = json.loads(os.read(fd, 1 << 20).decode())
                identity = os.fstat(fd)
                if current != record or identity.st_dev != record["device"] or identity.st_ino != record["inode"]:
                    return False
                os.unlink(lock.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)
        return True
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _owner_path(request, source_root):
    raw = request.get("owner_path")
    path = Path(raw) if raw is not None else source_root / "scripts" / "native_rust_exact_build_container_owner.py"
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise AdmissionError("owner_path is not a regular file")
    try:
        path.resolve(strict=True).relative_to(source_root.resolve(strict=True))
    except ValueError:
        raise AdmissionError("owner_path escapes source_root")
    return path


def _stable_file_bytes(root, path, expected, label):
    """Read authenticated bytes through a descriptor-relative no-follow walk."""
    root = Path(root); path = Path(path)
    try:
        rel = path.relative_to(root)
    except ValueError:
        raise AdmissionError("%s escapes source_root" % label)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fds = []
    try:
        fd = os.open(str(root), flags)
        fds.append(fd)
        for component in rel.parts[:-1]:
            if component in ("", ".", ".."):
                raise AdmissionError("invalid component in %s" % label)
            nxt = os.open(component, flags, dir_fd=fd)
            fds.append(nxt); fd = nxt
        if not rel.parts or rel.parts[-1] in ("", ".", ".."):
            raise AdmissionError("invalid file path for %s" % label)
        leaf = os.open(rel.parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd)
        fds.append(leaf)
        opened = os.fstat(leaf)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise AdmissionError("%s is not a unique regular file" % label)
        chunks = []
        while True:
            block = os.read(leaf, 1 << 20)
            if not block: break
            chunks.append(block)
        data = b"".join(chunks)
        after = os.fstat(leaf)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mode) != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mode):
            raise AdmissionError("%s identity changed during read" % label)
    except AdmissionError:
        raise
    except OSError as exc:
        raise AdmissionError("cannot read %s: %s" % (label, exc))
    finally:
        for item in reversed(fds):
            try: os.close(item)
            except OSError: pass
    if not isinstance(expected, str) or hashlib.sha256(data).hexdigest() != expected:
        raise AdmissionError("%s hash mismatch" % label)
    return data


def _load_owner(request):
    source_root = Path(request.get("source_root", ""))
    if not source_root.is_absolute() or not source_root.is_dir() or source_root.is_symlink():
        raise AdmissionError("source_root is not a regular directory")
    source_root = source_root.resolve(strict=True)
    path = _owner_path(request, source_root)
    try:
        path.relative_to(source_root)
    except ValueError:
        raise AdmissionError("owner_path escapes source_root")
    owner_hash = request.get("owner_path_sha256")
    if owner_hash is None:
        raise AdmissionError("owner_path_sha256 is required before import")
    owner_bytes = _stable_file_bytes(source_root, path, owner_hash, "owner_path")
    # Both modules are loaded under a private candidate package.  The owner
    # uses a relative provenance import; this prevents a preloaded generic
    # ``native_rust_exact_build_offline`` module from contaminating admission.
    import sys
    package = "_mckernel_exact_candidate_%d_%x" % (os.getpid(), id(request))
    package_module = types.ModuleType(package)
    package_module.__path__ = [str(path.parent)]
    package_module.__package__ = package
    sys.modules[package] = package_module
    loaded = []
    try:
        provenance_name = package + ".native_rust_exact_build_offline"
        provenance_path = path.parent / "native_rust_exact_build_offline.py"
        try:
            provenance_path.relative_to(source_root)
        except ValueError:
            raise AdmissionError("provenance path escapes source_root")
        provenance_hash = request.get("provenance_path_sha256")
        if provenance_hash is None:
            raise AdmissionError("provenance_path_sha256 is required before import")
        provenance_bytes = _stable_file_bytes(source_root, provenance_path, provenance_hash, "provenance_path")
        driver_path = Path(request.get("driver_path", ""))
        if driver_path != provenance_path:
            raise AdmissionError("driver_path must equal authenticated provenance_path")
        if request.get("driver_path_sha256") != provenance_hash:
            raise AdmissionError("driver_path hash must equal provenance hash")
        provenance = types.ModuleType(provenance_name)
        provenance.__file__ = str(provenance_path)
        provenance.__package__ = package
        sys.modules[provenance_name] = provenance
        loaded.append(provenance_name)
        exec(compile(provenance_bytes, str(provenance_path), "exec"), provenance.__dict__)
        name = package + ".native_rust_exact_build_container_owner"
        module = types.ModuleType(name)
        module.__file__ = str(path)
        module.__package__ = package
        sys.modules[name] = module
        loaded.append(name)
        exec(compile(owner_bytes, str(path), "exec"), module.__dict__)
        if module.provenance.__file__ != str(provenance_path):
            raise AdmissionError("loaded provenance path differs from source_root")
        return module
    finally:
        for name in loaded + [package]:
            sys.modules.pop(name, None)


def _aggregate_argument(raw):
    if raw is None:
        raw = LAUNCHER_AGGREGATE_GIB
    if not isinstance(raw, str) or raw != LAUNCHER_AGGREGATE_GIB:
        raise AdmissionError("launcher aggregate must be exactly 16.2158 GiB")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise AdmissionError("invalid launcher aggregate")
    if value != Decimal(LAUNCHER_AGGREGATE_GIB):
        raise AdmissionError("launcher aggregate is not exact")
    return LAUNCHER_AGGREGATE_BYTES


def _require_profile(owner, request):
    if dict(getattr(owner, "LIMITS", {})) != EXPECTED_LIMITS:
        raise AdmissionError("owner LIMITS differ from reviewed pinned profile")
    requested = request.get("limits")
    if requested is not None and dict(requested) != EXPECTED_LIMITS:
        raise AdmissionError("request limits differ from reviewed pinned profile")
    if request.get("memory_backed_bytes", 0) not in (0, None):
        raise AdmissionError("request declares memory-backed source bytes")
    roots = request.get("memory_allocation_roots", [])
    if not isinstance(roots, list) or not roots:
        raise AdmissionError("memory allocation roots are required")
    # This is a lexical admission check; BuildOwner.validate performs the
    # authoritative filesystem binding and accounting check.
    if any("tmpfs" in str(root).lower() for root in roots):
        raise AdmissionError("tmpfs source roots are forbidden")


def _check_measurement(measurement, budget):
    if not isinstance(measurement, dict):
        raise AdmissionError("owner did not publish a measurement")
    backed = measurement.get("memory_allocation_memory_backed_bytes")
    if backed is None:
        backed = measurement.get("candidate_memory_effect", {}).get("bytes")
    if not isinstance(backed, int) or isinstance(backed, bool) or backed != 0:
        raise AdmissionError("owner measurement has nonzero memory-backed bytes")
    rows = measurement.get("memory_allocation_roots", [])
    if not isinstance(rows, list) or not rows:
        raise AdmissionError("owner allocation measurement is missing")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("filesystem"), str):
            raise AdmissionError("owner allocation measurement row is malformed")
        if row["filesystem"] not in ("ext4", "xfs"):
            raise AdmissionError("owner measurement includes unsupported filesystem")
        effect = row.get("memory_effect_bytes")
        if not isinstance(effect, int) or isinstance(effect, bool) or effect != 0:
            raise AdmissionError("owner allocation row has nonzero memory effect")
        allocated = row.get("allocated_bytes")
        if not isinstance(allocated, int) or isinstance(allocated, bool) or allocated < 0:
            raise AdmissionError("owner allocation row total is malformed")
        total = locals().get("row_total", 0) + allocated
        row_total = total
    aggregate = measurement.get("aggregate_memory_required")
    if not isinstance(aggregate, int) or isinstance(aggregate, bool):
        raise AdmissionError("owner aggregate measurement is missing")
    total_field = measurement.get("memory_allocation_total_bytes")
    if not isinstance(total_field, int) or isinstance(total_field, bool):
        raise AdmissionError("owner allocation total is missing")
    if total_field != row_total:
        raise AdmissionError("owner allocation total is inconsistent")
    tmpfs_total = measurement.get("memory_allocation_tmpfs_bytes")
    if not isinstance(tmpfs_total, int) or isinstance(tmpfs_total, bool) or tmpfs_total != 0:
        raise AdmissionError("owner tmpfs total is nonzero or missing")
    effect = measurement.get("candidate_memory_effect")
    if not isinstance(effect, dict) or effect.get("classification") != "none":
        raise AdmissionError("candidate memory effect classification is not none")
    effect_bytes = effect.get("bytes")
    if not isinstance(effect_bytes, int) or isinstance(effect_bytes, bool) or effect_bytes != 0:
        raise AdmissionError("candidate memory effect is nonzero")
    expected_aggregate = EXPECTED_LIMITS["Memory"] + effect_bytes
    if aggregate != expected_aggregate:
        raise AdmissionError("owner aggregate measurement is inconsistent")
    if aggregate < EXPECTED_LIMITS["Memory"]:
        raise AdmissionError("owner aggregate measurement is below pinned container memory")
    if aggregate > budget:
        raise AdmissionError("owner aggregate exceeds launcher budget")


def run_request(request, aggregate_gib=LAUNCHER_AGGREGATE_GIB):
    """Validate admission and invoke BuildOwner.run exactly once."""
    budget = _aggregate_argument(aggregate_gib)
    if "launcher_aggregate_memory_gib" in request:
        _aggregate_argument(request["launcher_aggregate_memory_gib"])
    lock, lock_record = _acquire_exclusion(request)
    try:
        owner = _load_owner(request)
        _require_profile(owner, request)
        # The offline provenance runner consumes this environment.  Set the
        # reviewed value before owner validation and retain all other owner values.
        owner.provenance.ENV["GIT_OPTIONAL_LOCKS"] = "0"
        with owner.CliSignals() as signals:
            checked = owner.BuildOwner(request, signals=signals)
            original_validate = checked.validate

            def guarded_validate():
                result = original_validate()
                _check_measurement(getattr(checked, "measurement", None), budget)
                return result

            # BuildOwner.run() calls self.validate() again immediately before
            # lease acquisition.  Guard that call too: a changed second measure
            # must never reach Docker or a lease.
            checked.validate = guarded_validate
            guarded_validate()
            result = checked.run()
        _release_exclusion(lock, lock_record, result)
        return result
    except BaseException:
        # Retain the exclusion on every exception: cleanup/lease state is not
        # positively proven, so a later run must explicitly quarantine it.
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--launcher-aggregate-gib", default=LAUNCHER_AGGREGATE_GIB)
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text())
    result = run_request(request, args.launcher_aggregate_gib)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
