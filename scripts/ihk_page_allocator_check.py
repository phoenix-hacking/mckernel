#!/usr/bin/env python3
"""Validate the bounded native Rust IHK page-allocator foundation.

The checker is intentionally incapable of granting IHK-006 credit.  It binds
the frozen legacy oracle, production source, and exact-compiler fixture; checks
the ownership and arithmetic invariants; and optionally compiles/runs the
fixture with the configured Rocky rustc.  Missing compiler input is an explicit
skip, while a configured compiler mismatch or failure is fatal.
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
DEFAULT_CONTRACT = Path("host-kernel/native-rust/ihk-page-allocator-contract-v1.json")
EXPECTED_COMPILER = (
    "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
)
EXPECTED_UNPROVEN = [
    "native ihk crate-root and Kbuild integration",
    "audited Linux spin_lock_irqsave-equivalent adapter enforcing IRQ-disabled, nonpreemptible, no-sleep, and non-reentrant execution for every operation including Drop",
    "six versioned legacy export adapters, raw-address registry integration, generation-free address adapter ownership proof, and consumer migration",
    "exact Rocky 10.2 kernel compilation, modpost, load, and unload",
    "differential legacy allocation, exhaustion, fragmentation, errno behavior, and deliberate boundary deltas",
    "bounded irq-disabled latency and large fragmented-allocation pressure",
    "fault injection, KCSAN, lockdep, and long-run leak evidence",
    "IHK-006 gate completion or credit",
]


class ValidationError(Exception):
    """Raised when the page-allocator foundation drifts or overclaims proof."""


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


def _require_at_least(text, fragment, count, label):
    actual = text.count(fragment)
    if actual < count:
        raise ValidationError(
            "{0} must occur at least {1} times, found {2}".format(label, count, actual)
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


def _validate_contract(contract):
    _require_keys(
        contract,
        {
            "compile_fixture",
            "evidence_policy",
            "foundation_status",
            "gate_id",
            "intentional_legacy_deltas",
            "legacy_oracle",
            "lifetime_probe",
            "must_use_probe",
            "ownership_contract",
            "production_source",
            "protocol",
            "schema_version",
            "unproven",
        },
        "contract",
    )
    if contract["schema_version"] != 1 or contract["gate_id"] != "IHK-006":
        raise ValidationError("unsupported page-allocator contract identity")
    if contract["foundation_status"] != "source-only-bitmap-page-allocator":
        raise ValidationError("foundation status differs or overclaims integration")

    _require_keys(contract["production_source"], {"path", "sha256"}, "production_source")
    if contract["production_source"]["path"] != "host-kernel/native-rust/page_allocator.rs":
        raise ValidationError("contract points at a different production source")

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
    expected_tests = [
        "validates_constructor_ranges_and_storage",
        "exact_capacity_fifo_drop_and_explicit_release_restore_space",
        "alignment_and_bitmap_word_crossing_are_exact",
        "reservations_exclude_allocations_and_roll_back_on_drop",
        "fragmentation_accounting_and_coalescing_are_deterministic",
        "byte_api_and_range_errors_fail_closed",
        "concurrent_allocations_never_overlap_and_restore_every_block",
        "reserve_over_allocated_is_rejected_and_ownership_remains_exact",
        "concurrent_reserve_release_snapshot_preserves_invariants",
        "physical_alignment_uses_absolute_base",
        "partial_tail_capacities_are_exact",
        "overflow_and_zero_input_matrix_fails_closed",
        "copied_range_metadata_does_not_extend_lease_ownership",
    ]
    if fixture["path"] != "scripts/tests/fixtures/ihk_page_allocator_compile.rs":
        raise ValidationError("contract points at a different compile fixture")
    if (
        fixture["test_names"] != expected_tests
        or fixture["internal_test_names"]
        != ["wrong_kind_and_overlapping_release_are_rejected_without_clearing"]
        or fixture["expected_test_count"] != 14
    ):
        raise ValidationError("compile fixture fourteen-test inventory differs")
    if fixture["compile_arguments"] != [
        "--edition=2021",
        "--test",
        "-Dwarnings",
        "-C",
        "overflow-checks=yes",
    ]:
        raise ValidationError("exact compile arguments differ")
    if fixture["compiler_environment"] != "IHK_PAGE_ALLOCATOR_RUSTC":
        raise ValidationError("compiler environment name differs")
    if fixture["compiler_version_first_line"] != EXPECTED_COMPILER:
        raise ValidationError("exact Rocky compiler identity differs")
    probe = contract["must_use_probe"]
    _require_keys(
        probe,
        {"compile_arguments", "diagnostic_fragments", "path", "sha256"},
        "must_use_probe",
    )
    if probe != {
        "compile_arguments": ["--edition=2021", "-Dunused-must-use"],
        "diagnostic_fragments": [
            "unused `PageAllocation` that must be used",
            "unused `PageReservation` that must be used",
        ],
        "path": "scripts/tests/fixtures/ihk_page_allocator_must_use_compile_fail.rs",
        "sha256": probe["sha256"],
    }:
        raise ValidationError("must-use compile-fail probe contract differs")
    lifetime = contract["lifetime_probe"]
    _require_keys(
        lifetime,
        {"compile_arguments", "diagnostic_fragments", "path", "sha256"},
        "lifetime_probe",
    )
    if lifetime != {
        "compile_arguments": ["--edition=2021"],
        "diagnostic_fragments": [
            "error[E0515]",
            "cannot return value referencing local variable `allocator`",
        ],
        "path": "scripts/tests/fixtures/ihk_page_allocator_lifetime_compile_fail.rs",
        "sha256": lifetime["sha256"],
    }:
        raise ValidationError("lifetime compile-fail probe contract differs")
    for item, label in (
        (contract["production_source"], "source"),
        (fixture, "fixture"),
        (probe, "must-use probe"),
        (lifetime, "lifetime probe"),
    ):
        if re.fullmatch(r"[0-9a-f]{64}", item["sha256"] or "") is None:
            raise ValidationError("{0} SHA-256 is malformed".format(label))

    oracle = contract["legacy_oracle"]
    _require_keys(
        oracle,
        {
            "header_path",
            "header_sha256",
            "source_commit",
            "source_path",
            "source_sha256",
            "symbols",
        },
        "legacy_oracle",
    )
    if oracle != {
        "header_path": "ihk/linux/include/ihk/ihk_host_misc.h",
        "header_sha256": "50e7931e58fe623d7102867e59ecb88d0b31ddc1bd64e28ec64b0c76789ad584",
        "source_commit": "3114d9e7101ad52030eb3effa849a5c108972a1f",
        "source_path": "ihk/linux/core/mem_alloc.c",
        "source_sha256": "352d40a1eab04e45b83f79bcfee833e4d7a19ca3b82b7e3096a0f5708d1d3be6",
        "symbols": [
            "ihk_pagealloc_init",
            "ihk_pagealloc_destroy",
            "ihk_pagealloc_alloc",
            "ihk_pagealloc_free",
            "ihk_pagealloc_alloc_size",
            "ihk_pagealloc_free_size",
        ],
    }:
        raise ValidationError("frozen legacy allocator oracle differs")

    expected_deltas = [
        "reject zero, non-power-of-two, misaligned, truncated-byte, overflowing, and out-of-range inputs",
        "allocate exact contiguous block counts across bitmap-word boundaries instead of forbidding small cross-word ranges or rounding requests of 32 or more blocks to 64-block groups",
        "permit an exact allocation ending at the final bitmap block instead of preserving the legacy large-allocation final-word rejection",
        "apply requested alignment to the absolute physical unit number rather than an allocator-relative bitmap index",
        "separate allocation and reservation ownership maps and reject overlapping or wrong-kind release",
        "return typed outcomes internally and require a later audited legacy ABI adapter",
        "use rollback leases whose Drop paths restore ownership",
    ]
    if contract["intentional_legacy_deltas"] != expected_deltas:
        raise ValidationError("intentional legacy delta inventory differs")

    ownership = contract["ownership_contract"]
    _require_keys(
        ownership,
        {
            "allocation_drop_rolls_back",
            "allocator_metadata_allocates_no_memory",
            "bitmap_storage_caller_owned",
            "drop_requires_irqsave_nonpreemptible_no_sleep_context",
            "double_or_wrong_kind_release_rejected",
            "failed_explicit_release_retains_lease",
            "leases_are_must_use",
            "operation_lock_requires_non_reentrant_context",
            "range_metadata_does_not_extend_lease_ownership",
            "reservation_drop_rolls_back",
        },
        "ownership_contract",
    )
    if any(value is not True for value in ownership.values()):
        raise ValidationError("every allocator ownership condition must remain mandatory")

    if contract["protocol"] != {
        "alignment": "power-of-two allocator-unit counts applied to the absolute physical unit number",
        "allocation_policy": "legacy-effective first-fit exact contiguous range",
        "bitmap_word_bits": 64,
        "range_end": "exclusive checked u64 physical address",
        "reservation_policy": "exact non-overlapping physical interval",
        "unit": "nonzero power-of-two bytes",
        "zero_physical_address": "rejected because legacy ABI reserves zero as failure",
    }:
        raise ValidationError("allocator protocol differs")

    _require_keys(
        contract["evidence_policy"],
        {
            "built_into_ihk_validated",
            "differential_legacy_parity_validated",
            "exact_kernel_compile_validated",
            "failure_injection_validated",
            "gate_credit_eligible",
            "rocky_runtime_validated",
        },
        "evidence_policy",
    )
    if any(value is not False for value in contract["evidence_policy"].values()):
        raise ValidationError("source-only contract cannot claim evidence or gate credit")
    if contract["unproven"] != EXPECTED_UNPROVEN:
        raise ValidationError("unproven blocker inventory differs")


def _validate_source(source):
    if not source.startswith("// SPDX-License-Identifier: GPL-2.0\n"):
        raise ValidationError("production source lacks exact GPL-2.0 SPDX header")
    forbidden = [
        "unsafe ",
        "extern \"C\"",
        "include!",
        "global_asm!",
        "asm!",
        "alloc::",
        "Vec<",
        "Box<",
        "kmalloc",
        "kfree",
        "ihk_pagealloc_",
        "next_hint",
        "AtomicUsize",
    ]
    for fragment in forbidden:
        if fragment in source:
            raise ValidationError("forbidden implementation boundary: {0}".format(fragment))

    for fragment, label in (
        ("const BITS_PER_WORD: usize = u64::BITS as usize;", "64-bit bitmap word"),
        ("allocated: &'storage [AtomicU64]", "separate allocation map"),
        ("reserved: &'storage [AtomicU64]", "separate reservation map"),
        ("operation_lock: AtomicBool", "serialized operation lock"),
        ("#[must_use = \"dropping the allocation lease immediately releases its physical range\"]", "allocation must-use contract"),
        ("#[must_use = \"dropping the reservation lease immediately releases its physical range\"]", "reservation must-use contract"),
        ("This is copied metadata, not an ownership token.", "range metadata lifetime contract"),
        ("valid only while this lease remains alive", "lease-scoped range validity"),
        ("audited Linux irqsave-equivalent adapter", "irqsave integration precondition"),
        ("disables local IRQs and", "IRQ-disabled integration precondition"),
        ("preemption, cannot sleep", "nonpreemptible no-sleep integration precondition"),
        ("including lease `Drop`", "Drop integration precondition"),
        ("PageAllocatorError::Overlap", "overlap rejection"),
        ("PageAllocatorError::Ownership", "ownership rejection"),
        ("largest_free_run", "fragmentation accounting"),
        ("Ordering::Acquire", "lock acquire ordering"),
        ("Ordering::Release", "lock release ordering"),
    ):
        if fragment not in source:
            raise ValidationError("source lacks {0}".format(label))

    _require_once(source, "impl Drop for PageAllocation<'_, '_>", "allocation Drop")
    _require_once(source, "impl Drop for PageReservation<'_, '_>", "reservation Drop")
    _require_at_least(source, ".release_owned(self.range, OwnershipKind::Allocated)", 2, "allocation rollback")
    _require_at_least(source, ".release_owned(self.range, OwnershipKind::Reserved)", 2, "reservation rollback")
    _require_at_least(source, ".checked_mul(self.unit_bytes)", 3, "checked range multiplication")

    retryable_release = _function_body(
        source, "pub(crate) fn try_release(", "retryable allocation release"
    )
    _require_order(
        retryable_release,
        [
            "if !self.owned",
            "return Err(PageAllocatorError::Ownership);",
            ".release_owned(self.range, OwnershipKind::Allocated)?;",
            "self.owned = false;",
            "Ok(())",
        ],
        "failure-preserving explicit allocation release",
    )
    consuming_release = _function_body(
        source, "pub(crate) fn release(mut self)", "consuming allocation release"
    )
    if "self.try_release()" not in consuming_release:
        raise ValidationError("consuming allocation release must use retryable release")

    constructor = _function_body(source, "pub(crate) fn new(", "allocator constructor")
    for fragment, label in (
        ("unit_bytes.is_power_of_two()", "power-of-two unit validation"),
        ("start == 0", "zero-address failure-sentinel rejection"),
        ("start % unit_bytes != 0", "start alignment validation"),
        ("size_bytes % unit_bytes != 0", "size alignment validation"),
        (".checked_add(size_bytes)", "checked physical end"),
        (".checked_add(BITS_PER_WORD - 1)", "checked bitmap word ceiling"),
        ("allocated_storage.len() < required_words", "allocation bitmap bounds"),
        ("reserved_storage.len() < required_words", "reservation bitmap bounds"),
    ):
        if fragment not in constructor:
            raise ValidationError("constructor lacks {0}".format(label))

    allocation = _function_body(source, "pub(crate) fn allocate_aligned(", "aligned allocation")
    if allocation.count("let _guard = self.lock();") != 1:
        raise ValidationError("aligned allocation must take exactly one local operation lock")
    for fragment, label in (
        ("!alignment_blocks.is_power_of_two()", "alignment validation"),
        ("let base_block = self.start / self.unit_bytes;", "physical base block"),
        ("for candidate in 0..self.block_count", "legacy-effective first-fit search"),
        ("candidate.checked_add(blocks)", "checked candidate limit"),
        ("limit > self.block_count", "candidate capacity bound"),
        (".checked_add(candidate_u64)", "checked physical block"),
        ("physical_block % alignment_blocks != 0", "absolute physical alignment test"),
        ("!self.range_is_clear(candidate, blocks)", "dual-map allocation exclusion"),
    ):
        if fragment not in allocation:
            raise ValidationError("aligned allocation lacks {0}".format(label))
    _require_order(
        allocation,
        [
            "let _guard = self.lock();",
            "let base_block = self.start / self.unit_bytes;",
            "for candidate in 0..self.block_count",
            "candidate.checked_add(blocks)",
            "limit > self.block_count",
            "!self.range_is_clear(candidate, blocks)",
            "let range = self.range_from_blocks(candidate, blocks)?;",
            "self.set_range(self.allocated, candidate, blocks, true);",
            "return Ok(PageAllocation",
        ],
        "serialized allocation transaction",
    )

    reservation = _function_body(source, "pub(crate) fn reserve(", "reservation")
    if reservation.count("let _guard = self.lock();") != 1:
        raise ValidationError("reservation must take exactly one local operation lock")
    _require_order(
        reservation,
        [
            "let start_block = self.validate_range(address, blocks)?;",
            "let _guard = self.lock();",
            "if !self.range_is_clear(start_block, blocks)",
            "let range = self.range_from_blocks(start_block, blocks)?;",
            "self.set_range(self.reserved, start_block, blocks, true);",
            "Ok(PageReservation",
        ],
        "fallible-before-commit reservation transaction",
    )

    snapshot = _function_body(source, "pub(crate) fn snapshot(", "snapshot")
    if snapshot.count("let _guard = self.lock();") != 1:
        raise ValidationError("snapshot must take exactly one local operation lock")
    _require_order(
        snapshot,
        [
            "let _guard = self.lock();",
            "for block in 0..self.block_count",
            "let allocated = self.bit_is_set(self.allocated, block);",
            "let reserved = self.bit_is_set(self.reserved, block);",
            "PageAllocatorSnapshot",
        ],
        "serialized snapshot transaction",
    )

    release = _function_body(source, "fn release_owned(", "owned release")
    if release.count("let _guard = self.lock();") != 1:
        raise ValidationError("owned release must take exactly one local operation lock")
    _require_order(
        release,
        [
            "let start_block = self.validate_range(range.address, range.blocks)?;",
            "range.bytes",
            "let _guard = self.lock();",
            "let (owned, other) = match kind",
            "if !self.range_is_set(owned, start_block, range.blocks)",
            "|| self.range_has_any(other, start_block, range.blocks)",
            "return Err(PageAllocatorError::Ownership);",
            "self.set_range(owned, start_block, range.blocks, false);",
        ],
        "serialized exact-kind release transaction",
    )

    clear = _function_body(source, "fn range_is_clear(", "dual-map clear check")
    _require_order(
        clear,
        [
            "!self.range_has_any(self.allocated, start, blocks)",
            "&& !self.range_has_any(self.reserved, start, blocks)",
        ],
        "dual-map clear check",
    )
    _require_once(
        source,
        "fn wrong_kind_and_overlapping_release_are_rejected_without_clearing()",
        "ownership invariant test",
    )
    ownership_test = _function_body(
        source,
        "fn wrong_kind_and_overlapping_release_are_rejected_without_clearing()",
        "ownership invariant test",
    )
    _require_order(
        ownership_test,
        [
            "inject_reserved_overlap_for_test(range.address(), range.blocks(), true)",
            "allocation.try_release()",
            "Err(PageAllocatorError::Ownership)",
            "assert!(allocator.bit_is_set(allocator.allocated, 0));",
            "inject_reserved_overlap_for_test(range.address(), range.blocks(), false)",
            "allocation.try_release().unwrap();",
            "assert_eq!(allocation.try_release(), Err(PageAllocatorError::Ownership));",
        ],
        "failed explicit release retains ownership test",
    )


def _validate_fixture(fixture, test_names):
    _require_once(
        fixture,
        '#[path = "../../../host-kernel/native-rust/page_allocator.rs"]',
        "production-source fixture import",
    )
    for name in test_names:
        _require_once(fixture, "fn {0}()".format(name), "fixture test {0}".format(name))
    for fragment, label in (
        ("const THREADS: usize = 8;", "eight-thread contention"),
        ("const OPERATIONS: usize = 300;", "bounded contention operations"),
        ("let active_ranges = Arc::new(Mutex::new", "concurrent overlap oracle"),
        ("end <= *other_start || range.address() >= *other_end", "pairwise overlap assertion"),
        ("assert!(active_ranges.lock().unwrap().is_empty());", "overlap-oracle teardown"),
        ("largest_free_run", "fragmentation assertion"),
        ("PageAllocatorError::Exhausted", "exhaustion assertions"),
        ("PageAllocatorError::Overlap", "overlap assertion"),
        ("PageAllocatorError::Invalid", "invalid-input assertions"),
        ("reservation.release().unwrap();", "explicit reservation release"),
        ("first.release().unwrap();", "explicit allocation release"),
        ("assert_eq!(coalesced.range().address(), 0x50_0000 + 24 * 4096);", "legacy-effective first-fit oracle"),
        ("fn reserve_over_allocated_is_rejected_and_ownership_remains_exact()", "reserve-over-allocated coverage"),
        ("fn concurrent_reserve_release_snapshot_preserves_invariants()", "concurrent reserve/release/snapshot coverage"),
        ("snapshot.allocated_blocks\n                            + snapshot.reserved_blocks\n                            + snapshot.free_blocks", "concurrent accounting invariant"),
        ("fn physical_alignment_uses_absolute_base()", "misaligned-base alignment coverage"),
        ("assert_eq!(lease.range().address(), 64 * 4096);", "absolute alignment oracle"),
        ("for capacity in [1_usize, 63, 65, 127]", "partial-tail capacity matrix"),
        ("assert_eq!(allocator.allocate(2).err(), Some(PageAllocatorError::Exhausted));", "tail candidate limit oracle"),
        ("fn overflow_and_zero_input_matrix_fails_closed()", "overflow and zero matrix"),
        ("(1, u64::MAX - 1, 1)", "bitmap ceiling overflow case"),
        ("allocator.reserve(0xc0_0000, usize::MAX)", "release-range multiplication overflow analogue"),
        ("fn copied_range_metadata_does_not_extend_lease_ownership()", "range lifetime coverage"),
        ("assert_eq!(replacement.range().address(), copied_metadata.address());", "first-fit metadata reuse oracle"),
    ):
        if fragment not in fixture:
            raise ValidationError("fixture lacks {0}".format(label))


def _validate_must_use_probe(probe):
    _require_once(
        probe,
        '#[path = "../../../host-kernel/native-rust/page_allocator.rs"]',
        "must-use production-source import",
    )
    for fragment, label in (
        ("allocator.allocate(1).unwrap();", "discarded allocation lease"),
        ("allocator.reserve(0x1000, 1).unwrap();", "discarded reservation lease"),
    ):
        _require_once(probe, fragment, label)


def _validate_lifetime_probe(probe):
    _require_once(
        probe,
        '#[path = "../../../host-kernel/native-rust/page_allocator.rs"]',
        "lifetime production-source import",
    )
    _require_once(
        probe,
        "fn escaped_lease<'borrow>() -> PageAllocation<'borrow, 'borrow>",
        "escaping lease lifetime probe",
    )
    _require_once(probe, "allocator.allocate(1).unwrap()", "borrowed lease return")


def validate_repository(repo):
    repo = Path(repo).resolve()
    contract_path = _repo_file(repo, DEFAULT_CONTRACT.as_posix(), "contract")
    contract = _load_json(contract_path)
    _validate_contract(contract)

    source_path = _repo_file(repo, contract["production_source"]["path"], "production source")
    fixture_path = _repo_file(repo, contract["compile_fixture"]["path"], "compile fixture")
    probe_path = _repo_file(repo, contract["must_use_probe"]["path"], "must-use probe")
    lifetime_path = _repo_file(repo, contract["lifetime_probe"]["path"], "lifetime probe")
    oracle_source = _repo_file(repo, contract["legacy_oracle"]["source_path"], "legacy source")
    oracle_header = _repo_file(repo, contract["legacy_oracle"]["header_path"], "legacy header")
    for path, expected, label in (
        (source_path, contract["production_source"]["sha256"], "source"),
        (fixture_path, contract["compile_fixture"]["sha256"], "fixture"),
        (probe_path, contract["must_use_probe"]["sha256"], "must-use probe"),
        (lifetime_path, contract["lifetime_probe"]["sha256"], "lifetime probe"),
        (oracle_source, contract["legacy_oracle"]["source_sha256"], "legacy source"),
        (oracle_header, contract["legacy_oracle"]["header_sha256"], "legacy header"),
    ):
        actual = _sha256(path)
        if actual != expected:
            raise ValidationError(
                "{0} digest differs: expected {1}, got {2}".format(label, expected, actual)
            )

    source = _read_text(source_path, "production source")
    fixture = _read_text(fixture_path, "compile fixture")
    probe = _read_text(probe_path, "must-use probe")
    lifetime = _read_text(lifetime_path, "lifetime probe")
    legacy = _read_text(oracle_source, "legacy source")
    header = _read_text(oracle_header, "legacy header")
    _validate_source(source)
    _validate_fixture(fixture, contract["compile_fixture"]["test_names"])
    _validate_must_use_probe(probe)
    _validate_lifetime_probe(lifetime)
    for symbol in contract["legacy_oracle"]["symbols"]:
        if legacy.count("EXPORT_SYMBOL({0});".format(symbol)) != 1:
            raise ValidationError("legacy source export differs: {0}".format(symbol))
        if symbol not in header:
            raise ValidationError("legacy header declaration differs: {0}".format(symbol))

    return {
        "gate_id": "IHK-006",
        "source_contract_validated": True,
        "gate_credit_eligible": False,
        "built_into_ihk_validated": False,
        "exact_kernel_compile_validated": False,
        "rocky_runtime_validated": False,
        "differential_legacy_parity_validated": False,
        "failure_injection_validated": False,
    }


def _resolve_compiler(explicit):
    configured = explicit if explicit is not None else os.environ.get("IHK_PAGE_ALLOCATOR_RUSTC")
    if configured is not None and configured.strip():
        configured = configured.strip()
        candidate = Path(configured)
        if not candidate.is_absolute():
            found = shutil.which(configured)
            if found is None:
                raise ValidationError("configured rustc is unavailable: {0}".format(configured))
            candidate = Path(found)
        if not candidate.is_file():
            raise ValidationError("configured rustc is not a regular file: {0}".format(candidate))
        return str(candidate)
    return None


def validate_configured_fixture(repo, rustc=None, require_rustc=False):
    repo = Path(repo).resolve()
    validate_repository(repo)
    contract = _load_json(_repo_file(repo, DEFAULT_CONTRACT.as_posix(), "contract"))
    _validate_contract(contract)
    compiler = _resolve_compiler(rustc)
    if compiler is None:
        if require_rustc:
            raise ValidationError("exact Rocky rustc is required but absent")
        return {"fixture_status": "SKIPPED_NO_CONFIGURED_RUSTC", "compiler_version": None}

    environment = dict(os.environ)
    library_directory = str(Path(compiler).resolve().parent.parent / "lib64")
    if Path(library_directory).is_dir():
        prior = environment.get("LD_LIBRARY_PATH")
        environment["LD_LIBRARY_PATH"] = (
            library_directory if not prior else library_directory + os.pathsep + prior
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
    with tempfile.TemporaryDirectory(prefix="ihk-page-allocator-") as temporary:
        output = Path(temporary) / "ihk-page-allocator-tests"
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
                "page-allocator fixture compilation failed: {0}".format(
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
                "page-allocator fixture execution failed: {0}".format(executed.stdout.strip())
            )
        match = re.search(
            r"test result: ok\. (\d+) passed; 0 failed; 0 ignored; 0 measured; 0 filtered out",
            executed.stdout,
        )
        if match is None or int(match.group(1)) != fixture["expected_test_count"]:
            raise ValidationError("fixture did not execute the exact contracted test count")

        probe = contract["must_use_probe"]
        probe_output = Path(temporary) / "ihk-page-allocator-must-use-probe"
        probe_command = [compiler] + probe["compile_arguments"] + [
            probe["path"],
            "-o",
            str(probe_output),
        ]
        probed = subprocess.run(
            probe_command,
            cwd=str(repo),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=120,
        )
        if probed.returncode == 0:
            raise ValidationError("must-use compile-fail probe unexpectedly compiled")
        diagnostics = probed.stdout + probed.stderr
        for fragment in probe["diagnostic_fragments"]:
            if fragment not in diagnostics:
                raise ValidationError(
                    "must-use compile-fail probe lacks diagnostic: {0}".format(fragment)
                )

        lifetime = contract["lifetime_probe"]
        lifetime_output = Path(temporary) / "ihk-page-allocator-lifetime-probe"
        lifetime_command = [compiler] + lifetime["compile_arguments"] + [
            lifetime["path"],
            "-o",
            str(lifetime_output),
        ]
        lifetime_result = subprocess.run(
            lifetime_command,
            cwd=str(repo),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=120,
        )
        if lifetime_result.returncode == 0:
            raise ValidationError("lifetime compile-fail probe unexpectedly compiled")
        lifetime_diagnostics = lifetime_result.stdout + lifetime_result.stderr
        for fragment in lifetime["diagnostic_fragments"]:
            if fragment not in lifetime_diagnostics:
                raise ValidationError(
                    "lifetime compile-fail probe lacks diagnostic: {0}".format(fragment)
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
        fixture = validate_configured_fixture(
            Path(args.repo), rustc=args.rustc, require_rustc=args.require_rustc
        )
        result.update(fixture)
    except (ValidationError, OSError, subprocess.SubprocessError) as error:
        print("IHK page-allocator validation failed: {0}".format(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(
            "SOURCE-CONTRACT-VERIFIED fixture={0} kernel_build=NOT_PROVEN "
            "runtime=NOT_PROVEN differential_parity=NOT_PROVEN "
            "failure_injection=NOT_PROVEN gate_credit=FORBIDDEN".format(
                result["fixture_status"]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
