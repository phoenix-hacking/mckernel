#!/usr/bin/env python3
"""Validate the bounded native Rust IHK IKC queue source foundation.

This checker deliberately cannot grant IHK-008 credit.  It binds the reviewed
source and compile fixture, verifies the safety/order invariants that make the
safe queue methods defensible, and optionally compiles/runs the fixture with
the configured exact Rocky rustc.  Absence of a compiler is reported as a
skip; an explicitly configured, incompatible, or failing compiler is an error.
"""

from __future__ import annotations

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
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path("host-kernel/native-rust/ihk-ikc-queue-contract-v1.json")

EXPECTED_UNPROVEN = [
    "exact built ihk.ko incorporation of the statically connected queue source",
    "exact Rocky 10.2 kernel compilation and modpost",
    "Linux-to-McKernel shared-memory runtime interoperability",
    "queue allocation, notification, and teardown integration",
    "KCSAN, lockdep, model-checked concurrency, and stalled-producer recovery",
    "IHK-008 gate completion or credit",
]


class ValidationError(Exception):
    """Raised when the source foundation is incomplete or overclaims proof."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValidationError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError(f"cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


def _require_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValidationError(
            f"{label} keys differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _repo_file(repo: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError(f"{label} must be a non-empty POSIX path")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValidationError(f"{label} escapes the repository: {relative}")
    candidate = repo / relative_path
    try:
        candidate.lstat()
    except OSError as error:
        raise ValidationError(f"{label} is unavailable: {error}") from error
    if candidate.is_symlink() or not candidate.is_file():
        raise ValidationError(f"{label} must be a regular, non-symlink file")
    try:
        candidate.resolve().relative_to(repo.resolve())
    except ValueError as error:
        raise ValidationError(f"{label} resolves outside the repository") from error
    return candidate


def _read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValidationError(f"cannot read {label}: {error}") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValidationError(f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _require_once(text: str, fragment: str, label: str) -> None:
    count = text.count(fragment)
    if count != 1:
        raise ValidationError(f"{label} must occur exactly once, found {count}")


def _require_compact(text: str, fragment: str, label: str) -> None:
    if _compact(fragment) not in _compact(text):
        raise ValidationError(f"source lacks {label}")


def _require_order(text: str, fragments: Iterable[str], label: str) -> None:
    position = -1
    for fragment in fragments:
        found = text.find(fragment, position + 1)
        if found < 0:
            raise ValidationError(f"{label} lacks ordered fragment: {fragment}")
        position = found


def _function_body(text: str, name: str) -> str:
    matches = list(re.finditer(rf"\bfn\s+{re.escape(name)}\s*\(", text))
    if len(matches) != 1:
        raise ValidationError(f"Rust source must define fn {name} exactly once")
    opening = text.find("{", matches[0].end())
    if opening < 0:
        raise ValidationError(f"fn {name} has no body")
    depth = 0
    for index in range(opening, len(text)):
        byte = text[index]
        if byte == "{":
            depth += 1
        elif byte == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    raise ValidationError(f"fn {name} has an unterminated body")


def _validate_contract(contract: dict[str, Any]) -> None:
    _require_keys(
        contract,
        {
            "canonical_abi",
            "compile_fixture",
            "configured_fixture",
            "error_status",
            "evidence_policy",
            "foundation_status",
            "gate_id",
            "legacy_oracle",
            "production_source",
            "protocol",
            "safety_contract",
            "schema_version",
            "unproven",
        },
        "contract",
    )
    if contract["schema_version"] != 1 or contract["gate_id"] != "IHK-008":
        raise ValidationError("unsupported queue contract identity")
    if contract["foundation_status"] != "source-only-bounded-queue":
        raise ValidationError("queue foundation status differs or overclaims integration")

    _require_keys(contract["canonical_abi"], {"path", "sha256", "type"}, "canonical_abi")
    if contract["canonical_abi"] != {
        "path": "host-kernel/native-rust/abi/x86_64.rs",
        "sha256": "b5980e5b621914a120a0e6b72241477c48aee85615ae4cc76077f3874e35f860",
        "type": "IhkIkcQueueHead",
    }:
        raise ValidationError("queue contract must bind the canonical x86_64 queue header")

    _require_keys(contract["production_source"], {"path", "sha256"}, "production_source")
    if contract["production_source"]["path"] != "host-kernel/native-rust/ikc_queue.rs":
        raise ValidationError("queue contract points at a different production source")
    _require_keys(
        contract["compile_fixture"],
        {
            "expected_test_count",
            "fixture_test_names",
            "internal_test_names",
            "path",
            "sha256",
        },
        "compile_fixture",
    )
    fixture = contract["compile_fixture"]
    if fixture["path"] != "scripts/tests/fixtures/ihk_native_queue_compile.rs":
        raise ValidationError("queue contract points at a different compile fixture")
    expected_fixture_tests = [
        "sequential_capacity_fifo_and_legacy_results",
        "counters_wrap_without_changing_slot_order",
        "malformed_metadata_and_short_packets_fail_closed",
        "concurrent_producers_and_consumers_transfer_each_packet_once",
    ]
    if fixture["fixture_test_names"] != expected_fixture_tests:
        raise ValidationError("compile fixture test inventory differs")
    if fixture["internal_test_names"] != [
        "consumer_claim_is_exclusive_and_released_on_every_error"
    ]:
        raise ValidationError("internal queue regression test inventory differs")
    if fixture["expected_test_count"] != 5:
        raise ValidationError("configured fixture must execute exactly five tests")
    for item, label in (
        (contract["canonical_abi"], "canonical ABI"),
        (contract["production_source"], "production source"),
        (fixture, "compile fixture"),
    ):
        digest = item["sha256"]
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValidationError(f"{label} digest must be lowercase SHA-256")

    _require_keys(
        contract["legacy_oracle"],
        {"header_path", "source_commit", "source_path", "write_full_retry_limit"},
        "legacy_oracle",
    )
    if contract["legacy_oracle"] != {
        "header_path": "ihk/ikc/include/ikc/queue.h",
        "source_commit": "3114d9e7101ad52030eb3effa849a5c108972a1f",
        "source_path": "ihk/ikc/queue.c",
        "write_full_retry_limit": 128,
    }:
        raise ValidationError("frozen legacy queue oracle differs")

    _require_keys(
        contract["protocol"],
        {
            "capacity",
            "counter_width_bits",
            "dequeue_order",
            "minimum_packet_count",
            "packet_alignment_bytes",
            "publication_order",
            "wrap_arithmetic",
        },
        "protocol",
    )
    if contract["protocol"] != {
        "capacity": "packet_count - 1",
        "counter_width_bits": 64,
        "dequeue_order": [
            "claim-local-consumer",
            "acquire-published-snapshot",
            "copy-packet",
            "release-read-offset",
            "release-local-consumer",
        ],
        "minimum_packet_count": 2,
        "packet_alignment_bytes": 8,
        "publication_order": [
            "reserve-write-offset-acqrel",
            "copy-packet",
            "publish-max-read-offset-release",
        ],
        "wrap_arithmetic": "u64-wrapping",
    }:
        raise ValidationError("queue protocol contract differs")

    _require_keys(
        contract["safety_contract"],
        {
            "aligned_linux_cmpxchg_peer_required",
            "mapping_aliases_forbidden",
            "mapping_overlap_packets_rejected",
            "non_sleeping_reservation_to_publication_required",
            "remote_dequeue_owner_forbidden",
            "sole_rust_dequeue_owner_required",
            "single_local_queue_view_required",
        },
        "safety_contract",
    )
    if any(value is not True for value in contract["safety_contract"].values()):
        raise ValidationError("every queue safety precondition must remain mandatory")
    if contract["error_status"] != {
        "busy": -16,
        "corrupt": -117,
        "empty": -1,
        "full": -16,
        "invalid": -22,
    }:
        raise ValidationError("queue error/status mapping differs")

    _require_keys(
        contract["evidence_policy"],
        {
            "built_into_ihk_validated",
            "exact_kernel_compile_validated",
            "gate_credit_eligible",
            "performance_parity_validated",
            "rocky_runtime_validated",
            "teardown_validated",
        },
        "evidence_policy",
    )
    if any(value is not False for value in contract["evidence_policy"].values()):
        raise ValidationError("source-only queue contract cannot claim build, runtime, or credit")
    if contract["unproven"] != EXPECTED_UNPROVEN:
        raise ValidationError("queue contract must preserve the exact unproven scope")

    _require_keys(
        contract["configured_fixture"],
        {
            "compile_arguments",
            "compiler_environment",
            "compiler_version_first_line",
            "run_arguments",
            "status_when_compiler_absent",
        },
        "configured_fixture",
    )
    configured = contract["configured_fixture"]
    if configured != {
        "compile_arguments": [
            "--edition=2021",
            "--test",
            "-C",
            "overflow-checks=yes",
        ],
        "compiler_environment": "IHK_NATIVE_QUEUE_RUSTC",
        "compiler_version_first_line": (
            "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
        ),
        "run_arguments": ["--nocapture", "--test-threads=1"],
        "status_when_compiler_absent": "SKIPPED_NO_CONFIGURED_RUSTC",
    }:
        raise ValidationError("configured Rust fixture policy differs")


def _validate_source(text: str, contract: dict[str, Any]) -> None:
    _require_once(
        text,
        "use super::abi::IhkIkcQueueHead;",
        "canonical queue-header import",
    )
    for forbidden in (
        "copy_nonoverlapping",
        'extern "C"',
        'extern "Rust"',
        "include!",
        "include_bytes!",
        "global_asm!",
        "asm!(",
        "use std::",
        "use alloc::",
        "impl Clone for SharedQueue",
    ):
        if forbidden in text:
            raise ValidationError(f"queue source contains forbidden boundary: {forbidden}")

    _require_once(
        text,
        "const LEGACY_WRITE_QUEUE_RETRY: usize = 128;",
        "legacy write retry constant",
    )
    for fragment in (
        "Self::Invalid => -EINVAL",
        "Self::Empty => LEGACY_EMPTY_SENTINEL",
        "Self::Full | Self::Busy => -EBUSY",
        "Self::Corrupt => -EUCLEAN",
        "consumer_active: AtomicBool",
        "unsafe impl Send for SharedQueue<'_> {}",
        "unsafe impl Sync for SharedQueue<'_> {}",
        "pub(crate) unsafe fn attach(",
        "using aligned atomic operations compatible with Linux's `cmpxchg`",
        "Rust must be the sole dequeue owner",
        "no remote endpoint may consume",
        "exactly one local `SharedQueue` view may exist",
        "reference may alias the header or payload",
        "IRQ-disabled/non-sleeping progress rule",
    ):
        if fragment not in text:
            raise ValidationError(f"queue source lacks safety/ABI fragment: {fragment}")
    if text.count("unsafe impl Send for SharedQueue") != 1 or text.count(
        "unsafe impl Sync for SharedQueue"
    ) != 1:
        raise ValidationError("SharedQueue Send/Sync implementations must be unique")

    drop_body = _function_body(text, "drop")
    _require_compact(
        drop_body,
        "self.0.store(false, Ordering::Release);",
        "release-store consumer claim guard",
    )

    initialize = _function_body(text, "initialize")
    for fragment, label in (
        ("packet_bytes % size_of::<u64>() != 0", "8-byte packet alignment rejection"),
        ("packet_count < 2", "minimum packet-count rejection"),
        ("packet_count > u32::MAX as usize", "wire packet-count bound"),
        ("read_offset: 0", "zeroed read counter"),
        ("max_read_offset: 0", "zeroed publication counter"),
        ("write_offset: 0", "zeroed reservation counter"),
        ("queue_size: queue_size as u64", "wire queue-size initialization"),
    ):
        if fragment not in initialize:
            raise ValidationError(f"queue initialize lacks {label}")

    snapshot = _function_body(text, "snapshot")
    for fragment, label in (
        ("packet_size % size_of::<u64>() != 0", "attached packet alignment check"),
        ("packet_count < 2", "attached packet-count check"),
        ("checked_mul(packet_count as usize)", "payload multiplication check"),
        ("queue_size != payload_bytes as u64", "wire queue-size check"),
        ("required > self.mapping_bytes", "mapping bounds check"),
        ("reserved.wrapping_sub(read)", "reserved wrapping distance"),
        ("published.wrapping_sub(read)", "published wrapping distance"),
        ("reserved_distance >= packet_count", "capacity corruption bound"),
        ("published_distance > reserved_distance", "publication corruption bound"),
    ):
        if fragment not in snapshot:
            raise ValidationError(f"queue snapshot lacks {label}")
    if snapshot.count("load(Ordering::Acquire)") != 5:
        raise ValidationError("stable queue snapshot must use five acquire counter loads")
    _require_order(
        snapshot,
        ["read_before", "reserved_before", "let published", "reserved_after", "read_after"],
        "stable queue snapshot bracket",
    )

    packet_pointer = _function_body(text, "packet_pointer")
    if "sequence % state.packet_count" not in packet_pointer:
        raise ValidationError("packet slot selection must wrap by packet_count")

    overlap = _function_body(text, "overlaps_mapping")
    for fragment in (
        "mapping_start + self.mapping_bytes",
        "start.checked_add(bytes)",
        "start < mapping_end && mapping_start < end",
    ):
        if fragment not in overlap:
            raise ValidationError("mapping overlap rejection is incomplete")

    enqueue = _function_body(text, "try_enqueue")
    for fragment, label in (
        ("let mut full_attempts = 0_usize;", "per-call full retry counter"),
        ("full_attempts > LEGACY_WRITE_QUEUE_RETRY", "legacy 128-retry limit"),
        ("self.overlaps_mapping(packet.as_ptr(), state.packet_size)", "input mapping-overlap guard"),
        ("state.reserved.wrapping_add(1)", "wrapping reservation increment"),
        ("current.wrapping_add(1)", "wrapping publication increment"),
        ("state.reserved.wrapping_sub(current) >= state.packet_count", "publication corruption guard"),
    ):
        if fragment not in enqueue:
            raise ValidationError(f"queue enqueue lacks {label}")
    if enqueue.count("compare_exchange_weak(") != 2:
        raise ValidationError("enqueue must contain one reserve and one publish compare-exchange")
    _require_compact(
        enqueue,
        "compare_exchange_weak(state.reserved, state.reserved.wrapping_add(1), "
        "Ordering::AcqRel, Ordering::Acquire,)",
        "acqrel reservation compare-exchange",
    )
    _require_compact(
        enqueue,
        "compare_exchange_weak(current, current.wrapping_add(1), "
        "Ordering::Release, Ordering::Acquire,)",
        "release publication compare-exchange",
    )
    _require_order(
        enqueue,
        [
            "let state = self.snapshot()?;",
            "self.overlaps_mapping(",
            "full_attempts += 1;",
            ".write_counter()",
            "copy(packet.as_ptr(), destination, state.packet_size);",
            ".publish_counter()",
        ],
        "reserve-copy-publish sequence",
    )

    dequeue = _function_body(text, "try_dequeue")
    for fragment, label in (
        ("consumer_active", "process-local consumer guard"),
        ("Ordering::Acquire, Ordering::Relaxed", "consumer claim ordering"),
        ("map_err(|_| QueueError::Busy)", "contended-consumer backpressure"),
        ("self.overlaps_mapping(packet.as_ptr(), state.packet_size)", "output mapping-overlap guard"),
        ("state.read.wrapping_add(1)", "wrapping read increment"),
        ("drop(claim);", "explicit success-path claim release"),
    ):
        if fragment not in dequeue:
            raise ValidationError(f"queue dequeue lacks {label}")
    _require_compact(
        dequeue,
        "compare_exchange_weak(state.read, state.read.wrapping_add(1), "
        "Ordering::Release, Ordering::Acquire,)",
        "release read-offset compare-exchange",
    )
    _require_order(
        dequeue,
        [
            ".consumer_active",
            "let state = self.snapshot()?;",
            "self.overlaps_mapping(",
            "copy(source, packet.as_mut_ptr(), state.packet_size);",
            ".read_counter()",
            "drop(claim);",
        ],
        "claim-snapshot-copy-release dequeue sequence",
    )

    internal_tests = set(
        re.findall(r"#\[test\]\s*fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
    )
    expected_internal = set(contract["compile_fixture"]["internal_test_names"])
    if internal_tests != expected_internal:
        raise ValidationError(
            f"internal queue tests differ: expected={sorted(expected_internal)}, "
            f"actual={sorted(internal_tests)}"
        )
    internal = _function_body(
        text, "consumer_claim_is_exclusive_and_released_on_every_error"
    )
    for outcome in ("Busy", "Empty", "Invalid", "Corrupt"):
        if f"Err(QueueError::{outcome})" not in internal:
            raise ValidationError(f"consumer claim regression lacks {outcome} exit")
    if internal.count("!queue.consumer_active.load") != 3:
        raise ValidationError("consumer claim regression does not prove every error release")


def _validate_fixture(text: str, contract: dict[str, Any]) -> None:
    _require_once(
        text,
        '#[path = "../../../host-kernel/native-rust/abi/x86_64.rs"]',
        "canonical ABI fixture include",
    )
    _require_once(
        text,
        '#[path = "../../../host-kernel/native-rust/ikc_queue.rs"]',
        "production queue fixture include",
    )
    if re.search(r"\bstruct\s+IhkIkcQueueHead\b", text):
        raise ValidationError("compile fixture duplicates the canonical queue header")
    tests = re.findall(r"#\[test\]\s*fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
    if tests != contract["compile_fixture"]["fixture_test_names"]:
        raise ValidationError(f"compile fixture tests differ or changed order: {tests}")
    for fragment, label in (
        ("const PRODUCERS: usize = 4;", "four producers"),
        ("const CONSUMERS: usize = 4;", "four consumers"),
        ("const PER_PRODUCER: usize = 1_000;", "per-producer stress count"),
        ("Err(QueueError::Empty | QueueError::Busy)", "consumer backpressure handling"),
        ("assert!(values_ref.lock().unwrap().insert((producer, sequence)));", "duplicate rejection"),
        ("assert_eq!(values.into_inner().unwrap().len(), TOTAL);", "complete transfer assertion"),
        ("read_offset = u64::MAX", "read-counter wrap fixture"),
        ("max_read_offset = u64::MAX", "published-counter wrap fixture"),
        ("write_offset = u64::MAX", "reserved-counter wrap fixture"),
        ("(*head).queue_size += 1", "metadata-corruption fixture"),
    ):
        if fragment not in text:
            raise ValidationError(f"compile fixture lacks {label}")


def validate_repository(
    repo: Path, contract_path: Path = DEFAULT_CONTRACT
) -> dict[str, Any]:
    repo = repo.resolve()
    if not repo.is_dir():
        raise ValidationError(f"repository is not a directory: {repo}")
    contract_file = (
        contract_path if contract_path.is_absolute() else repo / contract_path
    )
    contract = _load_json(contract_file)
    _validate_contract(contract)

    source_path = _repo_file(
        repo, contract["production_source"]["path"], "production queue source"
    )
    abi_path = _repo_file(repo, contract["canonical_abi"]["path"], "canonical queue ABI")
    fixture_path = _repo_file(
        repo, contract["compile_fixture"]["path"], "queue compile fixture"
    )
    source_text = _read_text(source_path, "production queue source")
    fixture_text = _read_text(fixture_path, "queue compile fixture")
    _validate_source(source_text, contract)
    _validate_fixture(fixture_text, contract)
    if _sha256(abi_path) != contract["canonical_abi"]["sha256"]:
        raise ValidationError("canonical queue ABI digest is stale")
    if _sha256(source_path) != contract["production_source"]["sha256"]:
        raise ValidationError("production queue source digest is stale")
    if _sha256(fixture_path) != contract["compile_fixture"]["sha256"]:
        raise ValidationError("queue compile fixture digest is stale")

    return {
        "built_into_ihk_validated": False,
        "exact_kernel_compile_validated": False,
        "fixture_path": str(fixture_path),
        "fixture_status": "NOT_EVALUATED",
        "gate_credit_eligible": False,
        "gate_id": "IHK-008",
        "performance_parity_validated": False,
        "rocky_runtime_validated": False,
        "source_contract_validated": True,
        "teardown_validated": False,
        "unproven": list(contract["unproven"]),
    }


def _compiler_path(configured: str | None) -> Path | None:
    if configured is None:
        return None
    found = shutil.which(configured)
    if found is None:
        raise ValidationError(f"configured rustc is unavailable: {configured}")
    path = Path(found).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValidationError(f"configured rustc is not an executable file: {path}")
    return path


def _run_command(command: list[str], label: str, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValidationError(f"{label} could not complete: {error}") from error
    if result.returncode != 0:
        diagnostic = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValidationError(f"{label} failed ({result.returncode}): {diagnostic}")
    return result


def validate_configured_fixture(
    repo: Path,
    contract_path: Path = DEFAULT_CONTRACT,
    rustc: str | None = None,
    require_rustc: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve()
    # Keep the fixture entry point fail closed even when callers invoke it
    # directly instead of going through `main`.
    validate_repository(repo, contract_path)
    contract_file = (
        contract_path if contract_path.is_absolute() else repo / contract_path
    )
    contract = _load_json(contract_file)
    _validate_contract(contract)
    configured = rustc
    if configured is None:
        environment_name = contract["configured_fixture"]["compiler_environment"]
        environment_value = os.environ.get(environment_name, "").strip()
        configured = environment_value or None
    compiler = _compiler_path(configured)
    if compiler is None:
        if require_rustc:
            raise ValidationError("exact configured rustc is required but absent")
        return {
            "compiler": None,
            "compiler_version": None,
            "fixture_status": contract["configured_fixture"][
                "status_when_compiler_absent"
            ],
        }

    version_result = _run_command([str(compiler), "--version"], "rustc version probe", 30)
    version_lines = version_result.stdout.splitlines()
    version = version_lines[0].strip() if version_lines else ""
    expected_version = contract["configured_fixture"]["compiler_version_first_line"]
    if version != expected_version:
        raise ValidationError(
            f"configured rustc version differs: expected {expected_version!r}, got {version!r}"
        )

    fixture = _repo_file(
        repo, contract["compile_fixture"]["path"], "queue compile fixture"
    )
    with tempfile.TemporaryDirectory(prefix="ihk-native-queue-fixture-") as temporary:
        binary = Path(temporary) / "ihk-native-queue-tests"
        command = [str(compiler)]
        command.extend(contract["configured_fixture"]["compile_arguments"])
        command.extend([str(fixture), "-o", str(binary)])
        _run_command(command, "queue fixture compilation", 180)
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise ValidationError("rustc did not create an executable queue fixture")
        run_command = [str(binary)] + contract["configured_fixture"]["run_arguments"]
        run = _run_command(run_command, "queue fixture execution", 180)
        expected_count = contract["compile_fixture"]["expected_test_count"]
        result_pattern = re.compile(
            rf"test result: ok\. {expected_count} passed; 0 failed; "
            r"0 ignored; 0 measured; 0 filtered out"
        )
        if result_pattern.search(run.stdout) is None:
            raise ValidationError(
                "queue fixture did not report the exact contracted test count"
            )
    return {
        "compiler": str(compiler),
        "compiler_version": version,
        "fixture_status": "EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED",
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--rustc",
        help="exact rustc executable; otherwise use IHK_NATIVE_QUEUE_RUSTC",
    )
    parser.add_argument(
        "--require-rustc",
        action="store_true",
        help="fail instead of reporting SKIPPED_NO_CONFIGURED_RUSTC",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_repository(args.repo, args.contract)
        fixture = validate_configured_fixture(
            args.repo,
            args.contract,
            rustc=args.rustc,
            require_rustc=args.require_rustc,
        )
        summary.update(fixture)
    except ValidationError as error:
        print(f"ihk-native-queue-check: FAIL: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(
            "ihk-native-queue-check: SOURCE-CONTRACT-VERIFIED "
            f"fixture={summary['fixture_status']} "
            "ihk_crate_build=NOT_EVALUATED rocky_runtime=NOT_PROVEN "
            "teardown=NOT_PROVEN gate_credit=FORBIDDEN"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
