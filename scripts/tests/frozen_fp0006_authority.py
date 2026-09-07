"""Materialize the historical FP-0006 witness inputs, without changing its authority.

The live OS registry and dispatcher now implement additional behavior. These
two old witnesses intentionally retain their original four source/contract
inputs; current foundations and actual module behavior have separate tests.
"""

import hashlib
import io
import json
from pathlib import Path
import tarfile


ARCHIVE = "scripts/tests/fixtures/fp0006-unbooted-source-inputs-3d68165c.tar.gz"
ARCHIVE_SHA256 = "52f05bb9f57ac21f65c7b96fba435726668e6600055debbc40b11700dee35495"
HISTORICAL_PATHS = frozenset((
    "host-kernel/contracts/ihk-ioctl-dispatch-foundation-v1.json",
    "host-kernel/contracts/ihk-os-registry-foundation-v1.json",
    "host-kernel/native-rust/ihk_ioctl.rs",
    "host-kernel/native-rust/os_registry.rs",
))


def materialize(repo, destination, contract_path):
    repo, destination = Path(repo), Path(destination)
    archive = (repo / ARCHIVE).read_bytes()
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("historical FP-0006 source archive digest differs")
    historical = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        members = tar.getmembers()
        if len(members) != len(HISTORICAL_PATHS) or {m.name for m in members} != HISTORICAL_PATHS:
            raise ValueError("historical FP-0006 source archive members differ")
        for member in members:
            if not member.isfile() or not 0 < member.size <= 65536:
                raise ValueError("historical FP-0006 source member is not a bounded file")
            historical[member.name] = tar.extractfile(member).read()
    contract_bytes = (repo / contract_path).read_bytes()
    contract = json.loads(contract_bytes)
    payloads = {contract_path: contract_bytes}
    for binding in list(contract["frozen_inputs"].values()) + list(contract["producers"].values()):
        relative = binding["path"]
        if relative in HISTORICAL_PATHS:
            data = historical[relative]
        else:
            source = repo / relative
            if source.is_symlink() or not source.is_file():
                raise ValueError("FP-0006 source input is not a regular file: " + relative)
            data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != binding["sha256"]:
            raise ValueError("FP-0006 frozen input digest differs: " + relative)
        if "size" in binding and len(data) != binding["size"]:
            raise ValueError("FP-0006 frozen input size differs: " + relative)
        payloads[relative] = data
    # Tests still exercise the actual current validators and the unchanged
    # pinned IHK C reference, including their tamper and namespace controls.
    extras = {"scripts/fp0006_ihk_os_status_alias.py",
              "scripts/fp0006_ihk_device_negative_dispatch.py"}
    if "current_head_boundary" in contract:
        extras.add(contract["current_head_boundary"]["current_host_driver"]["path"])
    for relative in extras:
        if relative not in payloads:
            payloads[relative] = (repo / relative).read_bytes()
    destination.mkdir()
    for relative, data in sorted(payloads.items()):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return destination
