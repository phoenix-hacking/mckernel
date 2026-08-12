#!/usr/bin/env python3
"""Validate the unattached native Rust IHK raw-page ownership registry.

This checker freezes the safe, allocation-free source foundation and its exact
Rocky compiler fixture. It is structurally incapable of granting IHK-006
credit: kernel ownership, legacy adapters, Kbuild attachment, and runtime proof
remain explicit blockers.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path(
    "host-kernel/native-rust/ihk-page-owner-registry-contract-v1.json"
)
EXPECTED_COMPILER = (
    "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
)
EXPECTED_TESTS = [
    "construction_requires_caller_capacity_and_issues_distinct_identities",
    "allocation_lease_remains_owned_until_typed_release",
    "exact_capacity_full_failure_preserves_allocator_state",
    "double_free_and_stale_generation_are_distinct",
    "foreign_registry_handle_cannot_release_current_owner",
    "raw_address_release_is_exact_and_fails_closed",
    "backing_allocator_failure_does_not_consume_free_slot",
    "failed_release_retains_lease_for_retry",
    "aligned_byte_metadata_round_trips_exactly",
    "registry_drop_drains_every_retained_lease_once",
    "locked_concurrency_preserves_unique_addresses_and_accounting",
    "address_only_aba_limit_is_explicit_while_typed_handle_stays_stale",
]
EXPECTED_INTERNAL_TESTS = [
    "wrong_kind_and_overlapping_release_are_rejected_without_clearing",
    "generation_exhaustion_never_wraps_or_allocates",
    "forged_handle_metadata_cannot_clear_a_live_lease",
]
EXPECTED_UNPROVEN = [
    "native ihk crate-root, authoritative staging manifest, and Kbuild integration",
    "audited Linux irqsave-equivalent outer owner lock enforcing IRQ-disabled, nonpreemptible, no-sleep, non-reentrant execution and registry-to-allocator lock order",
    "pinned allocator and slot-storage owner with an audited drain-before-module-teardown path",
    "six versioned legacy allocation/free export adapters and all consumer migration",
    "generation-free legacy raw-address stale request after identical address-and-size reuse, which the frozen ABI cannot distinguish from the current owner",
    "registry capacity sizing plus bounded O(capacity) scan and drain latency while IRQs are disabled",
    "exact Rocky 10.2 kernel compilation, modpost, module load, unload, and allocator runtime",
    "differential legacy behavior, failure injection, KCSAN, lockdep, fragmentation pressure, and long-run leak evidence",
    "IHK-006 gate completion or credit",
]


class ValidationError(Exception):
    """Raised when the registry source foundation drifts or overclaims proof."""


def _object_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValidationError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _load_json(path):
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError("cannot load {0}: {1}".format(path, error))
    if not isinstance(value, dict):
        raise ValidationError("{0} must contain an object".format(path))
    return value


def _require_keys(value, expected, label):
    if not isinstance(value, dict):
        raise ValidationError("{0} must be an object".format(label))
    actual = set(value)
    if actual != expected:
        raise ValidationError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(expected - actual), sorted(actual - expected)
            )
        )


def _repo_file(repo, relative, label):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError("{0} must be a non-empty POSIX path".format(label))
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValidationError("{0} escapes repository".format(label))
    candidate = repo / relative_path
    try:
        candidate.lstat()
    except OSError as error:
        raise ValidationError("{0} is unavailable: {1}".format(label, error))
    if candidate.is_symlink() or not candidate.is_file():
        raise ValidationError("{0} must be a regular non-symlink file".format(label))
    try:
        candidate.resolve().relative_to(repo.resolve())
    except ValueError:
        raise ValidationError("{0} resolves outside repository".format(label))
    return candidate


def _read_text(path, label):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValidationError("cannot read {0}: {1}".format(label, error))


def _sha256(path):
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValidationError("cannot hash {0}: {1}".format(path, error))
    return digest.hexdigest()


def _require_once(text, fragment, label):
    count = text.count(fragment)
    if count != 1:
        raise ValidationError(
            "{0} must occur exactly once, found {1}".format(label, count)
        )


def _require_order(text, fragments, label):
    position = -1
    for fragment in fragments:
        position = text.find(fragment, position + 1)
        if position < 0:
            raise ValidationError(
                "{0} lacks ordered fragment: {1}".format(label, fragment)
            )


def _function_body(source, signature, label):
    start = source.find(signature)
    if start < 0:
        raise ValidationError("source lacks {0}".format(label))
    opening = source.find("{", start + len(signature))
    if opening < 0:
        raise ValidationError("{0} lacks an opening brace".format(label))
    depth = 0
    for position in range(opening, len(source)):
        character = source[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : position]
    raise ValidationError("{0} lacks a closing brace".format(label))


def _require_mut_receiver(source, signature, label):
    start = source.find(signature)
    if start < 0:
        raise ValidationError("source lacks {0}".format(label))
    opening = source.find("{", start + len(signature))
    if opening < 0 or "&mut self" not in source[start:opening]:
        raise ValidationError("{0} must require exclusive &mut registry access".format(label))


def _validate_contract(contract):
    _require_keys(
        contract,
        {
            "allocator_dependency",
            "compile_fixture",
            "evidence_policy",
            "foundation_status",
            "gate_id",
            "identity_contract",
            "lifetime_probe",
            "ownership_contract",
            "production_source",
            "protocol",
            "schema_version",
            "sync_probe",
            "unproven",
        },
        "contract",
    )
    if contract["schema_version"] != 1 or contract["gate_id"] != "IHK-006":
        raise ValidationError("unsupported page-owner registry contract identity")
    if contract["foundation_status"] != "source-only-unattached-raw-page-owner-registry":
        raise ValidationError("foundation status differs or overclaims integration")

    source = contract["production_source"]
    _require_keys(source, {"path", "sha256"}, "production_source")
    if source["path"] != "host-kernel/native-rust/page_owner_registry.rs":
        raise ValidationError("contract points at a different registry source")

    dependency = contract["allocator_dependency"]
    _require_keys(
        dependency,
        {"contract_path", "contract_sha256", "source_path", "source_sha256"},
        "allocator_dependency",
    )
    if dependency["source_path"] != "host-kernel/native-rust/page_allocator.rs":
        raise ValidationError("allocator dependency points at a different source")
    if (
        dependency["contract_path"]
        != "host-kernel/native-rust/ihk-page-allocator-contract-v1.json"
    ):
        raise ValidationError("allocator dependency points at a different contract")

    fixture = contract["compile_fixture"]
    _require_keys(
        fixture,
        {
            "compile_arguments",
            "compiler_environment",
            "compiler_version_first_line",
            "expected_test_count",
            "internal_test_names",
            "path",
            "sha256",
            "test_names",
        },
        "compile_fixture",
    )
    if fixture != {
        "compile_arguments": [
            "--edition=2021",
            "--test",
            "-Dwarnings",
            "-C",
            "overflow-checks=yes",
        ],
        "compiler_environment": "IHK_PAGE_OWNER_REGISTRY_RUSTC",
        "compiler_version_first_line": EXPECTED_COMPILER,
        "expected_test_count": 15,
        "internal_test_names": EXPECTED_INTERNAL_TESTS,
        "path": "scripts/tests/fixtures/ihk_page_owner_registry_compile.rs",
        "sha256": fixture["sha256"],
        "test_names": EXPECTED_TESTS,
    }:
        raise ValidationError("exact registry fixture contract differs")

    lifetime = contract["lifetime_probe"]
    _require_keys(
        lifetime,
        {"compile_arguments", "diagnostic_fragments", "path", "sha256"},
        "lifetime_probe",
    )
    if lifetime != {
        "compile_arguments": ["--edition=2021"],
        "diagnostic_fragments": [
            "cannot return value referencing local variable `allocator`",
            "cannot return value referencing local variable `slots`",
        ],
        "path": "scripts/tests/fixtures/ihk_page_owner_registry_lifetime_compile_fail.rs",
        "sha256": lifetime["sha256"],
    }:
        raise ValidationError("registry lifetime probe contract differs")

    sync_probe = contract["sync_probe"]
    _require_keys(
        sync_probe,
        {"compile_arguments", "diagnostic_fragments", "path", "sha256"},
        "sync_probe",
    )
    if sync_probe != {
        "compile_arguments": ["--edition=2021"],
        "diagnostic_fragments": [
            "Cell<()>` cannot be shared between threads safely",
            "required by a bound in `assert_sync`",
        ],
        "path": "scripts/tests/fixtures/ihk_page_owner_registry_sync_compile_fail.rs",
        "sha256": sync_probe["sha256"],
    }:
        raise ValidationError("registry non-Sync probe contract differs")

    for item, label in (
        (source, "source"),
        ({"sha256": dependency["source_sha256"]}, "allocator source"),
        ({"sha256": dependency["contract_sha256"]}, "allocator contract"),
        (fixture, "fixture"),
        (lifetime, "lifetime probe"),
        (sync_probe, "sync probe"),
    ):
        if re.fullmatch(r"[0-9a-f]{64}", item["sha256"] or "") is None:
            raise ValidationError("{0} SHA-256 is malformed".format(label))

    identity = contract["identity_contract"]
    _require_keys(
        identity,
        {
            "foreign_registry_rejected",
            "generation_is_nonzero_and_checked",
            "generation_never_wraps",
            "identity_is_module_lifetime_nonwrapping_atomic",
            "stale_generation_rejected",
        },
        "identity_contract",
    )
    ownership = contract["ownership_contract"]
    _require_keys(
        ownership,
        {
            "address_and_size_must_match",
            "allocation_failure_leaves_slot_free",
            "caller_owned_slot_storage",
            "double_free_rejected",
            "failed_release_retains_lease",
            "full_capacity_leaves_allocator_unchanged",
            "no_heap_or_unsafe_implementation",
            "registry_drop_releases_live_leases",
            "typed_handle_binds_address_blocks_and_bytes",
        },
        "ownership_contract",
    )
    if any(value is not True for value in identity.values()):
        raise ValidationError("every identity condition must remain mandatory")
    if any(value is not True for value in ownership.values()):
        raise ValidationError("every registry ownership condition must remain mandatory")

    if contract["protocol"] != {
        "address_only_release": "exact current address and block count under a caller current-ownership precondition",
        "authoritative_release": "registry identity plus slot generation plus exact copied range",
        "capacity": "fixed caller-owned slot slice; Full is a fail-closed source-only outcome",
        "generation": "nonzero checked u64 per slot; exhausted slots never wrap",
        "mutation": "exclusive &mut registry access behind one future audited kernel outer lock",
        "storage": "Option<PageAllocation> retains the actual lease without allocation or pointer erasure",
    }:
        raise ValidationError("registry protocol differs")

    evidence = contract["evidence_policy"]
    _require_keys(
        evidence,
        {
            "built_into_ihk_validated",
            "exact_kernel_compile_validated",
            "failure_injection_validated",
            "gate_credit_eligible",
            "legacy_adapters_validated",
            "rocky_runtime_validated",
        },
        "evidence_policy",
    )
    if any(value is not False for value in evidence.values()):
        raise ValidationError("source-only registry cannot claim evidence or gate credit")
    if contract["unproven"] != EXPECTED_UNPROVEN:
        raise ValidationError("unproven blocker inventory differs")


def _validate_source(source):
    if not source.startswith("// SPDX-License-Identifier: GPL-2.0\n"):
        raise ValidationError("registry source lacks exact GPL-2.0 SPDX header")
    forbidden = [
        "unsafe ",
        "extern \"C\"",
        "include!",
        "global_asm!",
        "asm!",
        "alloc::",
        "Vec<",
        "Box<",
        "Arc<",
        "Mutex<",
        "ManuallyDrop",
        "MaybeUninit",
        "mem::forget",
        "kmalloc",
        "kfree",
        "unsafe impl",
    ]
    for fragment in forbidden:
        if fragment in source:
            raise ValidationError("forbidden registry implementation: {0}".format(fragment))

    for fragment, label in (
        ("Option<PageAllocation<'allocator, 'storage>>", "retained lease slots"),
        ("slots: &'slots mut [RawPageOwnerSlot", "caller-owned slot slice"),
        ("PhantomData<Cell<()>>", "non-Sync marker"),
        ("static NEXT_REGISTRY_ID: AtomicU64 = AtomicU64::new(1);", "identity source"),
        ("#[must_use = \"discarding this handle loses the generation-aware release proof\"]", "handle must-use"),
        ("#[must_use = \"dropping the registry releases every allocation lease it retains\"]", "registry must-use"),
        ("one audited irqsave-equivalent outer lock", "outer lock blocker"),
        ("local IRQs disabled, preemption disabled, no sleeping", "kernel context blocker"),
        ("Slot storage must be pinned before construction", "pinned owner blocker"),
        ("a stale raw\n    /// request is indistinguishable", "raw ABA limitation"),
        ("RawPageOwnerError::DoubleFree", "double-free classification"),
        ("RawPageOwnerError::StaleHandle", "stale-handle classification"),
        ("RawPageOwnerError::Ownership", "ownership classification"),
    ):
        if fragment not in source:
            raise ValidationError("registry source lacks {0}".format(label))

    registry_fields = _function_body(
        source, "pub(crate) struct RawPageOwnerRegistry", "registry fields"
    )
    if "slots: &'slots mut [RawPageOwnerSlot<'allocator, 'storage>]" not in registry_fields:
        raise ValidationError("registry fields lack caller-owned slot slice")

    constructor = _function_body(source, "pub(crate) fn new(", "registry constructor")
    _require_order(
        constructor,
        [
            "if slots.is_empty() || slots.iter().any(|slot| slot.allocation.is_some())",
            "return Err(RawPageOwnerError::Invalid);",
            "let registry_id = next_registry_id()?;",
            "slots,",
            "_not_sync: PhantomData,",
        ],
        "caller-storage registry construction",
    )

    identity = _function_body(source, "fn next_registry_id()", "registry identity issue")
    _require_order(
        identity,
        [
            "NEXT_REGISTRY_ID.load(Ordering::Relaxed)",
            ".checked_add(1)",
            "RawPageOwnerError::RegistryIdentityExhausted",
            "if current == 0",
            "NEXT_REGISTRY_ID.compare_exchange_weak(",
            "Ok(_) => return Ok(current)",
        ],
        "non-wrapping registry identity issue",
    )

    for signature, allocator_call, label in (
        ("pub(crate) fn allocate(", "allocator.allocate(blocks)?;", "block allocation"),
        (
            "pub(crate) fn allocate_bytes(",
            "allocator.allocate_bytes(bytes, alignment_bytes)?;",
            "byte allocation",
        ),
    ):
        body = _function_body(source, signature, label)
        _require_mut_receiver(source, signature, label)
        _require_order(
            body,
            [
                "let (slot, generation) = self.next_slot()?;",
                "let allocator: &'allocator BitmapPageAllocator<'storage> = self.allocator;",
                allocator_call,
                "Ok(self.commit(slot, generation, allocation))",
            ],
            "slot-before-allocator {0}".format(label),
        )

    next_slot = _function_body(source, "fn next_slot(", "free-slot selection")
    _require_order(
        next_slot,
        [
            "let mut saw_free_slot = false;",
            "for (index, slot) in self.slots.iter().enumerate()",
            "if slot.allocation.is_some()",
            "saw_free_slot = true;",
            "slot.generation.checked_add(1)",
            "if generation != 0",
            "return Ok((index, generation));",
            "RawPageOwnerError::GenerationExhausted",
            "RawPageOwnerError::Full",
        ],
        "non-wrapping free-slot selection",
    )

    commit = _function_body(source, "fn commit(", "lease commit")
    _require_order(
        commit,
        [
            "let range = allocation.range();",
            "let destination = &mut self.slots[slot];",
            "destination.generation = generation;",
            "destination.allocation = Some(allocation);",
            "RawPageAllocationHandle",
        ],
        "infallible lease commit",
    )

    release = _function_body(source, "pub(crate) fn release(", "typed release")
    _require_mut_receiver(source, "pub(crate) fn release(", "typed release")
    for fragment, label in (
        ("handle.registry_id != self.registry_id", "registry identity check"),
        ("handle.generation == 0", "zero generation check"),
        (".get_mut(handle.slot)", "slot bounds check"),
        ("slot.generation != handle.generation", "slot generation check"),
        (".ok_or(RawPageOwnerError::DoubleFree)?", "double-free check"),
        ("range.address() != handle.address()", "address ownership check"),
        ("range.blocks() != handle.blocks()", "block ownership check"),
        ("range.bytes() != handle.bytes()", "byte ownership check"),
    ):
        if fragment not in release:
            raise ValidationError("typed release lacks {0}".format(label))
    _require_order(
        release,
        [
            "handle.registry_id != self.registry_id",
            ".get_mut(handle.slot)",
            "slot.generation != handle.generation",
            ".ok_or(RawPageOwnerError::DoubleFree)?",
            "let range = allocation.range();",
            "range.address() != handle.address()",
            "range.blocks() != handle.blocks()",
            "range.bytes() != handle.bytes()",
            "allocation.try_release()?;",
            "let released = slot.allocation.take();",
            "drop(released);",
        ],
        "validate-release-before-slot-clear transaction",
    )

    raw_release = _function_body(source, "pub(crate) fn release_address(", "raw release")
    _require_mut_receiver(source, "pub(crate) fn release_address(", "raw release")
    _require_order(
        raw_release,
        [
            "if address == 0 || blocks == 0",
            "for (index, slot) in self.slots.iter().enumerate()",
            "let Some(allocation) = slot.allocation.as_ref()",
            "if range.address() != address",
            "if range.blocks() != blocks || found.is_some()",
            "return Err(RawPageOwnerError::Ownership);",
            "found = Some(RawPageAllocationHandle",
            "self.release(found.ok_or(RawPageOwnerError::UnknownAddress)?)",
        ],
        "exact current-address release",
    )

    _require_mut_receiver(source, "fn commit(", "lease commit")

    registry_drop = _function_body(
        source,
        "impl Drop for RawPageOwnerRegistry<'_, '_, '_>",
        "registry Drop",
    )
    _require_order(
        registry_drop,
        ["for slot in self.slots.iter_mut()", "drop(slot.allocation.take());"],
        "registry drain Drop",
    )
    for name in EXPECTED_INTERNAL_TESTS[1:]:
        _require_once(source, "fn {0}()".format(name), "internal test {0}".format(name))


def _validate_allocator_dependency(source):
    attempt = _function_body(source, "pub(crate) fn try_release(", "retryable allocation release")
    _require_order(
        attempt,
        [
            "if !self.owned",
            "return Err(PageAllocatorError::Ownership);",
            ".release_owned(self.range, OwnershipKind::Allocated)?;",
            "self.owned = false;",
            "Ok(())",
        ],
        "release failure retains allocation lease",
    )
    release = _function_body(source, "pub(crate) fn release(mut self)", "allocation release")
    if "self.try_release()" not in release:
        raise ValidationError("consuming allocation release must delegate to retryable release")
    internal = _function_body(
        source,
        "fn wrong_kind_and_overlapping_release_are_rejected_without_clearing()",
        "allocator rollback test",
    )
    _require_order(
        internal,
        [
            "inject_reserved_overlap_for_test(range.address(), range.blocks(), true)",
            "allocation.try_release()",
            "Err(PageAllocatorError::Ownership)",
            "assert!(allocator.bit_is_set(allocator.allocated, 0));",
            "inject_reserved_overlap_for_test(range.address(), range.blocks(), false)",
            "allocation.try_release().unwrap();",
            "assert_eq!(allocation.try_release(), Err(PageAllocatorError::Ownership));",
        ],
        "retryable allocator-release rollback test",
    )


def _validate_fixture(fixture):
    for import_path in (
        '#[path = "../../../host-kernel/native-rust/page_allocator.rs"]',
        '#[path = "../../../host-kernel/native-rust/page_owner_registry.rs"]',
    ):
        _require_once(fixture, import_path, "exact fixture source import")
    for name in EXPECTED_TESTS:
        _require_once(fixture, "fn {0}()".format(name), "fixture test {0}".format(name))
    for fragment, label in (
        ("const THREADS: usize = 8;", "eight-thread contention"),
        ("const OPERATIONS: usize = 200;", "bounded contention operations"),
        ("let registry = Mutex::new(RawPageOwnerRegistry::new", "outer-lock concurrency"),
        ("assert!(!addresses.contains(&handle.address()));", "unique-address oracle"),
        ("Err(RawPageOwnerError::Full)", "full-capacity coverage"),
        ("Err(RawPageOwnerError::DoubleFree)", "double-free coverage"),
        ("Err(RawPageOwnerError::StaleHandle)", "stale-handle coverage"),
        ("inject_reserved_overlap_for_test", "release rollback injection"),
        ("assert_eq!(registry.active_count(), 1);", "retained-lease assertion"),
        ("explicit.release().unwrap();", "consuming allocation release coverage"),
        ("Some(PageAllocatorError::Overlap)", "reservation overlap coverage"),
        ("reservation.release().unwrap();", "reservation release coverage"),
        ("let _retained_handle = registry.allocate(blocks).unwrap();", "must-use retained handle coverage"),
        ("A generation-free legacy request cannot distinguish these owners.", "raw ABA oracle"),
    ):
        if fragment not in fixture:
            raise ValidationError("registry fixture lacks {0}".format(label))


def _validate_lifetime_probe(probe):
    for fragment, label in (
        ("fn escape_registry() -> RawPageOwnerRegistry<'static, 'static, 'static>", "escaping registry"),
        ("RawPageOwnerRegistry::new(&allocator, &mut slots).unwrap()", "borrowed registry return"),
    ):
        _require_once(probe, fragment, label)


def _validate_sync_probe(probe):
    _require_once(probe, "fn assert_sync<T: Sync>() {}", "Sync bound")
    _require_once(
        probe,
        "assert_sync::<RawPageOwnerRegistry<'static, 'static, 'static>>();",
        "registry Sync rejection",
    )


def validate_repository(repo):
    repo = Path(repo).resolve()
    contract_path = _repo_file(repo, DEFAULT_CONTRACT.as_posix(), "contract")
    contract = _load_json(contract_path)
    _validate_contract(contract)
    paths = {
        "source": _repo_file(repo, contract["production_source"]["path"], "source"),
        "allocator source": _repo_file(
            repo, contract["allocator_dependency"]["source_path"], "allocator source"
        ),
        "allocator contract": _repo_file(
            repo, contract["allocator_dependency"]["contract_path"], "allocator contract"
        ),
        "fixture": _repo_file(repo, contract["compile_fixture"]["path"], "fixture"),
        "lifetime probe": _repo_file(
            repo, contract["lifetime_probe"]["path"], "lifetime probe"
        ),
        "sync probe": _repo_file(repo, contract["sync_probe"]["path"], "sync probe"),
    }
    expected = {
        "source": contract["production_source"]["sha256"],
        "allocator source": contract["allocator_dependency"]["source_sha256"],
        "allocator contract": contract["allocator_dependency"]["contract_sha256"],
        "fixture": contract["compile_fixture"]["sha256"],
        "lifetime probe": contract["lifetime_probe"]["sha256"],
        "sync probe": contract["sync_probe"]["sha256"],
    }
    for label, path in paths.items():
        actual = _sha256(path)
        if actual != expected[label]:
            raise ValidationError(
                "{0} digest differs: expected {1}, got {2}".format(
                    label, expected[label], actual
                )
            )

    source = _read_text(paths["source"], "registry source")
    allocator = _read_text(paths["allocator source"], "allocator source")
    fixture = _read_text(paths["fixture"], "fixture")
    lifetime = _read_text(paths["lifetime probe"], "lifetime probe")
    sync_probe = _read_text(paths["sync probe"], "sync probe")
    _validate_source(source)
    _validate_allocator_dependency(allocator)
    _validate_fixture(fixture)
    _validate_lifetime_probe(lifetime)
    _validate_sync_probe(sync_probe)
    return {
        "gate_id": "IHK-006",
        "source_contract_validated": True,
        "gate_credit_eligible": False,
        "built_into_ihk_validated": False,
        "exact_kernel_compile_validated": False,
        "rocky_runtime_validated": False,
        "legacy_adapters_validated": False,
        "failure_injection_validated": False,
    }


def _resolve_compiler(explicit):
    configured = (
        explicit
        if explicit is not None
        else os.environ.get("IHK_PAGE_OWNER_REGISTRY_RUSTC")
    )
    if configured is not None and configured.strip():
        configured = configured.strip()
        candidate = Path(configured)
        if not candidate.is_absolute():
            found = shutil.which(configured)
            if found is None:
                raise ValidationError(
                    "configured rustc is unavailable: {0}".format(configured)
                )
            candidate = Path(found)
        if not candidate.is_file():
            raise ValidationError(
                "configured rustc is not a regular file: {0}".format(candidate)
            )
        return str(candidate)
    return None


def _run_compile_fail_probe(compiler, repo, environment, contract, name, temporary):
    probe = contract[name]
    output = Path(temporary) / ("ihk-page-owner-" + name)
    command = [compiler] + probe["compile_arguments"] + [
        probe["path"],
        "-o",
        str(output),
    ]
    result = subprocess.run(
        command,
        cwd=str(repo),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=120,
    )
    if result.returncode == 0:
        raise ValidationError("{0} unexpectedly compiled".format(name.replace("_", " ")))
    diagnostics = result.stdout + result.stderr
    for fragment in probe["diagnostic_fragments"]:
        if fragment not in diagnostics:
            raise ValidationError(
                "{0} lacks diagnostic: {1}".format(name.replace("_", " "), fragment)
            )


def validate_configured_fixture(repo, rustc=None, require_rustc=False):
    repo = Path(repo).resolve()
    validate_repository(repo)
    contract = _load_json(_repo_file(repo, DEFAULT_CONTRACT.as_posix(), "contract"))
    _validate_contract(contract)
    compiler = _resolve_compiler(rustc)
    if compiler is None:
        if require_rustc:
            raise ValidationError("exact Rocky rustc is required but absent")
        return {
            "fixture_status": "SKIPPED_NO_CONFIGURED_RUSTC",
            "compiler_version": None,
        }

    environment = dict(os.environ)
    library_directory = str(Path(compiler).resolve().parent.parent / "lib64")
    if Path(library_directory).is_dir():
        prior = environment.get("LD_LIBRARY_PATH")
        environment["LD_LIBRARY_PATH"] = (
            library_directory
            if not prior
            else library_directory + os.pathsep + prior
        )
    version = subprocess.run(
        [compiler, "--version"],
        cwd=str(repo),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=30,
    )
    if version.returncode != 0:
        raise ValidationError("configured rustc --version failed")
    first_line = version.stdout.splitlines()[0] if version.stdout.splitlines() else ""
    if first_line != EXPECTED_COMPILER:
        raise ValidationError(
            "configured rustc version differs: expected {0!r}, got {1!r}".format(
                EXPECTED_COMPILER, first_line
            )
        )

    fixture = contract["compile_fixture"]
    with tempfile.TemporaryDirectory(prefix="ihk-page-owner-registry-") as temporary:
        output = Path(temporary) / "ihk-page-owner-registry-tests"
        command = [compiler] + fixture["compile_arguments"] + [
            fixture["path"],
            "-o",
            str(output),
        ]
        compiled = subprocess.run(
            command,
            cwd=str(repo),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=120,
        )
        if compiled.returncode != 0:
            raise ValidationError(
                "page-owner registry fixture compilation failed: {0}".format(
                    compiled.stderr.strip()
                )
            )
        executed = subprocess.run(
            [str(output), "--nocapture", "--test-threads=1"],
            cwd=str(repo),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=120,
        )
        if executed.returncode != 0:
            raise ValidationError(
                "page-owner registry fixture execution failed: {0}".format(
                    executed.stdout.strip()
                )
            )
        match = re.search(
            r"test result: ok\. (\d+) passed; 0 failed; 0 ignored; 0 measured; 0 filtered out",
            executed.stdout,
        )
        if match is None or int(match.group(1)) != fixture["expected_test_count"]:
            raise ValidationError("fixture did not execute the exact contracted test count")
        _run_compile_fail_probe(
            compiler, repo, environment, contract, "lifetime_probe", temporary
        )
        _run_compile_fail_probe(
            compiler, repo, environment, contract, "sync_probe", temporary
        )

    return {
        "fixture_status": "EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED",
        "compiler_version": first_line,
    }


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--rustc")
    parser.add_argument("--require-rustc", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        result = validate_repository(Path(args.repo))
        result.update(
            validate_configured_fixture(
                Path(args.repo), rustc=args.rustc, require_rustc=args.require_rustc
            )
        )
    except (ValidationError, OSError, subprocess.SubprocessError) as error:
        print("IHK page-owner registry validation failed: {0}".format(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(
            "SOURCE-CONTRACT-VERIFIED fixture={0} attached=NOT_PROVEN "
            "legacy_adapters=NOT_PROVEN runtime=NOT_PROVEN "
            "gate_credit=FORBIDDEN".format(result["fixture_status"])
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
