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
        "scope": "native OS runtime admission across boot, application, service and shutdown, with checked Linux character-device ownership and bounded image-loading state",
        "inputs": inputs,
        "behavior": {
            "capacity": 64,
            "minor_allocation": "first-free generation-checked registry transaction",
            "create_command": "0x00112900",
            "destroy_command": "0x00112901",
            "status_commands": ["0x00112a03", "0x00112a14"],
            "status_return": 0,
            "status_return_scope": "idle NotBooted state; an in-progress image load reports Loading=1",
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
            "destroy_order": ["exclude new opens", "require exclusive NotBooted status",
                              "lock OS operations", "finish backend resource cleanup",
                              "remove node", "free kmsg", "release provider owners", "recycle minor"],
            "project_c_dispatch": False,
            "resource_assignment": "through the checked SMP v2 backend; effects bound by SMP lifecycle contract",
            # These are frozen v1/v2 assertions.  They describe the original
            # unbooted dispatch surface, not the additive v3-v5 lifecycle
            # below; keeping them separate prevents a current booted state
            # from being incorrectly judged against the historical ABI.
            "historical_unbooted_v1": {
                "backend_abi": {"version": 1, "callback_pair_required": True,
                                "trusted_module_code_only": True, "provider_module_retained": True,
                                "generation_source": "live OsLease or exclusive DestroyGuard",
                                "operation_lock": "per-OS sleepable mutex",
                                "allowed_status": "NotBooted",
                                "native_address_bits": 64, "compat_address_bits": 32,
                                "compat_normalization": "zero extend once",
                                "cleanup_failure": "keep node, generation and owners live"},
                "image_boot": False,
            },
            "current_boot_application_service_shutdown": {
                "boot_prepare": "runs only while registry status is NotBooted; a nonzero result returns before Booting, remains NotBooted and leaves prior admission state unchanged",
                "boot_start": "publishes Booting before start; zero publishes Ready, nonzero publishes Failed",
                "boot_start_nonzero": "may have CPU effects and retains non-destroyable generation, owners and resources",
                "resident_application_or_service": "returns EBUSY before v5 shutdown callback until its resident admission owner releases",
                "shutdown_v5_nonzero": "callback must make no teardown effects; ShutdownGuard drop restores the original live registry status while preserving references",
                "shutdown_v6_outcome": "zero is complete; a signed Linux errno is pre-effect; SHUTDOWN_V6_POST_EFFECT tagged errno is post-effect",
                "shutdown_v6_post_effect": "retains Shutdown registry and closed admission for same-generation reconciliation; it cannot be rolled back as pre-effect",
                "shutdown_admission": "close_for_shutdown closes an open idle gate; successful shutdown commits and leaves the gate closed",
                "shutdown_admission_rollback": "ShutdownAdmission drop reopens only an open gate closed by this attempt; a borrowed prior close and overflow poison stay closed",
                "closed_gate_retry": "an idle closed non-poisoned gate can be borrowed for a shutdown retry and remains closed if that retry fails",
                "successful_shutdown": "commits NotBooted with admission closed",
                "reboot": "only successful start reopens a closed non-poisoned gate after Ready publication; a nonzero reboot start publishes Failed and leaves the prior closed gate closed",
                "owner_release_order": "FileService or BackendApplication Close runs before its AdmissionOwner release, which runs before the OS lease release",
            },
            "image_load": {
                "command": "0x00112a00",
                "initial_state": "NotBooted",
                "observable_inflight_state": "Loading",
                "completion_state": "NotBooted after every backend result",
                "serialization": "same per-OS operation mutex as resource assignment and destruction",
                "backend_ownership": "existing IHK OS lease and SMP module reference",
                "starts_cpus": False,
            },
            "shared_kmsg_readers": False,
        },
        "verification_requirements": {
            "host_fixture": "complete production source with fault-injectable mocked Linux calls",
            "adapter_cases": 24,
            "total_cases": 62,
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
