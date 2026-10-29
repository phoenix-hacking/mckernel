#!/usr/bin/env python3
"""Freshly probe an immutable tool image and rebind its receipt to a candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

from native_rust_exact_build_container_owner import (
    CliSignals, Docker, Lease, RESOURCE_ARGS, check_profile, inspect, inventory,
    retire,
)
from native_rust_exact_build_image_prepare import (
    BASE_IMAGE, LIBRARIES, PACKAGES, PROBE, TOOLS, validate_probe,
)
import native_rust_exact_build_image_rebind as request_contract
from native_rust_exact_mckernel_image_container_owner import (
    _PREPARATION_EVIDENCE, _SHARED_HEAVY_ENTRY_CONTRACT,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_PROFILE = request_contract.PROFILE


class RebindProbeError(RuntimeError):
    pass


def _duplicates(items):
    value = {}
    for key, item in items:
        if key in value:
            raise RebindProbeError("duplicate JSON key: " + key)
        value[key] = item
    return value


def _safe_regular(path, label):
    path = Path(path)
    if (not path.is_absolute() or not path.is_file() or path.is_symlink() or
            any(parent.is_symlink() for parent in (path, *path.parents))):
        raise RebindProbeError(label + " is not a safe regular file")
    return path


def _read_json_snapshot(path, label, expected_sha256=None):
    path = _safe_regular(path, label)
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise RebindProbeError(label + " is not regular")
        chunks = []
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
        after = os.fstat(fd)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise RebindProbeError(label + " changed during read")
    finally:
        os.close(fd)
    payload = b"".join(chunks)
    observed = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and observed != expected_sha256:
        raise RebindProbeError(label + " digest differs")
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_duplicates)
    except RebindProbeError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise RebindProbeError(label + " is not valid JSON") from exc
    return value, observed


def _write_new(path, payload, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 mode)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise RebindProbeError("publication made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def _write_json(path, value):
    _write_new(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def _copy_closure(source_root, target_root, rows):
    for name, row in sorted(rows.items()):
        relative = Path(name) if isinstance(name, str) else Path(".")
        if (relative.is_absolute() or relative == Path(".") or
                name != relative.as_posix() or
                any(part in ("", ".", "..") for part in relative.parts)):
            raise RebindProbeError("malformed evidence name")
        source = _safe_regular(Path(source_root) / relative, "source evidence")
        payload = source.read_bytes()
        if (hashlib.sha256(payload).hexdigest() != row.get("sha256") or
                len(payload) != row.get("size")):
            raise RebindProbeError("source evidence drift: " + name)
        _write_new(Path(target_root) / relative, payload)


def _expected_probe(request):
    return {
        "network": "none", "mounts": "none", "read_only": True,
        "unprivileged": True, "fresh_container": True,
        "compare_with_source_observation": True,
        "target_receipt_must_be_pass": True,
        "target_receipt_candidate_sha": request["target_candidate_sha"],
        "target_receipt_evidence_root": request["target_evidence_root"],
        "owned_cleanup_required": True, "retire_before_lease_release": True,
    }


def authenticate_request(request_path, expected_request_sha256):
    if not SHA256.fullmatch(str(expected_request_sha256 or "")):
        raise RebindProbeError("expected request digest is required")
    request, request_sha = _read_json_snapshot(
        request_path, "request", expected_request_sha256)
    required = {
        "schema": "mckernel.native-exact-build-image-rebind.v1",
        "status": "READY_FOR_REVIEWED_EXECUTION", "execution_claim": False,
        "profile": EXPECTED_PROFILE,
    }
    for key, expected in required.items():
        if request.get(key) != expected:
            raise RebindProbeError("request field differs: " + key)
    if request.get("probe") != _expected_probe(request):
        raise RebindProbeError("request probe contract differs")
    if (not GIT_SHA.fullmatch(str(request.get("source_candidate_sha", ""))) or
            not GIT_SHA.fullmatch(str(request.get("target_candidate_sha", ""))) or
            not IMAGE_ID.fullmatch(str(request.get("image_id", ""))) or
            not SHA256.fullmatch(str(request.get("source_receipt_sha256", ""))) or
            not SHA256.fullmatch(str(request.get("toolchain_lock_sha256", "")))):
        raise RebindProbeError("request identity is malformed")
    receipt = request_contract.validate_receipt(
        request["source_receipt"], request["source_evidence_root"],
        source_candidate_sha=request["source_candidate_sha"],
        source_receipt_sha256=request["source_receipt_sha256"],
        image_id=request["image_id"],
        toolchain_lock_sha256=request["toolchain_lock_sha256"])
    if request.get("source_evidence") != receipt.get("evidence"):
        raise RebindProbeError("request evidence closure differs")
    if (receipt.get("base_image") != BASE_IMAGE or
            not isinstance(receipt.get("packages"), dict) or
            not isinstance(receipt.get("tools"), dict) or
            not isinstance(receipt.get("libraries"), dict)):
        raise RebindProbeError("source receipt closure is incomplete")
    if not set(_PREPARATION_EVIDENCE).issubset(receipt["evidence"]):
        raise RebindProbeError("source preparation evidence is incomplete")
    source_probe, _ = _read_json_snapshot(
        Path(request["source_evidence_root"]) / "offline-tool-observation.json",
        "source offline observation",
        receipt["evidence"]["offline-tool-observation.json"]["sha256"])
    validate_probe(source_probe, {})
    target_root = Path(request.get("target_evidence_root", ""))
    target_receipt = Path(request.get("target_receipt", ""))
    if (not target_root.is_absolute() or target_root.exists() or target_root.is_symlink() or
            ".." in target_root.parts or
            target_root != Path(os.path.normpath(str(target_root))) or
            not target_root.parent.is_dir() or target_root.parent.is_symlink() or
            any(parent.is_symlink() for parent in target_root.parents) or
            target_receipt != target_root / "image-receipt.json" or
            target_receipt.exists() or target_receipt.is_symlink()):
        raise RebindProbeError("target evidence destination is not canonical and fresh")
    return request, request_sha, receipt, source_probe


def create_args(name, image, nonce):
    return [
        "create", "--name", name, "--label", "mckernel.owner=" + nonce,
        "--init", "--network=none", "--ipc=private", *RESOURCE_ARGS,
        "--user", "%d:%d" % (os.getuid(), os.getgid()), "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--tmpfs", "/tmp:rw,nodev,nosuid,size=256m",
        "--entrypoint", "/usr/bin/sleep", image, "infinity",
    ]


def validate_image_inspect(rows, image):
    if (not isinstance(rows, list) or len(rows) != 1 or
            rows[0].get("Id") != image or rows[0].get("Architecture") != "amd64" or
            rows[0].get("Os") != "linux"):
        raise RebindProbeError("immutable image inspection differs")
    return rows[0]


def validate_container(info, image, nonce):
    check_profile(info, image, nonce, network="none", readonly=True)
    host, config = info.get("HostConfig", {}), info.get("Config", {})
    if (info.get("Mounts") or host.get("Binds") or
            host.get("Tmpfs") != {"/tmp": "rw,nodev,nosuid,size=256m"} or
            host.get("RestartPolicy") != {"Name": "no", "MaximumRetryCount": 0} or
            config.get("User") != "%d:%d" % (os.getuid(), os.getgid()) or
            config.get("Entrypoint") != ["/usr/bin/sleep"] or
            config.get("Cmd") != ["infinity"]):
        raise RebindProbeError("effective offline profile differs")


def _absence(docker, name):
    observed = docker.call(["inspect", name], check=False)
    expected_stdout = "[]\n"
    expected_stderr = "Error: No such object: %s\n" % name
    if (observed.returncode != 1 or observed.stdout != expected_stdout or
            observed.stderr != expected_stderr):
        raise RebindProbeError("container absence is unproven")
    return {"container_name": name, "absent": True,
            "inspect_exit_code": observed.returncode, "stderr": observed.stderr}


def execute(*, request_path, expected_request_sha256, runner=None, signals=None):
    request, request_sha, source_receipt, source_probe = authenticate_request(
        request_path, expected_request_sha256)
    target = Path(request["target_evidence_root"])
    final_receipt = Path(request["target_receipt"])
    lease_path = target.parent / ("." + target.name + ".lease.json")
    if lease_path.exists() or lease_path.is_symlink():
        raise RebindProbeError("rebind lease already exists")
    shared_request = {
        "kind": "tool-image-rebind", "request": str(Path(request_path).resolve()),
        "request_sha256": request_sha, "target_evidence_root": str(target),
        "target_candidate_sha": request["target_candidate_sha"],
        "image_id": request["image_id"],
    }
    shared_lock, shared_record = _SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(
        shared_request, "image")
    name = "mckernel-tool-rebind-" + uuid.uuid4().hex
    lease = None
    docker = None
    attempted = lease_acquired = retired = removed = False
    terminal = None
    phase = "shared-acquired"
    result = {
        "status": "FAIL", "candidate_sha": request["target_candidate_sha"],
        "image_id": request["image_id"], "base_image": BASE_IMAGE,
        "toolchain_lock_sha256": request["toolchain_lock_sha256"],
        "source_receipt": request["source_receipt"],
        "source_receipt_sha256": request["source_receipt_sha256"],
        "container_name": name, "lease_path": str(lease_path),
        "source_free": True, "runtime_network": "none", "retired": False,
        "cleanup_separately_required": True, "terminal_container_info": None,
        "terminal_container_info_current": False,
        "shared_heavy_operation": {"kind": "image", "path": str(shared_lock),
                                   "record": shared_record},
    }
    try:
        target.mkdir(mode=0o700)
        lease = Lease(lease_path, name)
        _copy_closure(request["source_evidence_root"], target,
                      source_receipt["evidence"])
        _write_json(target / "rebind-provenance.json", {
            "schema": "mckernel.tool-image-rebind-provenance.v1",
            "request": str(Path(request_path).resolve()),
            "request_sha256": request_sha,
            "source_candidate_sha": request["source_candidate_sha"],
            "source_receipt": request["source_receipt"],
            "source_receipt_sha256": request["source_receipt_sha256"],
            "historical_preparation_evidence_copied_unchanged": True,
            "target_candidate_sha": request["target_candidate_sha"],
        })
        docker = runner or Docker(target / "rebind.log", signals=signals, sudo=True)
        lease.acquire()
        lease_acquired = True
        phase = "lease-acquired"
        image_rows = json.loads(docker.call(
            ["image", "inspect", request["image_id"]]).stdout)
        _write_json(target / "rebind-image-inspect.json",
                    validate_image_inspect(image_rows, request["image_id"]))
        attempted = True
        phase = "create-attempted"
        docker.call(create_args(name, request["image_id"], lease.nonce))
        before = inspect(docker, name)
        validate_container(before, request["image_id"], lease.nonce)
        _write_json(target / "rebind-offline-inspect-before-start.json", before)
        docker.call(["start", name])
        phase = "started"
        fresh_probe = json.loads(docker.call([
            "exec", "--env", "EXPECTED_PACKAGES=" + json.dumps(PACKAGES),
            "--env", "EXPECTED_TOOLS=" + json.dumps(TOOLS),
            "--env", "EXPECTED_LIBRARIES=" + json.dumps(LIBRARIES), name,
            "/usr/bin/python3", "-I", "-c", PROBE,
        ]).stdout)
        validate_probe(fresh_probe, {})
        _write_json(target / "rebind-offline-tool-observation.json", fresh_probe)
        if fresh_probe != source_probe:
            raise RebindProbeError("fresh offline observation differs from source")
        terminal = retire(docker, name, lease.nonce)
        retired = True
        _write_json(target / "rebind-offline-inspect-terminal.json", terminal)
        docker.call(["rm", name])
        removed = True
        _write_json(target / "rebind-container-absence.json", _absence(docker, name))
        attempted = False
        if getattr(docker, "client_retirement_unproven", False):
            raise RebindProbeError("Docker client retirement is unproven")
        if signals is not None:
            signals.check()
        lease.release()
        lease_acquired = False
        phase = "container-absent"
        result.update({
            "status": "PASS", "retired": True,
            "cleanup_separately_required": False,
            "terminal_container_info": None,
            "terminal_container_info_current": True,
            "packages": source_receipt["packages"],
            "tools": source_receipt["tools"],
            "libraries": source_receipt["libraries"],
        })
        _write_json(target / "rebind-result-before-shared-release.json", result)
        released = _SHARED_HEAVY_ENTRY_CONTRACT._release_exclusion(
            shared_lock, shared_record, result)
        _write_json(target / "rebind-shared-release.json", {"released": released})
        if not released:
            raise RebindProbeError("shared heavy-operation release failed")
        phase = "shared-released"
    except BaseException as exc:
        if signals is not None:
            signals.cleaning = True
        result.update(status="FAIL", error=str(exc), phase=phase)
        if attempted and docker is not None:
            try:
                terminal = retire(docker, name, lease.nonce)
                retired = True
                if not (target / "rebind-offline-inspect-terminal.json").exists():
                    _write_json(target / "rebind-offline-inspect-terminal.json", terminal)
            except BaseException as cleanup_exc:
                result["retirement_error"] = str(cleanup_exc)
                retired = False
            try:
                captured = docker.call(["logs", name], check=False)
                _write_new(target / "rebind-container.log",
                           (captured.stdout + captured.stderr).encode())
            except BaseException as capture_exc:
                result["capture_error"] = str(capture_exc)
        client_unproven = bool(
            docker is not None and
            getattr(docker, "client_retirement_unproven", False))
        result.update(
            retired=retired and not client_unproven,
            # Every failure retains the shared heavy-operation token, even if
            # the container itself is positively absent.
            cleanup_separately_required=True,
            terminal_container_info=None if removed else terminal,
            terminal_container_info_current=(
                removed or (terminal is not None and not client_unproven)),
            client_retirement_unproven=client_unproven,
            container_name=name, lease_path=str(lease_path),
            shared_release_required=True,
        )
    finally:
        if target.is_dir() and not final_receipt.exists():
            result["evidence"] = inventory(target)
            _write_json(final_receipt, result)
    return final_receipt, result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--expected-request-sha256", required=True)
    args = parser.parse_args(argv)
    with CliSignals() as signals:
        receipt, result = execute(
            request_path=args.request,
            expected_request_sha256=args.expected_request_sha256,
            signals=signals)
    print(json.dumps({"receipt": str(receipt), "status": result["status"]},
                     sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
