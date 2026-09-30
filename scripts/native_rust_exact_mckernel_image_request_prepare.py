#!/usr/bin/env python3
"""Prepare one deterministic v2 image-owner request.

This is deliberately a data-only boundary: it never builds, starts Docker, or
changes the candidate/build roots.  All roots and receipts are authenticated
before the two new JSON documents are published.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_rust_exact_mckernel_image_container_owner as owner
import native_rust_exact_mckernel_image_offline as driver


class PreparationError(RuntimeError):
    pass


def _fail(ok, message):
    if not ok:
        raise PreparationError(message)


def _digest(path):
    return owner._sha256(Path(path))


def _file(path, label):
    path = Path(path)
    _fail(path.is_absolute() and path.is_file() and not path.is_symlink(), label + " missing")
    _fail(not any(part.is_symlink() for part in [path, *path.parents]), label + " has symlink parent")
    return path


def _directory(path, label):
    path = Path(path)
    _fail(path.is_absolute() and path.is_dir() and not path.is_symlink(), label + " missing")
    _fail(not any(part.is_symlink() for part in path.parents), label + " has symlink parent")
    return path


def _fresh(path, label):
    path = Path(path)
    _fail(path.is_absolute() and not path.exists() and not path.is_symlink(), label + " must be fresh")
    _directory(path.parent, label + " parent")
    return path


def _write_new(path, value):
    path = _fresh(path, "manifest")
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    fd = path.open("xb")
    try:
        fd.write(payload); fd.flush()
        os.fsync(fd.fileno())
    finally:
        fd.close()
    owner._fsync_dir(path.parent)
    return path


def _publish_staged(staged, final, label):
    """Publish a durable staged regular file without replacing an existing name.

    ``link`` is the portable no-replace primitive available to this data-only
    preparer: the destination appears as one complete inode or not at all.
    Staging is deliberately in the destination parent, so this cannot silently
    degrade into a cross-filesystem copy with a partially visible destination.
    """
    staged = _file(staged, label + " staging")
    final = _fresh(final, label)
    _fail(staged.parent.stat().st_dev == final.parent.stat().st_dev,
          label + " staging filesystem differs")
    try:
        os.link(staged, final, follow_symlinks=False)
    except FileExistsError as exc:
        raise PreparationError(label + " already exists") from exc
    owner._fsync_dir(final.parent)
    return final


def _staged_json(parent, prefix, value):
    """Create one private, durable JSON inode in the final parent's filesystem."""
    parent = _directory(parent, prefix + " parent")
    stage_dir = Path(tempfile.mkdtemp(prefix="." + prefix + "-", dir=str(parent)))
    try:
        staged = _write_new(stage_dir / "document.json", value)
    except BaseException:
        # A write may have created a short private file before failing.  It
        # must never escape the private staging name, and cleanup must not
        # replace the write failure that explains the rejection.
        try:
            for item in stage_dir.iterdir():
                item.unlink()
            stage_dir.rmdir()
        except OSError:
            pass
        raise
    return stage_dir, staged


def _publish(toolchain, final_toolchain, final_request, make_request, validate):
    """Validate through private staging, then publish toolchain and request in order."""
    final_toolchain = _fresh(final_toolchain, "toolchain manifest")
    final_request = _fresh(final_request, "request")
    toolchain_stage = request_stage = None
    try:
        toolchain_stage, staged_toolchain = _staged_json(
            final_toolchain.parent, "mckernel-image-toolchain", toolchain)
        staged_request = make_request(staged_toolchain)
        validate(staged_request)
        _publish_staged(staged_toolchain, final_toolchain, "toolchain manifest")
        request = make_request(final_toolchain)
        validate(request)
        request_stage, staged_request = _staged_json(
            final_request.parent, "mckernel-image-request", request)
        _publish_staged(staged_request, final_request, "request")
        return request
    finally:
        for stage_dir in (toolchain_stage, request_stage):
            if stage_dir is not None:
                for item in stage_dir.iterdir():
                    item.unlink()
                stage_dir.rmdir()
        # Once staged admission passed, retain an atomically published final
        # toolchain if later validation/publication fails.  It is evidence, not
        # runnable authority: the request is always published last.  A failed
        # contender may also observe another contender's final here; never
        # mistake that independent publication for this call leaking a file.


def prepare(*, candidate_manifest, backup_root, backup_inventory, build_output,
            image_receipt, image_id, nightly_root, host_git, driver_path,
            provenance_path, host_owner_path, source_root, owner_work_root,
            owner_evidence_root, output_root, evidence_root, attempt_root,
            lease_path, common_exclusion_path=owner.COMMON_EXCLUSION,
            toolchain_manifest=None, request_path=None, jobs=4, timeout=19800,
            host_root=None, scratch_root=None, disk_admission=None,
            expected_toolchain_lock_sha256=None, gitlink_manifest=None,
            gitlink_root=None):
    """Return and optionally publish a validated REQUEST_SCHEMA v1 request."""
    manifest = _file(candidate_manifest, "candidate/input manifest")
    source = _directory(source_root, "source root")
    backup = _directory(backup_root, "source backup")
    out = _directory(build_output, "build output")
    nightly = _directory(nightly_root, "nightly root")
    fresh_output = _fresh(output_root, "output root")
    fresh_evidence = _fresh(evidence_root, "evidence root")
    receipt_path = _file(image_receipt, "tool-image receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    _fail(receipt.get("status") == "PASS", "tool-image receipt is not PASS")
    _fail(receipt.get("source_free") is True, "tool-image receipt source_free is not true")
    _fail(receipt.get("runtime_network") == "none", "tool-image receipt runtime_network differs")
    _fail(receipt.get("image_id") == image_id, "tool-image receipt image differs")
    _fail(isinstance(expected_toolchain_lock_sha256, str) and
          re.fullmatch(r"[0-9a-f]{64}", expected_toolchain_lock_sha256) is not None,
          "expected toolchain lock hash")
    _fail(receipt.get("toolchain_lock_sha256") == expected_toolchain_lock_sha256,
          "tool-image receipt toolchain lock differs")
    _fail(re.fullmatch(r"sha256:[0-9a-f]{64}", str(image_id)) is not None, "image identity")
    tools = receipt.get("tools")
    _fail(isinstance(tools, dict), "tool-image receipt tools missing")
    # v2 receipts attest only immutable image-provided tools.  ``rustc`` is
    # authenticated independently from the mounted nightly closure below.
    required = tuple(name for name in owner.REQUIRED_TOOLS if name != "rustc")
    _fail(all(name in tools and isinstance(tools[name], dict) for name in required), "tool-image tools incomplete")
    for name in required:
        row = tools[name]
        _fail(re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256"))) is not None, "tool hash: " + name)
        _fail(isinstance(row.get("path"), str) and row["path"].startswith("/"), "tool path: " + name)
    libraries = receipt.get("libraries")
    evidence = receipt.get("evidence")
    _fail(isinstance(evidence, dict), "tool-image receipt evidence missing")
    for name in owner._PREPARATION_EVIDENCE:
        row = evidence.get(name)
        _fail(isinstance(row, dict) and isinstance(row.get("sha256"), str) and
              re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) and
              isinstance(row.get("size"), int) and row["size"] >= 0,
              "tool-image receipt evidence entry missing: " + name)
        path = _file(receipt_path.parent / name, "tool-image receipt evidence")
        _fail(path.stat().st_size == row["size"] and _digest(path) == row["sha256"],
              "tool-image receipt evidence drift: " + name)
    _fail(evidence["tool-observation.json"]["sha256"] ==
          evidence["offline-tool-observation.json"]["sha256"],
          "tool-image receipt preparation/offline observations differ")
    # Validate the complete immutable closure before publishing anything.  The
    # owner repeats this after binding the receipt and its evidence hashes.
    owner._validate_library_closure(receipt, libraries, receipt_path.parent)
    _fail(host_root is not None and scratch_root is not None or disk_admission is not None,
          "explicit host/scratch roots or disk admission required")
    nightly_version = __import__("subprocess").check_output([str(nightly / "bin/rustc"), "--version"], text=True).strip()
    roots = [{"path": "/out", "inventory": owner._closure_inventory(out, out, Path("/out"))},
             {"path": "/nightly", "inventory": owner._closure_inventory(nightly, nightly, Path("/nightly"))}]
    toolchain = {
        "schema": driver.TOOLCHAIN_SCHEMA_V2,
        "kernel_binding": {"container_root": "/out", "container_kernel_dir": "/out/build",
                            "closure_inventory": roots[0]["inventory"]},
        "kernel_inventory": driver._tree_inventory(out / "build", visible_roots={"/out": out, "/nightly": nightly}, allow_visible_root=True),
        "image_tools": {name: dict(tools[name]) for name in required if name != "rustc"},
        "libraries": libraries,
        "mounted_tools": {"rustc": {"path": "/nightly/bin/rustc", "sha256": _digest(nightly / "bin/rustc"),
                                       "version": nightly_version}},
        "toolchain_roots": roots, "path_dirs": ["/nightly/bin", "/usr/bin"],
        "linux_probe": {"arch": "x86_64", "release": driver.REPRO_ENV["EXPECTED_KERNEL_RELEASE"], "kernel_dir": "/out/build"},
        "environment": {},
    }
    _fail((nightly / "bin/rustc").is_file(), "nightly rustc missing")
    _fail("nightly" in toolchain["mounted_tools"]["rustc"]["version"].lower(),
          "nightly rustc version is not nightly")
    inventory = json.loads(Path(backup_inventory).read_text(encoding="utf-8")) if isinstance(backup_inventory, (str, Path)) else backup_inventory
    _fail(inventory == owner._tree_inventory(backup), "source backup inventory differs")
    work = _directory(owner_work_root, "owner work root")
    evidence_owner = _directory(owner_evidence_root, "owner evidence root")
    _fail(not any(work.iterdir()), "owner work root must be empty")
    _fail(not any(evidence_owner.iterdir()), "owner evidence root must be empty")
    disk = disk_admission or {"host_root": str(host_root), "scratch_root": str(scratch_root),
                              "host_device": Path(host_root).stat().st_dev, "scratch_device": Path(scratch_root).stat().st_dev,
                              "host_free_floor": 16 * 2**30, "scratch_free_floor": 12 * 2**30}
    source_doc = json.loads(manifest.read_text(encoding="utf-8"))
    _fail(isinstance(source_doc, dict), "candidate/input manifest malformed")
    _fail(receipt.get("candidate_sha") == source_doc.get("candidate_sha"), "tool-image receipt candidate differs")
    _fail(receipt.get("retired") is True and receipt.get("base_image") == owner.PREPARER_BASE_IMAGE,
          "tool-image receipt lifecycle/base differs")
    supplemental = None
    bound_gitlink_root = None
    if gitlink_manifest is not None:
        supplemental = _file(gitlink_manifest, "gitlink manifest")
        _fail(gitlink_root is not None, "gitlink checkout root required")
        bound_gitlink_root = _directory(gitlink_root, "gitlink checkout root")
        try:
            owner._disjoint((source, bound_gitlink_root))
        except owner.OwnerError as exc:
            raise PreparationError("gitlink checkout overlaps source") from exc
        supplemental_doc = json.loads(supplemental.read_text(encoding="utf-8"))
        owner._validate_gitlink_manifest(supplemental_doc, supplemental, bound_gitlink_root,
                                         manifest, source_doc.get("candidate_sha"),
                                         source_doc.get("ihk_sha"))
    _fail(toolchain_manifest is not None and request_path is not None,
          "explicit toolchain and request publication paths required")
    final_tc = _fresh(toolchain_manifest, "toolchain manifest")
    final_request = _fresh(request_path, "request")
    protected = (source, backup, out, nightly, work, evidence_owner, manifest,
                 receipt_path, _file(driver_path, "driver"),
                 _file(provenance_path, "provenance"),
                 _file(host_owner_path, "host owner"))
    if supplemental is not None:
        protected += (supplemental, bound_gitlink_root)
    try:
        owner._disjoint((*protected, final_tc, final_request))
    except owner.OwnerError as exc:
        raise PreparationError("publication destination overlaps protected input") from exc

    common = {
        "schema": owner.REQUEST_SCHEMA, "candidate_sha": json.loads(manifest.read_text()).get("candidate_sha"),
        "ihk_sha": json.loads(manifest.read_text()).get("ihk_sha"), "image_id": image_id,
        "jobs": jobs, "timeout": timeout, "source_root": str(source), "source_identity": owner._identity(source),
        "backup_root": str(backup), "backup_identity": owner._identity(backup), "backup_inventory": inventory,
        "disk_identity": owner._identity(source), "source_manifest": str(manifest), "source_manifest_sha256": _digest(manifest),
        "driver_path": str(_file(driver_path, "driver")), "driver_sha256": _digest(driver_path),
        "provenance_path": str(_file(provenance_path, "provenance")), "provenance_sha256": _digest(provenance_path),
        "host_owner_path": str(_file(host_owner_path, "host owner")), "host_owner_sha256": _digest(host_owner_path),
        "toolchain_roots": [{"host_path": str(out), "container_path": "/out", "inventory": roots[0]["inventory"]},
                             {"host_path": str(nightly), "container_path": "/nightly", "inventory": roots[1]["inventory"]}],
        "path_dirs": toolchain["path_dirs"], "nightly": {"rustc_version": nightly_version},
        "host_git": host_git, "image_receipt": str(receipt_path), "image_receipt_sha256": _digest(receipt_path),
        # This was supplied by the reviewed caller, rather than copied from
        # the receipt.  The equality above makes the receipt an assertion of
        # the independently authenticated lock value, not its source.
        "toolchain_lock_sha256": expected_toolchain_lock_sha256,
        "mounts": {"source": "/src", "manifest": "/inputs.json", "toolchain": "/toolchain.json", "driver": "/driver.py", "provenance": "/native_rust_exact_build_offline.py", "work": "/work"},
        "common_exclusion_path": common_exclusion_path, "lease_path": str(lease_path), "owner_evidence_root": str(evidence_owner),
        "attempt_root": str(attempt_root), "work_root": str(work), "output_root": str(fresh_output),
        "evidence_root": str(fresh_evidence), "launcher_aggregate_memory_gib": owner.LAUNCHER_AGGREGATE_GIB,
        "memory_backed_bytes": 0, "aggregate_memory_required": owner.LIMITS["Memory"], "memory_allocation_roots": [str(source), str(backup)] + ([str(bound_gitlink_root)] if bound_gitlink_root is not None else []), "disk_admission": disk,
    }
    if supplemental is not None:
        common.update({"gitlink_manifest": str(supplemental),
                       "gitlink_manifest_sha256": _digest(supplemental),
                       "gitlink_root": str(bound_gitlink_root)})
        common["mounts"] = dict(common["mounts"],
                                 gitlink_manifest="/libdwarf-inputs.json",
                                 gitlink="/src/executer/user/lib/libdwarf/libdwarf")
    _fail(common["candidate_sha"] and common["ihk_sha"], "candidate manifest identities missing")

    def make_request(bound_toolchain):
        request = dict(common)
        request["toolchain_manifest"] = str(bound_toolchain)
        request["toolchain_manifest_sha256"] = _digest(bound_toolchain)
        return request

    # ImageOwner.validate is read-only: it authenticates the complete request
    # but neither starts Docker nor publishes leases/receipts.
    return _publish(toolchain, final_tc, final_request, make_request,
                    lambda request: owner.ImageOwner(request).validate())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=Path); parser.add_argument("--request", required=True)
    args = parser.parse_args()
    values = json.loads(args.inputs.read_text(encoding="utf-8")); values["request_path"] = args.request
    try: prepare(**values)
    except (PreparationError, OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
