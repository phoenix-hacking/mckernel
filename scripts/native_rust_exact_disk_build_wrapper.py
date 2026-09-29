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


class AdmissionError(ValueError):
    pass


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


def _load_owner(request):
    source_root = Path(request.get("source_root", ""))
    if not source_root.is_absolute() or not source_root.is_dir() or source_root.is_symlink():
        raise AdmissionError("source_root is not a regular directory")
    path = _owner_path(request, source_root)
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
        provenance_spec = importlib.util.spec_from_file_location(
            provenance_name, str(provenance_path))
        if provenance_spec is None or provenance_spec.loader is None:
            raise AdmissionError("cannot load candidate provenance")
        provenance = importlib.util.module_from_spec(provenance_spec)
        sys.modules[provenance_name] = provenance
        loaded.append(provenance_name)
        provenance_spec.loader.exec_module(provenance)
        name = package + ".native_rust_exact_build_container_owner"
        spec = importlib.util.spec_from_file_location(name, str(path))
        if spec is None or spec.loader is None:
            raise AdmissionError("cannot load BuildOwner")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loaded.append(name)
        spec.loader.exec_module(module)
        if Path(module.__file__).resolve(strict=True) != path.resolve(strict=True):
            raise AdmissionError("loaded owner path differs from request")
        if Path(module.provenance.__file__).resolve(strict=True) != provenance_path.resolve(strict=True):
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
    if backed != 0:
        raise AdmissionError("owner measurement has nonzero memory-backed bytes")
    rows = measurement.get("memory_allocation_roots", [])
    if not isinstance(rows, list) or not rows:
        raise AdmissionError("owner allocation measurement is missing")
    if any(row.get("filesystem") == "tmpfs" for row in rows if isinstance(row, dict)):
        raise AdmissionError("owner measurement includes a tmpfs source root")
    aggregate = measurement.get("aggregate_memory_required")
    if not isinstance(aggregate, int) or isinstance(aggregate, bool):
        raise AdmissionError("owner aggregate measurement is missing")
    if aggregate < EXPECTED_LIMITS["Memory"]:
        raise AdmissionError("owner aggregate measurement is below pinned container memory")
    if aggregate > budget:
        raise AdmissionError("owner aggregate exceeds launcher budget")


def run_request(request, aggregate_gib=LAUNCHER_AGGREGATE_GIB):
    """Validate admission and invoke BuildOwner.run exactly once."""
    budget = _aggregate_argument(aggregate_gib)
    if "launcher_aggregate_memory_gib" in request:
        _aggregate_argument(request["launcher_aggregate_memory_gib"])
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
        return checked.run()


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
