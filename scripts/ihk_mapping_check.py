#!/usr/bin/env python3
"""Validate the bounded, unattached native Rust IHK mapping foundation.

This checker cannot grant IHK-007 or tracker credit.  It binds the frozen IHK
mapping sources, enforces allocation-free checked Rust semantics and the lack
of production attachment, and optionally runs the exact Rocky Rust 1.92
fixture plus its compile-fail ownership probe.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


DEFAULT_CONTRACT = Path(
    "host-kernel/native-rust/ihk-mapping-foundation-contract-v1.json"
)
EXPECTED_COMPILER = (
    "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
)
EXPECTED_GITLINK = "3114d9e7101ad52030eb3effa849a5c108972a1f"
EXPECTED_SOURCE = "host-kernel/native-rust/ihk_mapping.rs"
EXPECTED_CHECKER = "scripts/ihk_mapping_check.py"
EXPECTED_FIXTURE = "scripts/tests/fixtures/ihk_mapping_compile.rs"
EXPECTED_MUST_USE = (
    "scripts/tests/fixtures/ihk_mapping_must_use_compile_fail.rs"
)
EXPECTED_LEGACY_INPUTS = [
    (
        "ihk/linux/core/mm.c",
        "5e69019ddab24581ae1edb819b05a6c063ce3f4b5e5fc40ea0db7ffffb91b504",
        895,
        [
            "ihk_host_map_generic",
            "ihk_host_unmap_generic",
            "not implemented",
            "return NULL;",
            "return -ENOSYS;",
        ],
    ),
    (
        "ihk/linux/core/host_driver.c",
        "be75185f5b1a0aea84b0be995f67405e45964999b6ed28ae60adb3ed1dece722",
        69863,
        [
            "ihk_host_device_mmap",
            "vma->vm_pgoff << PAGE_SHIFT",
            "remap_pfn_range",
            "kzalloc(sizeof(*md), GFP_KERNEL)",
            "ihk_device_unmap_memory",
        ],
    ),
    (
        "ihk/linux/core/ops_wrappers.h",
        "cfd2acae5e82d22f1d51d781bacf527b555e3dddeda1f2ff757a8085f4ae117e",
        6114,
        [
            "IHK_DEV_OPS_BEGIN(unsigned long, map_memory",
            "IHK_DEV_OPS_BEGIN(int, unmap_memory",
            "IHK_DEV_OPS_BEGIN(void *, map_virtual",
            "IHK_DEV_OPS_BEGIN(int, unmap_virtual",
        ],
    ),
    (
        "ihk/linux/include/ihk/ihk_host_driver.h",
        "924c4a99f25d9fe832146ee21dd1f0b64b7cbf5d350c59f7f075dbc934a50d85",
        31132,
        [
            "#define IHK_MAP_FLAG_CACHE  0",
            "#define IHK_MAP_FLAG_NOCACHE  1",
            "void *(*map_virtual)",
            "int (*unmap_virtual)",
        ],
    ),
    (
        "ihk/linux/include/ihk/ihk_host_user.h",
        "2335260024075a08becbe74651162a950aee8bea603e9a451cb8bcae3aa0ef97",
        5704,
        [
            "IHK_DEVICE_CREATE_OS",
            "IHK_DEVICE_DEBUG_START",
            "struct ihk_mem_req",
            "PHYS_CHUNKS_DESC_SIZE",
        ],
    ),
    (
        "ihk/linux/driver/smp/smp-driver.c",
        "90fefdcb66ecd49cff6d43d2f5b8c13ce28010be2bde8043400cb2baebfa2544",
        138442,
        [
            "ihk_smp_map_virtual",
            "phys_to_virt",
            "ihk_smp_unmap_virtual",
            "smp_ihk_map_virtual",
        ],
    ),
    (
        "ihk/linux/driver/smp/arch/x86_64/smp-arch-driver.c",
        "6ec820741ce6e77e4f60ce4c6b6577ed215a42ecf1a7e30207390ed6d0cbb745",
        52592,
        [
            "smp_ihk_os_map_memory",
            "return remote_phys;",
            "smp_ihk_map_memory",
            "smp_ihk_unmap_memory",
        ],
    ),
]
EXPECTED_OBSERVATIONS = [
    "generic fixed-virtual-address map and unmap helpers are explicitly unimplemented and return NULL or -ENOSYS",
    "device mmap derives the remote physical byte address from vm_pgoff and PAGE_SHIFT, maps device memory, then calls remap_pfn_range",
    "legacy mmap performs unchecked shift/add range arithmetic and allocates VMA metadata after remap without a checked allocation or explicit remap-failure unmap in that function",
    "VMA close reference-counts private metadata and calls device unmap on the final close",
    "the frozen internal driver API assigns cache flag 0 and no-cache flag 1",
    "the frozen user header defines no dedicated mmap request structure; the device-file mmap offset and VMA describe the request",
    "the SMP device map is identity translation while virtual lookup accepts only ranges contained in a used memory chunk",
]
EXPECTED_TESTS = [
    "ihk_mapping::tests::mapped_translation_requires_nonzero_aligned_local_address",
    "ihk_mapping::tests::page_geometry_and_range_edges_are_checked",
    "ihk_mapping::tests::rollback_state_cannot_be_replayed",
    "tests::adapter_errno_range_and_local_mapping_are_checked",
    "tests::aligned_range_constructor_rejects_partial_pages",
    "tests::authorized_physical_window_is_end_exclusive",
    "tests::cache_policy_values_match_frozen_ihk_flags_only",
    "tests::error_classes_map_to_stable_negative_errno_values",
    "tests::kernel_mapping_descriptor_covers_pages_and_preserves_offset",
    "tests::kernel_mapping_descriptor_checks_the_full_page_padded_virtual_extent",
    "tests::live_mapping_close_is_terminal_without_failure_errno",
    "tests::metadata_failure_orders_user_then_device_rollback",
    "tests::page_offset_conversion_rejects_numeric_overflow",
    "tests::pre_mapping_failure_has_no_cleanup_and_preserves_errno",
    "tests::property_covering_range_is_aligned_minimal_and_contains_input",
    "tests::property_page_requests_round_trip_without_overlap_or_truncation",
    "tests::protection_policy_is_explicit_and_fail_closed",
    "tests::rejected_live_rollback_preserves_the_required_close_cleanup",
    "tests::remap_failure_releases_device_mapping_once",
    "tests::transaction_rejects_mapping_for_another_request",
    "tests::user_vma_alignment_length_and_order_fail_closed",
    "tests::valid_user_mmap_descriptor_preserves_exact_ranges",
]
EXPECTED_UNPROVEN = [
    "Linux 6.12.0-211.44.1.el10_2 VMA, remap_pfn_range, vm_flags, pgprot, pinning, refcount, fork, split, mremap, and close adapters",
    "attachment to ihk.rs, the authoritative Kbuild/staging surface, RS-011 unsafe ledger, lifecycle contracts, and validation workflows",
    "device-specific map_memory, unmap_memory, map_virtual, and unmap_virtual calls and exact cache-policy translation",
    "rollback execution after partial remap or metadata-allocation failure and exact VMA teardown ordering",
    "reserved-memory ownership lookup across multiple physical chunks and concurrent release exclusion",
    "successful exact Rocky kernel compile, modpost, module load/unload, user mmap runtime, negative-path fault injection, and differential legacy parity",
    "IHK-007 completion, PASS status, or tracker credit",
]


class ValidationError(RuntimeError):
    """Raised when the bounded source contract drifts or overclaims evidence."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValidationError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def require_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ValidationError(
            "{0} keys differ: actual={1}, expected={2}".format(
                label, actual, sorted(expected)
            )
        )
    return value


def require_exact(actual, expected, label):
    if actual != expected or type(actual) is not type(expected):
        raise ValidationError(
            "{0} differs: actual={1!r}, expected={2!r}".format(
                label, actual, expected
            )
        )


def repo_file(repo, relative, label):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError("{0} path is malformed".format(label))
    path = Path(relative)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValidationError("{0} path escapes the repository".format(label))
    candidate = repo.joinpath(*path.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValidationError("{0} is unavailable: {1}".format(label, error))
    try:
        resolved.relative_to(repo.resolve())
    except ValueError:
        raise ValidationError("{0} resolves outside the repository".format(label))
    if candidate.is_symlink() or not candidate.is_file() or resolved != candidate:
        raise ValidationError("{0} must be a canonical regular file".format(label))
    return candidate


def read_json(path, label):
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError("cannot read {0}: {1}".format(label, error))
    if not isinstance(value, dict):
        raise ValidationError("{0} must contain an object".format(label))
    return value


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError as error:
        raise ValidationError("cannot hash {0}: {1}".format(path, error))
    return size, digest.hexdigest()


def read_text(path, label):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValidationError("cannot read {0}: {1}".format(label, error))


def validate_gitlink(repo, legacy):
    require_exact(legacy["gitlink_path"], "ihk", "legacy gitlink path")
    require_exact(legacy["gitlink_commit"], EXPECTED_GITLINK, "legacy gitlink commit")
    completed = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--stage", "--", "ihk"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ValidationError(
            "cannot inspect frozen IHK gitlink: {0}".format(
                completed.stderr.decode("utf-8", errors="replace").strip()
            )
        )
    rows = completed.stdout.decode("ascii", errors="strict").splitlines()
    expected = "160000 {0} 0\tihk".format(EXPECTED_GITLINK)
    require_exact(rows, [expected], "frozen IHK gitlink index entry")


def validate_legacy(repo, legacy):
    require_keys(legacy, {"gitlink_commit", "gitlink_path", "inputs", "observations"}, "legacy oracle")
    validate_gitlink(repo, legacy)
    require_exact(legacy["observations"], EXPECTED_OBSERVATIONS, "legacy observations")
    inputs = legacy["inputs"]
    if not isinstance(inputs, list):
        raise ValidationError("legacy inputs must be a list")
    expected_rows = []
    for path, digest, size, markers in EXPECTED_LEGACY_INPUTS:
        expected_rows.append(
            {
                "path": path,
                "required_markers": markers,
                "sha256": digest,
                "size": size,
            }
        )
    require_exact(inputs, expected_rows, "frozen legacy input authority")
    for index, row in enumerate(inputs):
        path = repo_file(repo, row["path"], "legacy input {0}".format(index))
        actual_size, actual_digest = sha256_file(path)
        require_exact(actual_size, row["size"], "legacy input size")
        require_exact(actual_digest, row["sha256"], "legacy input digest")
        text = read_text(path, "legacy input")
        for marker in row["required_markers"]:
            if marker not in text:
                raise ValidationError(
                    "legacy input {0} lacks marker {1!r}".format(index, marker)
                )


def validate_unattached(repo, contract):
    require_exact(
        contract["attachment_status"],
        {
            "ihk_crate_mod_edge": False,
            "kernel_build_surface": False,
            "native_stage_manifest": False,
            "rs011_ledger": False,
            "validation_workflows": False,
        },
        "attachment status",
    )
    forbidden_surfaces = [
        "host-kernel/native-rust/ihk.rs",
        "host-kernel/kbuild/Kbuild.in",
        "host-kernel/kbuild/stage-manifest.json",
        "host-kernel/contracts/native-rust-unsafe-ffi-ledger-v1.json",
        ".github/workflows/native-rust-host-modules-exact-build.yml",
        ".github/workflows/rocky-kernel-source-evidence.yml",
    ]
    for relative in forbidden_surfaces:
        text = read_text(repo_file(repo, relative, "attachment surface"), "attachment surface")
        if "ihk_mapping" in text or EXPECTED_SOURCE in text:
            raise ValidationError(
                "unattached mapping foundation appears on production surface {0}".format(
                    relative
                )
            )


def validate_source(repo, source_binding):
    require_keys(source_binding, {"allocation_model", "path", "sha256", "size"}, "production source")
    require_exact(source_binding["path"], EXPECTED_SOURCE, "production source path")
    require_exact(
        source_binding["allocation_model"],
        "core-only fixed-capacity values; no heap or Linux API calls",
        "allocation model",
    )
    source_path = repo_file(repo, source_binding["path"], "production source")
    size, digest = sha256_file(source_path)
    require_exact(size, source_binding["size"], "production source size")
    require_exact(digest, source_binding["sha256"], "production source digest")
    text = read_text(source_path, "production source")
    require_exact(text.count("// SPDX-License-Identifier: GPL-2.0"), 1, "source license marker")
    for forbidden in (
        "unsafe",
        'extern "C"',
        "std::",
        "alloc::",
        "Vec<",
        "Box<",
        "Arc<",
        "Mutex<",
        "include!",
        "include_bytes!",
        "asm!(",
        "module!(",
        "wrapping_add",
        "wrapping_mul",
        "wrapping_sub",
        "saturating_add",
        "saturating_mul",
        "saturating_sub",
    ):
        if forbidden in text:
            raise ValidationError(
                "production mapping core contains forbidden construct {0!r}".format(
                    forbidden
                )
            )
    required_once = [
        "pub(crate) struct PageGeometry",
        "pub(crate) struct PhysicalRange",
        "pub(crate) struct AlignedPhysicalRange",
        "pub(crate) enum CachePolicy",
        "pub(crate) struct KernelMapDescriptor",
        "pub(crate) struct UserMmapRequest",
        "pub(crate) struct DeviceMapping",
        "pub(crate) enum CleanupStep",
        "pub(crate) struct RollbackPlan",
        "pub(crate) struct MmapTransaction",
        "pfn.checked_mul(self.size)",
        ".checked_add(length)",
        ".checked_sub(byte_offset)",
        "base.checked_add(mapped.length())",
        ".checked_sub(user_start)",
        "if !allowed_window.contains(physical.range())",
        "0 => Ok(Self::Cached)",
        "1 => Ok(Self::Uncached)",
        "RollbackPlan::user_then_device(errno, self.request, mapping.local())",
        "Ok(RollbackPlan::close(mapping.local()))",
        "let next = self.steps[0].take();",
        "self.steps[0] = self.steps[1].take();",
    ]
    for marker in required_once:
        count = text.count(marker)
        if count != 1:
            raise ValidationError(
                "mapping invariant marker {0!r} must occur once, found {1}".format(
                    marker, count
                )
            )
    cleanup = (
        "steps: [\n"
        "                Some(CleanupStep::UnmapUser {\n"
        "                    user_start: request.user_start(),\n"
        "                    length: request.length(),\n"
        "                }),\n"
        "                Some(CleanupStep::UnmapDevice { local }),\n"
        "            ],"
    )
    if cleanup not in text:
        raise ValidationError("user-remap rollback cleanup order differs")
    if text.count("#[must_use") != 2:
        raise ValidationError("transaction and rollback ownership must both be must-use")
    return text


def validate_checker(repo, checker_binding):
    require_keys(checker_binding, {"path", "sha256", "size"}, "mapping checker")
    require_exact(checker_binding["path"], EXPECTED_CHECKER, "mapping checker path")
    checker_path = repo_file(repo, checker_binding["path"], "mapping checker")
    size, digest = sha256_file(checker_path)
    require_exact(size, checker_binding["size"], "mapping checker size")
    require_exact(digest, checker_binding["sha256"], "mapping checker digest")


def validate_contract(repo):
    contract_path = repo_file(repo, DEFAULT_CONTRACT.as_posix(), "mapping contract")
    contract = read_json(contract_path, "mapping contract")
    require_keys(
        contract,
        {
            "attachment_status",
            "checker",
            "compile_fixture",
            "evidence_policy",
            "foundation_status",
            "gate_id",
            "legacy_oracle",
            "must_use_probe",
            "production_source",
            "protocol",
            "schema_version",
            "unproven",
        },
        "mapping contract",
    )
    require_exact(contract["schema_version"], 1, "contract schema")
    require_exact(contract["gate_id"], "IHK-007", "contract gate")
    require_exact(
        contract["foundation_status"],
        "unattached-allocation-free-mapping-validation-core",
        "foundation status",
    )
    require_exact(
        contract["evidence_policy"],
        {
            "differential_legacy_parity_validated": False,
            "exact_kernel_compile_validated": False,
            "gate_credit_eligible": False,
            "linux_adapter_validated": False,
            "rocky_runtime_validated": False,
            "unmap_cleanup_validated": False,
            "user_mmap_runtime_validated": False,
        },
        "credit-forbidden evidence policy",
    )
    require_exact(contract["unproven"], EXPECTED_UNPROVEN, "unproven blockers")
    require_exact(
        contract["protocol"],
        {
            "address_width_bits": 64,
            "cache_flags": {"cached": 0, "uncached": 1},
            "cleanup_consumption": "each fixed-capacity cleanup step is removed when read so one plan cannot replay it",
            "cleanup_order_after_user_remap": ["unmap-user", "unmap-device"],
            "desired_virtual_extent": "page-aligned virtual base plus full page-covered mapped length uses checked addition",
            "errno_policy": "validation errors use deterministic negative Linux errno values; valid adapter errno in -4095..=-1 is preserved",
            "page_shift_range": [12, 63],
            "physical_ranges": "non-empty checked half-open u64 byte ranges",
            "protection_policy": "supplied explicitly by the future adapter; the core does not infer Linux VMA permissions",
            "user_offset": "page offset multiplied by the exact adapter-supplied base page size with checked arithmetic",
        },
        "mapping protocol",
    )
    validate_legacy(repo, contract["legacy_oracle"])
    validate_checker(repo, contract["checker"])
    validate_source(repo, contract["production_source"])
    validate_unattached(repo, contract)
    fixture = contract["compile_fixture"]
    require_keys(
        fixture,
        {
            "compile_arguments",
            "compiler_environment",
            "compiler_version_first_line",
            "expected_test_count",
            "path",
            "sha256",
            "test_names",
        },
        "compile fixture",
    )
    require_exact(fixture["path"], EXPECTED_FIXTURE, "compile fixture path")
    require_exact(
        fixture["compile_arguments"],
        ["--edition=2021", "--test", "-Dwarnings", "-C", "overflow-checks=yes"],
        "compile fixture arguments",
    )
    require_exact(fixture["compiler_environment"], "IHK_MAPPING_RUSTC", "compiler environment")
    require_exact(fixture["compiler_version_first_line"], EXPECTED_COMPILER, "compiler identity")
    require_exact(fixture["expected_test_count"], 22, "fixture test count")
    require_exact(fixture["test_names"], EXPECTED_TESTS, "fixture test inventory")
    fixture_path = repo_file(repo, fixture["path"], "compile fixture")
    unused_size, digest = sha256_file(fixture_path)
    del unused_size
    require_exact(digest, fixture["sha256"], "compile fixture digest")
    fixture_text = read_text(fixture_path, "compile fixture")
    for name in EXPECTED_TESTS[3:]:
        marker = "fn {0}()".format(name.split("::")[-1])
        if fixture_text.count(marker) != 1:
            raise ValidationError("fixture lacks exact test marker {0}".format(marker))
    for property_marker in ("for _ in 0..20_000", "for _ in 0..10_000"):
        if fixture_text.count(property_marker) != 1:
            raise ValidationError("fixture property coverage differs")
    probe = contract["must_use_probe"]
    require_keys(
        probe,
        {"compile_arguments", "diagnostic_fragments", "path", "sha256"},
        "must-use probe",
    )
    require_exact(probe["path"], EXPECTED_MUST_USE, "must-use probe path")
    require_exact(
        probe["compile_arguments"],
        ["--edition=2021", "-Dunused-must-use"],
        "must-use arguments",
    )
    require_exact(
        probe["diagnostic_fragments"],
        [
            "unused `MmapTransaction` that must be used",
            "mapping transactions must reach rollback, live, or close",
            "unused `RollbackPlan` that must be used",
            "mapping cleanup plans must be executed by the Linux adapter",
        ],
        "must-use diagnostics",
    )
    probe_path = repo_file(repo, probe["path"], "must-use probe")
    unused_size, probe_digest = sha256_file(probe_path)
    del unused_size
    require_exact(probe_digest, probe["sha256"], "must-use probe digest")
    return contract


def configured_rustc(explicit=None):
    requested = explicit if explicit is not None else os.environ.get("IHK_MAPPING_RUSTC", "")
    if not requested:
        return None
    path = Path(requested)
    if not path.is_absolute():
        raise ValidationError("configured rustc must be an absolute path")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValidationError("configured rustc is unavailable: {0}".format(error))
    if path.is_symlink() or not resolved.is_file() or not os.access(str(resolved), os.X_OK):
        raise ValidationError("configured rustc must be an executable regular file")
    return resolved


def run_command(command, label):
    completed = subprocess.run(
        [str(item) for item in command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise ValidationError(
            "{0} failed ({1}): {2}".format(
                label,
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace").strip(),
            )
        )
    return completed


def validate_configured_fixture(repo, rustc=None, require_rustc=False):
    contract = validate_contract(repo)
    compiler = configured_rustc(rustc)
    if compiler is None:
        if require_rustc:
            raise ValidationError("exact Rocky rustc is required but absent")
        return {"fixture_status": "SKIPPED_NO_CONFIGURED_RUSTC", "compiler_version": None}
    version = run_command([compiler, "--version"], "rustc version probe")
    if version.stderr:
        raise ValidationError("rustc version probe wrote stderr")
    lines = version.stdout.decode("utf-8", errors="strict").splitlines()
    require_exact(lines, [EXPECTED_COMPILER], "rustc version output")
    fixture = repo_file(repo, contract["compile_fixture"]["path"], "compile fixture")
    probe = repo_file(repo, contract["must_use_probe"]["path"], "must-use probe")
    with tempfile.TemporaryDirectory(prefix="ihk-mapping-rustc-") as temporary:
        binary = Path(temporary) / "ihk-mapping-tests"
        command = [compiler] + contract["compile_fixture"]["compile_arguments"] + [fixture, "-o", binary]
        run_command(command, "mapping fixture compilation")
        execution = run_command([binary, "--test-threads=1"], "mapping fixture execution")
        output = (execution.stdout + execution.stderr).decode("utf-8", errors="strict")
        summary = re.findall(
            r"test result: ok\. ([0-9]+) passed; 0 failed; 0 ignored; 0 measured; 0 filtered out",
            output,
        )
        require_exact(summary, [str(contract["compile_fixture"]["expected_test_count"])], "fixture result summary")
        for name in EXPECTED_TESTS:
            if "test {0} ... ok".format(name) not in output:
                raise ValidationError("fixture did not execute contracted test {0}".format(name))
        probe_binary = Path(temporary) / "must-use-probe"
        probe_command = [compiler] + contract["must_use_probe"]["compile_arguments"] + [probe, "-o", probe_binary]
        probe_run = subprocess.run(
            [str(item) for item in probe_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if probe_run.returncode == 0:
            raise ValidationError("must-use probe unexpectedly compiled")
        diagnostics = (probe_run.stdout + probe_run.stderr).decode(
            "utf-8", errors="replace"
        )
        for fragment in contract["must_use_probe"]["diagnostic_fragments"]:
            if fragment not in diagnostics:
                raise ValidationError(
                    "must-use probe lacks diagnostic {0!r}".format(fragment)
                )
    return {
        "fixture_status": "EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED",
        "compiler_version": EXPECTED_COMPILER,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--rustc")
    parser.add_argument("--require-rustc", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        result = validate_configured_fixture(
            repo, rustc=args.rustc, require_rustc=args.require_rustc
        )
    except ValidationError as error:
        print("IHK-007 mapping foundation error: {0}".format(error), file=sys.stderr)
        return 1
    print(
        "SOURCE-CONTRACT-VERIFIED fixture={0} attachment=ABSENT "
        "kernel_build=NOT_PROVEN runtime=NOT_PROVEN cleanup=NOT_PROVEN "
        "gate_credit=FORBIDDEN".format(result["fixture_status"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
