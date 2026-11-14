#!/usr/bin/env python3
"""Bind the unbooted native OS adapter and its executable ownership fixture."""

import argparse
import hashlib
import json
from pathlib import Path


CONTRACT = "host-kernel/contracts/ihk-os-runtime-v1.json"
SOURCE = "host-kernel/native-rust/os_runtime.rs"
INPUTS = (
    SOURCE,
    "host-kernel/native-rust/abi/x86_64.rs",
    "host-kernel/native-rust/os_registry.rs",
    "host-kernel/native-rust/device_registry.rs",
    "host-kernel/native-rust/ihk_ioctl.rs",
    "scripts/tests/fixtures/ihk_os_runtime_compile.rs",
    "scripts/tests/test_ihk_os_runtime.py",
)


def derive_contract(repo):
    inputs = []
    for relative in INPUTS:
        path = Path(repo) / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("native OS input must be a regular file: " + relative)
        data = path.read_bytes()
        inputs.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    return {
        "schema_version": 1,
        "gate_id": "IHK-005-unbooted-adapter",
        "scope": "native unbooted create/status/destroy and Linux character-device ownership",
        "inputs": inputs,
        "behavior": {
            "capacity": 64,
            "minor_allocation": "first-free generation-checked registry transaction",
            "create_command": "0x00112900",
            "destroy_command": "0x00112901",
            "status_commands": ["0x00112a03", "0x00112a14"],
            "status_return": 0,
            "create_argument": "scalar ignored by the frozen SMP create path",
            "destroy_with_open_files_errno": -16,
            "missing_or_out_of_range_destroy_errno": -22,
            "unknown_ioctl_errno": -22,
            "node_family": "/dev/mcosN",
            "linux_major": "dynamic",
            "linux_minor": "OS index 0 through 63",
            "node_publication": "only after kmsg and provider owners exist; open excluded until registry commit",
            "file_owner": "ihk.ko .owner plus one generation-checked OS lease per open file",
            "instance_owner": "one DeviceOsLease and one Linux SMP module reference",
            "kmsg_bytes": 4194304,
            "kmsg_order": 10,
            "kmsg_initialization": "zeroed allocation and in-place ABI length; no large stack temporary",
            "allocation_policy": "sleepable GFP_KERNEL plus ZERO COMP NORETRY NOWARN; no spinlock held",
            "destroy_order": ["exclude new opens", "remove node", "free kmsg", "release provider owners", "recycle minor"],
            "project_c_dispatch": False,
            "resource_assignment": False,
            "image_boot": False,
            "shared_kmsg_readers": False,
        },
        "verification_requirements": {
            "host_fixture": "complete production source with fault-injectable mocked Linux calls",
            "adapter_cases": 10,
            "embedded_provider_registry_cases": 31,
            "kernel_abi_layout_proven_by_mock": False,
            "exact_rocky_build_and_guest_required": True,
            "broader_provider_and_booted_teardown_required": True,
        },
        "gate": {"status": "TODO", "credit_eligible": False, "tracker_credit": False},
    }


def validate_repository(repo):
    expected = derive_contract(repo)
    actual = json.loads((Path(repo) / CONTRACT).read_text())
    if actual != expected:
        raise ValueError("native OS adapter contract differs from its exact source and bounded behavior")
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(derive_contract(args.repo), indent=2, sort_keys=True))
    else:
        validate_repository(args.repo)
        print("IHK unbooted adapter source bound; kernel runtime required; tracker credit forbidden")


if __name__ == "__main__":
    main()
