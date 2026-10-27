#!/usr/bin/env python3
"""Strict command-line entry point for the reviewed native diagnostic.

The lifecycle and host adapters remain dependency-injected APIs.  This small
adapter is the only place that binds their reviewed build plan to the real
host factories; importing it never starts a child or opens QMP.
"""

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys


_HERE = Path(__file__).resolve().parent
_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load " + name)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def _backend_module():
    """Execute backend with the exact sibling qmp_capture, never ambient state."""
    sentinel = object()
    previous = sys.modules.get("qmp_capture", sentinel)
    qmp = _module("native_diagnostic_runner_qmp_capture", _HERE / "qmp_capture.py")
    sys.modules["qmp_capture"] = qmp
    try:
        return _module("native_diagnostic_runner_backend", _HERE / "native_diagnostic_backend.py")
    finally:
        if previous is sentinel:
            sys.modules.pop("qmp_capture", None)
        else:
            sys.modules["qmp_capture"] = previous


def _runtime():
    """Load source-local modules lazily, keeping import side effects absent."""
    diagnostic = _module("native_diagnostic_runner_diagnostic", _HERE / "native_diagnostic.py")
    backend = _backend_module()
    return diagnostic, backend


def _canonical_file(value, label):
    raw = os.fspath(value)
    path = Path(raw)
    if not path.is_absolute() or "\0" in raw:
        raise ValueError(label + " must be absolute")
    if not path.exists() or path.is_symlink() or not path.is_file():
        raise ValueError(label + " must be a regular file")
    if str(path.resolve(strict=True)) != raw:
        raise ValueError(label + " must be canonical")
    return path


def _private_parent(value):
    raw = os.fspath(value)
    path = Path(raw)
    if not path.is_absolute() or "\0" in raw or path.is_symlink():
        raise ValueError("attempt parent must be absolute canonical")
    if not path.is_dir() or str(path.resolve(strict=True)) != raw:
        raise ValueError("attempt parent must be absolute canonical")
    st = path.stat()
    if st.st_uid != os.getuid() or (st.st_mode & 0o777) != 0o700:
        raise ValueError("attempt parent must be private and caller-owned")
    return path


def _timeout(value):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout must be finite and in (0, 3600]") from exc
    if not math.isfinite(result) or result <= 0 or result > 3600:
        raise ValueError("timeout must be finite and in (0, 3600]")
    return result


def _attempt_name(value):
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value) or value in (".", ".."):
        raise ValueError("attempt name is not safe")
    return value


def _failure_text(exc):
    # Share the lifecycle's total conversion, including CLI errors before
    # runtime loading. Loading this source-local module has no runtime effects.
    try:
        diagnostic = _module("native_diagnostic_runner_failure", _HERE / "native_diagnostic.py")
        return diagnostic.failure_text(exc)
    except BaseException:
        return "<exception metadata unavailable>"


def _record_setup_failure(diagnostic, attempt, exc):
    try:
        diagnostic.record_failure(attempt, exc, "setup")
    except BaseException:
        # The original plan/factory error is authoritative, including failures
        # looking up the injected diagnostic helper itself.
        pass


def run(manifest_path, attempt_parent, attempt_name, timeout, *, diagnostic=None, backend=None):
    """Reserve one attempt and execute exactly one injected diagnostic."""
    manifest_path = _canonical_file(manifest_path, "manifest")
    attempt_parent = _private_parent(attempt_parent)
    attempt_name = _attempt_name(attempt_name)
    timeout = _timeout(timeout)
    if diagnostic is None or backend is None:
        diagnostic, backend = _runtime()
    manifest = diagnostic.load_manifest(str(manifest_path))
    attempt = diagnostic.prepare_attempt(manifest, str(attempt_parent), attempt_name)
    try:
        plan = diagnostic.build_command(manifest, attempt)
        process = backend.process_factory(plan["argv"], str(attempt))
        qmp = backend.qmp_factory(plan["qmp_socket"])
    except BaseException as exc:
        _record_setup_failure(diagnostic, attempt, exc)
        raise
    result = diagnostic.run_diagnostic(manifest, attempt, process, qmp, timeout=timeout,
                                       expected_plan=plan)
    if not isinstance(result, dict) or result.get("status") != "PROTOCOL_PASS":
        raise RuntimeError("diagnostic did not return PROTOCOL_PASS")
    return result


def _parser():
    parser = argparse.ArgumentParser(description="run one reviewed native diagnostic",
                                     allow_abbrev=False)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--attempt-parent", required=True)
    parser.add_argument("--attempt-name", required=True)
    parser.add_argument("--timeout", required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        result = run(args.manifest, args.attempt_parent, args.attempt_name, args.timeout)
    except Exception as exc:
        print("native diagnostic failed: " + _failure_text(exc), file=sys.stderr)
        return 1
    print(json.dumps({"attempt": args.attempt_name, "case_id": result.get("case_id"),
                      "status": "PROTOCOL_PASS"}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
