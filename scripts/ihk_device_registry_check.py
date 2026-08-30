#!/usr/bin/env python3
"""Validate the noncrediting native IHK device-registry foundation.

The checker binds the allocation-free Rust state machine and its standalone
fixture to the exact legacy registration/open/release/unregister oracle.  It
also verifies the bounded production integration: the crate root owns one
const registry and exposes only versioned scalar SMP lifecycle and open-receipt
ABIs, while the ioctl contract still rejects valid operations.  Source
agreement here cannot prove Linux device-node reachability, provider operation
callbacks, exact Kbuild, or runtime behavior.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys


IHK_REF = "3114d9e7101ad52030eb3effa849a5c108972a1f"
RUST_PATH = "host-kernel/native-rust/device_registry.rs"
FIXTURE_PATH = "scripts/tests/fixtures/ihk_device_registry_compile.rs"
CRATE_ROOT_PATH = "host-kernel/native-rust/ihk.rs"
IOCTL_CONTRACT_PATH = "host-kernel/contracts/ihk-ioctl-dispatch-foundation-v1.json"
CONTRACT_PATH = "host-kernel/contracts/ihk-device-registry-foundation-v1.json"
PROVIDER_ATTACH_SYMBOL = "ihk_smp_provider_attach_v2"
PROVIDER_DETACH_SYMBOL = "ihk_smp_provider_detach_v2"
PROVIDER_OPEN_SYMBOL = "ihk_smp_provider_open_v1"
PROVIDER_CLOSE_SYMBOL = "ihk_smp_provider_close_v1"
PROVIDER_COMPATIBILITY_EXPORTS = (
    "ihk_smp_provider_attach_v1",
    "ihk_smp_provider_detach_v1",
)
REFERENCE_INVENTORY_PATH = "host-kernel/reference/legacy-host-modules-f2eb7352.json"
REFERENCE_INVENTORY_SIZE = 246393
REFERENCE_INVENTORY_SHA256 = (
    "8da72c25cb50e1c92ceaceb0e93afa1cc7a72f80e8cd0095eeedb62004bad02d"
)
REFERENCE_PARENT = "f2eb735212e6ab0494e638497e80d9ae78b2848e"

SOURCE_LOCKS = (
    (
        "host_driver",
        "linux/core/host_driver.c",
        69863,
        "be75185f5b1a0aea84b0be995f67405e45964999b6ed28ae60adb3ed1dece722",
    ),
    (
        "public_header",
        "linux/include/ihk/ihk_host_driver.h",
        31132,
        "924c4a99f25d9fe832146ee21dd1f0b64b7cbf5d350c59f7f075dbc934a50d85",
    ),
    (
        "linux_private_header",
        "linux/core/host_linux.h",
        4475,
        "149218baad1027fd460fac6ec1e9430a7ede8d43be6640a296ce9c07afef7525",
    ),
    (
        "smp_provider",
        "linux/driver/smp/smp-driver.c",
        138442,
        "90fefdcb66ecd49cff6d43d2f5b8c13ce28010be2bde8043400cb2baebfa2544",
    ),
)

IN_FILE_TESTS = (
    "exact_capacity_first_fit_generation_reuse_and_stale_rejection",
    "dropping_reservation_aborts_and_consumes_generation",
    "explicit_reservation_abort_restores_slot",
    "publication_preserves_sharing_policy",
    "shareable_provider_references_are_counted_and_released",
    "exclusive_provider_allows_only_one_open",
    "os_references_drain_while_unpublishing",
    "provider_reference_overflow_fails_without_field_carry",
    "os_reference_overflow_fails_without_generation_carry",
    "dropping_unregister_guard_restores_live_state",
    "explicit_unregister_rollback_reopens_provider",
    "premature_unregister_commit_fails_and_rolls_back",
    "unregister_commit_vacates_and_reuse_stales_old_handle",
    "foreign_registry_handle_is_always_stale",
    "registry_identity_exhaustion_is_nonwrapping",
    "generation_exhaustion_retires_without_wrapping",
    "one_retired_minor_does_not_hide_an_available_slot",
    "malformed_packed_words_fail_closed_as_corrupt",
    "lease_drop_does_not_rewrite_corrupt_slot_words",
    "open_before_unregister_excludes_unregister",
    "unregister_before_open_excludes_new_references",
    "concurrent_publications_claim_unique_slots",
    "production_registry_token_round_trip_is_positive_and_exact",
    "provider_open_tokens_count_shared_files_and_release_once_each",
    "owned_open_token_release_fails_stop_on_unbalanced_receipt",
    "provider_token_header_version_and_generation_fail_closed",
    "provider_token_is_stale_after_unregister_and_slot_reuse",
    "dynamic_registry_cannot_issue_or_accept_production_tokens",
    "concurrent_provider_attaches_publish_exactly_one_minor_zero_lease",
    "concurrent_duplicate_detach_has_one_winner_and_no_live_slot",
    "errno_mapping_and_minor_bounds_fail_closed",
)

FIXTURE_TESTS = (
    "success_path_publishes_counts_and_unregisters",
    "failed_external_publication_aborts_without_reusing_handle",
    "registry_state_rollback_restores_live_before_external_commit",
    "deterministic_open_first_interleaving_blocks_unregister",
    "deterministic_unregister_first_interleaving_blocks_references",
    "simultaneous_publishers_get_unique_generation_tagged_slots",
    "production_token_adapter_round_trips_and_detaches",
    "malformed_and_replayed_production_tokens_fail_closed",
)

ERRNO_MAP = {
    "Busy": -16,
    "Capacity": -12,
    "Corrupt": -117,
    "GenerationExhausted": -75,
    "InvalidMinor": -22,
    "InvalidToken": -22,
    "NotFound": -2,
    "OsReferenceOverflow": -75,
    "ProviderReferenceOverflow": -75,
    "RegistryIdentityExhausted": -75,
    "StaleHandle": -116,
}

READINESS_BLOCKERS = (
    "the scalar lifecycle/open-receipt boundary does not by itself prove the SMP miscdevice registration, module-owner pinning, or userspace reachability",
    "the source-only mcd0 adapter still requires independent SMP-contract, exact-Kbuild, and hosted-runtime validation",
    "provider operation payload, create/destroy/resource callback lifetime, and external teardown ownership remain unmodeled; every ioctl is intentionally invalid",
    "the lifecycle callback lease proves one retained exit identity but not general callback module-owner pinning or in-flight operation drainage",
    "DeviceOsLease is not coupled to canonical os_registry create/destroy ownership",
    "legacy-stable first-fit and full-table results require an audited outer serialization adapter",
    "the nullable legacy registration return and callback errno surface have no audited Rust ABI bridge",
    "exact Rocky Linux 6.12 rustc dep-info, Kbuild, modpost, load/unload, and runtime concurrency evidence is absent",
)

INTENTIONAL_DELTAS = (
    "generation-tagged handles and a nonwrapping registry identity reject recycled-minor and cross-registry ABA",
    "failed reservations consume a generation and permanently retire a slot before generation wrap",
    "provider-open and child-OS ownership use separate bounded 16-bit counters with fail-closed overflow",
    "publishing, live, and unpublishing phases make reservation and unregister rollback explicit",
    "new opens and OS attachments are rejected after unpublishing linearizes while existing OS leases may drain",
    "concurrent lock-free reserve scans are observational until a Linux adapter supplies legacy-stable outer serialization",
    "typed internal errors are richer than the legacy nullable registration handle and require a later ABI adapter",
    "a magic/version/generation-tagged positive scalar token rejects malformed, cross-registry, and recycled-minor leases",
    "scalar open receipts transfer only counted ownership; identical shared-provider tokens require one count-balanced non-Copy owner per successful trusted call",
    "malformed, stale, and zero-reference owned-open releases fail stop, while same-generation duplicate closes are not individually detectable with shared tokens",
)


class ContractError(Exception):
    """Raised when the device-registry source contract drifts or overclaims."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _object_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _read(repo_root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ContractError("invalid repository path: {0!r}".format(relative))
    parts = relative.split("/")
    if relative.startswith("/") or "." in parts or ".." in parts:
        raise ContractError("repository path escapes root: {0}".format(relative))
    root = os.path.realpath(repo_root)
    path = os.path.join(root, *parts)
    if os.path.islink(path) or not os.path.isfile(path):
        raise ContractError("repository input is not a regular file: {0}".format(relative))
    if os.path.commonpath((root, os.path.realpath(path))) != root:
        raise ContractError("repository input resolves outside root: {0}".format(relative))
    try:
        with open(path, "rb") as stream:
            return stream.read()
    except (OSError, IOError) as error:
        raise ContractError("cannot read {0}: {1}".format(relative, error))


def _load_json_bytes(data, label):
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_object_without_duplicates
        )
    except (UnicodeError, ValueError) as error:
        raise ContractError("cannot load {0}: {1}".format(label, error))
    if not isinstance(value, dict):
        raise ContractError("{0} must contain an object".format(label))
    return value


def _git_blob(repo_root, ref, path):
    ihk = os.path.join(repo_root, "ihk")
    if not os.path.isdir(ihk):
        raise ContractError("frozen IHK submodule is not initialized")
    process = subprocess.Popen(
        ["git", "show", ref + ":" + path],
        cwd=ihk,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, error = process.communicate()
    if process.returncode:
        raise ContractError(
            "cannot read frozen IHK blob {0}:{1}: {2}".format(
                ref, path, error.decode("utf-8", "replace").strip()
            )
        )
    return output


def load_legacy_sources(repo_root, overrides=None):
    result = {}
    overrides = overrides or {}
    for source_id, path, size, digest in SOURCE_LOCKS:
        data = overrides.get(source_id)
        if data is None:
            data = _git_blob(repo_root, IHK_REF, path)
        if len(data) != size or _sha(data) != digest:
            raise ContractError(
                "frozen legacy source lock mismatch: {0}".format(source_id)
            )
        result[source_id] = data
    return result


def _validate_reference_inventory(data):
    if len(data) != REFERENCE_INVENTORY_SIZE or _sha(data) != REFERENCE_INVENTORY_SHA256:
        raise ContractError("legacy reference inventory lock mismatch")
    inventory = _load_json_bytes(data, "legacy reference inventory")
    provenance = inventory.get("provenance", {})
    if provenance.get("parent_commit") != REFERENCE_PARENT:
        raise ContractError("legacy reference inventory parent differs")
    if provenance.get("ihk_commit") != IHK_REF:
        raise ContractError("legacy reference inventory IHK ref differs")
    if provenance.get("build_target") != "smp-x86":
        raise ContractError("legacy reference inventory target differs")
    modules = inventory.get("source_capture", {}).get("modules", {})
    expected = (
        (
            "ihk",
            "ihk/linux/core/host_driver.c",
            69863,
            SOURCE_LOCKS[0][3],
            "5233fd512b3c912fec731fff7e150380900a99d7f302b47d21242afd4a0f7c97",
        ),
        (
            "ihk_smp_x86_64",
            "ihk/linux/driver/smp/smp-driver.c",
            138442,
            SOURCE_LOCKS[3][3],
            "c7bbe3a3cf06349e2e4324051c129a05fbb36adf2c6cc77c335d4a6713d675b8",
        ),
    )
    for module_id, path, size, base_digest, effective_digest in expected:
        inputs = modules.get(module_id, {}).get("active_inputs", [])
        matches = [item for item in inputs if item.get("source") == path]
        if len(matches) != 1:
            raise ContractError("legacy reference inventory lacks {0}".format(path))
        item = matches[0]
        if (
            item.get("bytes") != size
            or item.get("base_sha256") != base_digest
            or item.get("effective_input_sha256") != effective_digest
        ):
            raise ContractError("legacy reference inventory source lock differs: {0}".format(path))
    return inventory


def _text(data, label):
    try:
        return data.decode("utf-8")
    except UnicodeError as error:
        raise ContractError("{0} is not UTF-8: {1}".format(label, error))


def _without_comments(value):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", value, flags=re.DOTALL)


def _rust_code_view(value, label):
    """Return Rust code with comments and literals replaced by whitespace.

    The returned string has the same length and newline positions as the
    input.  That makes token-oriented regular expressions safe to use without
    letting a comment marker inside a string hide following code.  Rust block
    comments are nested, raw strings use an arbitrary hash delimiter, and a
    character literal is recognized only when its closing quote is locally
    unambiguous (so lifetimes remain code).
    """

    result = list(value)
    length = len(value)

    def blank(start, end):
        for position in range(start, end):
            if value[position] not in "\r\n":
                result[position] = " "

    def raw_hashes(quote):
        position = quote - 1
        hashes = 0
        while position >= 0 and value[position] == "#":
            hashes += 1
            position -= 1
        if position < 0 or value[position] != "r":
            return None
        prefix = position
        if prefix > 0 and value[prefix - 1] in "bc":
            prefix -= 1
        if prefix > 0 and (value[prefix - 1].isalnum() or value[prefix - 1] == "_"):
            return None
        return hashes

    def character_end(start):
        if start + 2 >= length or value[start] != "'":
            return None
        if value[start + 1] in "\r\n'":
            return None
        if value[start + 1] != "\\":
            return start + 3 if value[start + 2] == "'" else None
        position = start + 2
        while position < length and value[position] not in "\r\n":
            if value[position] == "'":
                return position + 1
            if value[position] == "\\":
                position += 1
            position += 1
        return None

    index = 0
    while index < length:
        if value.startswith("//", index):
            end = value.find("\n", index + 2)
            if end < 0:
                end = length
            blank(index, end)
            index = end
            continue
        if value.startswith("/*", index):
            depth = 1
            position = index + 2
            while position < length and depth:
                if value.startswith("/*", position):
                    depth += 1
                    position += 2
                elif value.startswith("*/", position):
                    depth -= 1
                    position += 2
                else:
                    position += 1
            if depth:
                raise ContractError("{0} has an unterminated block comment".format(label))
            blank(index, position)
            index = position
            continue
        if value[index] == '"':
            hashes = raw_hashes(index)
            if hashes is not None:
                terminator = '"' + ("#" * hashes)
                end = value.find(terminator, index + 1)
                if end < 0:
                    raise ContractError(
                        "{0} has an unterminated raw string".format(label)
                    )
                end += len(terminator)
            else:
                position = index + 1
                while position < length:
                    if value[position] == "\\":
                        position += 2
                        continue
                    if value[position] == '"':
                        position += 1
                        break
                    position += 1
                else:
                    raise ContractError(
                        "{0} has an unterminated string".format(label)
                    )
                end = position
            blank(index, end)
            index = end
            continue
        if value[index] == "'":
            end = character_end(index)
            if end is not None:
                blank(index, end)
                index = end
                continue
        index += 1
    return "".join(result)


def _require_pattern(text, pattern, label):
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        raise ContractError("missing locked behavior: {0}".format(label))


def _require_order(text, fragments, label):
    position = -1
    for fragment in fragments:
        position = text.find(fragment, position + 1)
        if position < 0:
            raise ContractError(
                "{0} lacks ordered fragment: {1}".format(label, fragment)
            )


def _active_fragment_positions(source, code, fragment, label):
    """Return exact fragment occurrences whose Rust syntax is active code."""

    fragment_code = _rust_code_view(fragment, label + " fragment")
    positions = []
    search_from = 0
    while True:
        position = source.find(fragment, search_from)
        if position < 0:
            return positions
        end = position + len(fragment)
        if code[position:end] == fragment_code:
            positions.append(position)
        search_from = position + 1


def _require_active_count(source, code, fragment, expected, label):
    actual = len(_active_fragment_positions(source, code, fragment, label))
    if actual != expected:
        raise ContractError(
            "{0} active occurrence count differs for {1}: expected {2}, got {3}".format(
                label, fragment, expected, actual
            )
        )


def _function_body(source, signature, label):
    start = source.find(signature)
    if start < 0:
        raise ContractError("source lacks {0}".format(label))
    opening = source.find("{", start + len(signature))
    if opening < 0:
        raise ContractError("{0} lacks an opening brace".format(label))
    depth = 0
    for position in range(opening, len(source)):
        character = source[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : position]
    raise ContractError("{0} lacks a closing brace".format(label))


def _validate_native_transactions(production):
    # Every structural transaction check below operates on active Rust syntax.
    # Keeping byte offsets/newlines stable prevents braces and required text in
    # comments or literals from changing function extraction or satisfying an
    # authority fragment.
    production = _rust_code_view(production, "device registry production source")
    slot_by_handle = _function_body(
        production, "fn slot_by_handle(", "DeviceRegistry::slot_by_handle"
    )
    _require_order(
        slot_by_handle,
        (
            "handle.registry_id != self.registry_id || handle.generation == 0",
            "return Err(DeviceRegistryError::StaleHandle);",
            "self.slot_by_minor(handle.minor())",
        ),
        "native foreign-registry handle rejection",
    )

    active_word = _function_body(
        production, "fn active_word(", "DeviceRegistry::active_word"
    )
    _require_order(
        active_word,
        (
            "validate_slot_word(current)?;",
            "generation(current) != handle.generation",
            "return Err(DeviceRegistryError::StaleHandle);",
            "PHASE_PUBLISHING | PHASE_LIVE | PHASE_UNPUBLISHING => Ok(current)",
            "PHASE_VACANT | PHASE_RETIRED => Err(DeviceRegistryError::NotFound)",
        ),
        "native active-handle generation rejection",
    )

    checked_live = _function_body(
        production, "fn checked_live_word(", "checked_live_word"
    )
    _require_order(
        checked_live,
        (
            "validate_slot_word(current)?;",
            "generation(current) != handle.generation",
            "return Err(DeviceRegistryError::StaleHandle);",
            "PHASE_LIVE => Ok(current)",
            "PHASE_PUBLISHING | PHASE_UNPUBLISHING => Err(DeviceRegistryError::Busy)",
        ),
        "native live-handle generation rejection",
    )

    checked_unpublishing = _function_body(
        production, "fn checked_unpublishing_word(", "checked_unpublishing_word"
    )
    _require_order(
        checked_unpublishing,
        (
            "validate_slot_word(current)?;",
            "generation(current) != handle.generation",
            "return Err(DeviceRegistryError::StaleHandle);",
            "PHASE_UNPUBLISHING => Ok(current)",
            "PHASE_PUBLISHING | PHASE_LIVE => Err(DeviceRegistryError::Busy)",
        ),
        "native unpublishing-handle generation rejection",
    )

    reserve = _function_body(
        production, "pub(crate) fn reserve(", "DeviceRegistry::reserve"
    )
    _require_order(
        reserve,
        (
            "for minor in 0..DEVICE_CAPACITY {",
            "let current = slot.word.load(Ordering::Acquire);",
            "validate_slot_word(current)?;",
            "PHASE_VACANT => {",
            "let old_generation = generation(current);",
            "if old_generation == MAX_GENERATION {",
            "PHASE_RETIRED,",
            ".compare_exchange(",
            "current,",
            "retired,",
            "generation_exhausted = true;",
            "let next_generation = old_generation + 1;",
            "PHASE_PUBLISHING,",
            ".compare_exchange(",
            "current,",
            "publishing,",
            "return Ok(ReservationGuard {",
            "generation: next_generation,",
            "publishing,",
            "armed: true,",
        ),
        "native reserve generation/retirement/publication transaction",
    )
    _require_pattern(
        reserve,
        r"if generation_exhausted\s*\{\s*Err\(DeviceRegistryError::GenerationExhausted\)\s*\}\s*else\s*\{\s*Err\(DeviceRegistryError::Capacity\)",
        "native reserve terminal classification",
    )
    _require_pattern(
        reserve,
        r"compare_exchange\(\s*current,\s*retired,\s*Ordering::AcqRel,\s*Ordering::Acquire",
        "native generation-retirement CAS",
    )
    _require_pattern(
        reserve,
        r"compare_exchange\(\s*current,\s*publishing,\s*Ordering::AcqRel,\s*Ordering::Acquire",
        "native publishing reservation CAS",
    )

    resolve = _function_body(
        production, "pub(crate) fn resolve_minor(", "DeviceRegistry::resolve_minor"
    )
    _require_order(
        resolve,
        (
            "let slot = self.slot_by_minor(minor)?;",
            "validate_slot_word(current)?;",
            "PHASE_LIVE => Ok(DeviceHandle {",
            "PHASE_PUBLISHING | PHASE_UNPUBLISHING => Err(DeviceRegistryError::Busy)",
            "PHASE_VACANT | PHASE_RETIRED => Err(DeviceRegistryError::NotFound)",
        ),
        "native live-only minor resolution",
    )

    production_constructor = _function_body(
        production, "const fn production(", "DeviceRegistry::production"
    )
    _require_order(
        production_constructor,
        (
            "registry_id: PRODUCTION_DEVICE_REGISTRY_ID,",
            "slots: [const { Slot::new() }; DEVICE_CAPACITY],",
        ),
        "native const production registry",
    )

    encode_token = _function_body(
        production,
        "pub(crate) fn encode_provider_token(",
        "DeviceRegistry::encode_provider_token",
    )
    _require_order(
        encode_token,
        (
            "self.registry_id != PRODUCTION_DEVICE_REGISTRY_ID",
            "return Err(DeviceRegistryError::InvalidToken);",
            "let snapshot = self.snapshot(handle)?;",
            "snapshot.phase != ActiveDevicePhase::Live",
            "return Err(DeviceRegistryError::Busy);",
            "PROVIDER_TOKEN_HEADER << PROVIDER_TOKEN_HEADER_SHIFT",
            "handle.generation << PROVIDER_TOKEN_GENERATION_SHIFT",
            "handle.minor as u64",
            "token == 0 || token > i64::MAX as u64",
            "Ok(token as i64)",
        ),
        "native provider-token encoding",
    )

    decode_token = _function_body(
        production,
        "pub(crate) fn decode_provider_token(",
        "DeviceRegistry::decode_provider_token",
    )
    _require_order(
        decode_token,
        (
            "self.registry_id != PRODUCTION_DEVICE_REGISTRY_ID || token <= 0",
            "return Err(DeviceRegistryError::InvalidToken);",
            "raw >> PROVIDER_TOKEN_HEADER_SHIFT != PROVIDER_TOKEN_HEADER",
            "let minor = raw & PROVIDER_TOKEN_MINOR_MASK;",
            "PROVIDER_TOKEN_GENERATION_MASK;",
            "minor >= DEVICE_CAPACITY as u64 || handle_generation == 0",
            "registry_id: self.registry_id,",
            "generation: handle_generation,",
        ),
        "native provider-token decoding",
    )

    attach_token = _function_body(
        production,
        "pub(crate) fn attach_provider_token(",
        "DeviceRegistry::attach_provider_token",
    )
    _require_order(
        attach_token,
        (
            "let reservation = self.reserve(SharePolicy::Shared)?;",
            "let reserved = reservation.handle();",
            "reserved.minor() != 0",
            "reservation.abort()?;",
            "return Err(DeviceRegistryError::Busy);",
            "let handle = reservation.publish()?;",
            "match self.encode_provider_token(handle)",
            ".begin_unregister(handle)",
            ".and_then(|unregister| unregister.commit());",
            "Err(cleanup_error) => Err(cleanup_error),",
        ),
        "native minor-zero provider attach transaction",
    )

    detach_token = _function_body(
        production,
        "pub(crate) fn detach_provider_token(",
        "DeviceRegistry::detach_provider_token",
    )
    _require_order(
        detach_token,
        (
            "let handle = self.decode_provider_token(token)?;",
            "self.begin_unregister(handle)?.commit()?;",
            "Ok(handle)",
        ),
        "native exact-token provider detach transaction",
    )

    retire_owned = _function_body(
        production,
        "pub(crate) fn retire_owned_provider_token(",
        "DeviceRegistry::retire_owned_provider_token",
    )
    _require_order(
        retire_owned,
        (
            "match self.detach_provider_token(token)",
            "Ok(handle) => handle,",
            "Err(error) => panic!(",
            "error.errno(),",
        ),
        "native fail-stop owned-provider retirement",
    )

    acquire_open = _function_body(
        production, "pub(crate) fn acquire_open(", "DeviceRegistry::acquire_open"
    )
    _require_order(
        acquire_open,
        (
            "let current = checked_live_word(slot, handle)?;",
            "let references = provider_references(current);",
            "share_policy(current) == SharePolicy::Exclusive && references != 0",
            "return Err(DeviceRegistryError::Busy);",
            "if references == MAX_REFERENCES {",
            "return Err(DeviceRegistryError::ProviderReferenceOverflow);",
            "current + PROVIDER_REFERENCE_ONE,",
            "return Ok(OpenLease {",
            "handle,",
        ),
        "native provider-open sharing and overflow transaction",
    )

    acquire_open_token = _function_body(
        production,
        "pub(crate) fn acquire_open_token(",
        "DeviceRegistry::acquire_open_token",
    )
    _require_order(
        acquire_open_token,
        (
            "let handle = self.resolve_minor(minor)?;",
            "let lease = self.acquire_open(handle)?;",
            "match self.encode_provider_token(lease.handle())",
            "core::mem::forget(lease);",
            "Ok(token)",
            "Err(error) => Err(error),",
        ),
        "native scalar provider-open receipt transaction",
    )

    release_owned_open = _function_body(
        production,
        "pub(crate) fn release_owned_open_token(",
        "DeviceRegistry::release_owned_open_token",
    )
    _require_order(
        release_owned_open,
        (
            ".decode_provider_token(token)",
            ".and_then(|handle| self.release_open_checked(handle).map(|()| handle));",
            "Ok(handle) => handle,",
            "Err(error) => panic!(",
            "error.errno(),",
        ),
        "native fail-stop scalar provider-open receipt release",
    )

    acquire_os = _function_body(
        production, "pub(crate) fn acquire_os(", "DeviceRegistry::acquire_os"
    )
    _require_order(
        acquire_os,
        (
            "let current = checked_live_word(slot, handle)?;",
            "if os_references(current) == MAX_REFERENCES {",
            "return Err(DeviceRegistryError::OsReferenceOverflow);",
            "current + OS_REFERENCE_ONE,",
            "return Ok(DeviceOsLease {",
            "handle,",
        ),
        "native OS-reference overflow transaction",
    )

    begin_unregister = _function_body(
        production,
        "pub(crate) fn begin_unregister(",
        "DeviceRegistry::begin_unregister",
    )
    _require_order(
        begin_unregister,
        (
            "let current = checked_live_word(slot, handle)?;",
            "if provider_references(current) != 0 {",
            "return Err(DeviceRegistryError::Busy);",
            "let unpublishing = (current & !PHASE_MASK) | PHASE_UNPUBLISHING;",
            ".compare_exchange(",
            "current,",
            "unpublishing,",
            "return Ok(UnregisterGuard {",
            "armed: true,",
        ),
        "native unregister exclusion transaction",
    )

    release_open_checked = _function_body(
        production,
        "fn release_open_checked(",
        "DeviceRegistry::release_open_checked",
    )
    _require_order(
        release_open_checked,
        (
            "let current = checked_live_word(slot, handle)?;",
            "provider_references(current) == 0",
            "return Err(DeviceRegistryError::Corrupt);",
            "current - PROVIDER_REFERENCE_ONE,",
            "return Ok(());",
        ),
        "native checked provider-open lease release",
    )

    release_open = _function_body(
        production, "fn release_open(", "DeviceRegistry::release_open"
    )
    _require_order(
        release_open,
        ("let _ = self.release_open_checked(handle);",),
        "native infallible provider-open RAII release",
    )

    release_os = _function_body(
        production, "fn release_os(", "DeviceRegistry::release_os"
    )
    _require_order(
        release_os,
        (
            "validate_slot_word(current).is_err()",
            "generation(current) != handle.generation",
            "!matches!(phase(current), PHASE_LIVE | PHASE_UNPUBLISHING)",
            "os_references(current) == 0",
            "current - OS_REFERENCE_ONE,",
        ),
        "native OS lease release",
    )

    publish = _function_body(
        production, "pub(crate) fn publish(", "ReservationGuard::publish"
    )
    _require_order(
        publish,
        (
            "let live = (self.publishing & !PHASE_MASK) | PHASE_LIVE;",
            ".compare_exchange(",
            "self.publishing,",
            "live,",
            ".map_err(|_| DeviceRegistryError::Corrupt)?;",
            "self.armed = false;",
        ),
        "native reservation publish transaction",
    )

    abort_inner = _function_body(
        production, "fn abort_inner(", "ReservationGuard::abort_inner"
    )
    _require_order(
        abort_inner,
        (
            "let vacant = pack(",
            "PHASE_VACANT,",
            "SharePolicy::Exclusive,",
            "self.handle.generation,",
            ".compare_exchange(",
            "self.publishing,",
            "vacant,",
            ".map_err(|_| DeviceRegistryError::Corrupt)",
        ),
        "native reservation abort transaction",
    )

    commit = _function_body(
        production, "pub(crate) fn commit(", "UnregisterGuard::commit"
    )
    _require_order(
        commit,
        (
            "let current = checked_unpublishing_word(slot, self.handle)?;",
            "provider_references(current) != 0 || os_references(current) != 0",
            "return Err(DeviceRegistryError::Busy);",
            "let vacant = pack(",
            "PHASE_VACANT,",
            "SharePolicy::Exclusive,",
            "self.handle.generation,",
            ".compare_exchange(",
            "current,",
            "vacant,",
            "self.armed = false;",
        ),
        "native unregister commit transaction",
    )

    rollback_inner = _function_body(
        production, "fn rollback_inner(", "UnregisterGuard::rollback_inner"
    )
    _require_order(
        rollback_inner,
        (
            "let current = checked_unpublishing_word(slot, self.handle)?;",
            "let live = (current & !PHASE_MASK) | PHASE_LIVE;",
            ".compare_exchange(",
            "current,",
            "live,",
        ),
        "native unregister rollback transaction",
    )

    identity = _function_body(
        production, "fn next_registry_id_from(", "next_registry_id_from"
    )
    _require_order(
        identity,
        (
            ".checked_add(1)",
            ".ok_or(DeviceRegistryError::RegistryIdentityExhausted)?;",
            "if current == 0 {",
            "return Err(DeviceRegistryError::RegistryIdentityExhausted);",
            "compare_exchange_weak(",
            "Ok(_) => return Ok(current),",
        ),
        "native nonwrapping registry identity transaction",
    )

    slot_validation = _function_body(
        production, "fn validate_slot_word(", "validate_slot_word"
    )
    for pattern, label in (
        (
            r"PHASE_VACANT\s+if provider_references == 0\s+&& os_references == 0\s+&& share_policy\(word\) == SharePolicy::Exclusive",
            "vacant slot invariant",
        ),
        (
            r"PHASE_PUBLISHING\s+if generation != 0 && provider_references == 0 && os_references == 0",
            "publishing slot invariant",
        ),
        (
            r"PHASE_LIVE\s+if generation != 0\s+&& \(share_policy\(word\) == SharePolicy::Shared\s+\|\| provider_references <= 1\)",
            "live slot invariant",
        ),
        (
            r"PHASE_UNPUBLISHING if generation != 0 && provider_references == 0",
            "unpublishing slot invariant",
        ),
        (
            r"PHASE_RETIRED\s+if generation == MAX_GENERATION\s+&& provider_references == 0\s+&& os_references == 0\s+&& share_policy\(word\) == SharePolicy::Exclusive",
            "retired slot invariant",
        ),
    ):
        _require_pattern(slot_validation, pattern, label)

    errno = _function_body(
        production, "pub(crate) const fn errno(", "DeviceRegistryError::errno"
    )
    _require_order(
        errno,
        (
            "Self::NotFound => -ENOENT,",
            "Self::Capacity => -ENOMEM,",
            "Self::Busy => -EBUSY,",
            "Self::InvalidMinor | Self::InvalidToken => -EINVAL,",
            "Self::RegistryIdentityExhausted",
            "| Self::GenerationExhausted",
            "| Self::ProviderReferenceOverflow",
            "| Self::OsReferenceOverflow => -EOVERFLOW,",
            "Self::StaleHandle => -ESTALE,",
            "Self::Corrupt => -EUCLEAN,",
        ),
        "native errno bridge",
    )

    for guard, release in (
        ("ReservationGuard", "let _ = self.abort_inner();"),
        ("OpenLease", "self.registry.release_open(self.handle);"),
        ("DeviceOsLease", "self.registry.release_os(self.handle);"),
        ("UnregisterGuard", "let _ = self.rollback_inner();"),
    ):
        body = _function_body(production, "impl Drop for {0}".format(guard), guard + " Drop")
        if release not in body:
            raise ContractError("{0} lacks fail-closed lease cleanup".format(guard))


def _validate_legacy(sources):
    host = _without_comments(_text(sources["host_driver"], "host_driver"))
    public = _without_comments(_text(sources["public_header"], "public_header"))
    private = _without_comments(
        _text(sources["linux_private_header"], "linux_private_header")
    )
    smp = _without_comments(_text(sources["smp_provider"], "smp_provider"))

    for pattern, label in (
        (r"^#define\s+DEV_MAX_MINOR\s+64$", "64-entry device capacity"),
        (r"^#define\s+DEV_DATA_INVALID\s+\(\(void \*\)-1\)$", "publication sentinel"),
        (r"^static DEFINE_SPINLOCK\(dev_data_lock\);$", "device table spinlock"),
        (r"dev_data\[DEV_MAX_MINOR\]", "fixed device pointer table"),
        (r"^static int dev_max_minor = 0;$", "device high-water mark"),
        (r"^EXPORT_SYMBOL\(ihk_register_device\);$", "registration export"),
        (r"^EXPORT_SYMBOL\(ihk_unregister_device\);$", "unregister export"),
    ):
        _require_pattern(host, pattern, label)

    register = _function_body(
        host, "ihk_device_t ihk_register_device(", "ihk_register_device"
    )
    for pattern, label in (
        (r"spin_lock_irqsave\(&dev_data_lock, flags\)", "registration table lock"),
        (r"for \(i = 0; i < dev_max_minor; i\+\+\).*?if \(!dev_data\[i\]\).*?break", "first-free scan"),
        (r"dev_max_minor >= DEV_MAX_MINOR.*?return NULL", "capacity null return"),
        (r"dev_data\[i\] = DEV_DATA_INVALID", "exclusive publication reservation"),
        (r"data->flag = param->flag", "sharing flag payload"),
        (r"data->ops = param->ops", "callback table payload"),
        (r"data->priv = param->priv", "provider private payload"),
        (r"param->ops->init.*?dev_data\[minor\] = NULL.*?return NULL", "provider init failure slot clearing"),
        (r"minor \+ 1 == os_max_minor.*?os_max_minor--", "provider init failure wrong OS high-water mutation"),
        (r"cdev_init\(&data->cdev, &mcd_cdev_ops\)", "cdev initialization"),
        (r"data->cdev.owner = THIS_MODULE", "legacy cdev owner"),
        (r"if \(cdev_add\(&data->cdev, data->dev_num, 1\) < 0\) \{\s*dev_data\[minor\] = NULL;\s*return NULL;\s*\}", "cdev failure slot-only clearing"),
        (r"if \(IS_ERR\(device_create\(mcd_class.*?DEV_DEV_NAME \"%d\", minor\)\)\) \{\s*dev_data\[minor\] = NULL;\s*return NULL;\s*\}", "device-node failure slot-only clearing"),
    ):
        _require_pattern(register, pattern, label)
    _require_order(
        register,
        (
            "spin_lock_irqsave(&dev_data_lock, flags);",
            "for (i = 0; i < dev_max_minor; i++)",
            "dev_data[i] = DEV_DATA_INVALID;",
            "spin_unlock_irqrestore(&dev_data_lock, flags);",
            "data = kzalloc(sizeof(*data), GFP_KERNEL);",
            "cdev_add(&data->cdev, data->dev_num, 1)",
            "device_create(mcd_class",
            "dev_data[minor] = data;",
            "data->minor = minor;",
        ),
        "legacy reserve/setup/publish order",
    )

    opened = _function_body(
        host, "static int ihk_host_device_open(", "ihk_host_device_open"
    )
    for pattern, label in (
        (r"idx = inode->i_rdev - mcd_dev_num", "minor decoding"),
        (r"idx < 0 \|\| idx > dev_max_minor.*?return -EINVAL", "minor rejection"),
        (r"!data \|\| data == DEV_DATA_INVALID.*?return -EINVAL", "unpublished rejection"),
        (r"data->flag & IHK_DEVICE_FLAG_SHARABLE.*?atomic_inc\(&data->refcount\)", "shared open"),
        (r"atomic_cmpxchg\(&data->refcount, 0, 1\) != 0.*?return -EBUSY", "exclusive open"),
        (r"file->private_data = data", "open payload publication"),
        (r"data->ops->open.*?atomic_dec\(&data->refcount\).*?return ret", "open callback rollback"),
    ):
        _require_pattern(opened, pattern, label)

    released = _function_body(
        host, "static int ihk_host_device_release(", "ihk_host_device_release"
    )
    _require_order(
        released,
        (
            "data = file->private_data;",
            "data->ops->close",
            "atomic_dec(&data->refcount);",
        ),
        "legacy close-before-reference-release order",
    )

    destroy_os = _function_body(host, "static int __destroy_all_os(", "__destroy_all_os")
    for pattern, label in (
        (r"spin_lock_irqsave\(&os_data_lock, flags\)", "child OS table lock"),
        (r"os_data\[i\]->dev_data == data", "child OS provider coupling"),
        (r"os_data\[i\] = NULL.*?__ihk_device_destroy_os\(data, os\)", "child OS removal"),
        (r"r != 0.*?os_data\[i\] = os.*?return r", "child OS rollback"),
    ):
        _require_pattern(destroy_os, pattern, label)

    unregister = _function_body(
        host, "int ihk_unregister_device(", "ihk_unregister_device"
    )
    for pattern, label in (
        (r"atomic_read\(&data->refcount\) > 0.*?return -EBUSY", "open-reference exclusion"),
        (r"__destroy_all_os\(data\) != 0.*?return -EBUSY", "child OS exclusion"),
        (r"while \(!list_empty\(&ihk_kmsg_bufs\)\).*?delete_kmsg_buf", "stray kmsg cleanup"),
    ):
        _require_pattern(unregister, pattern, label)
    _require_order(
        unregister,
        (
            "atomic_read(&data->refcount)",
            "__destroy_all_os(data)",
            "cdev_del(&data->cdev);",
            "device_destroy(mcd_class, data->dev_num);",
            "data->ops->exit",
            "dev_data[data->minor] = NULL;",
            "kfree(data->name);",
            "kfree(data);",
        ),
        "legacy unregister order",
    )
    if "dev_data_lock" in unregister or "atomic_cmpxchg" in unregister:
        raise ContractError("legacy unregister unexpectedly gained exclusion")

    for pattern, label in (
        (r"^#define\s+IHK_DEVICE_FLAG_SHARABLE\s+1$", "public sharing flag"),
        (r"struct ihk_register_device_data\s*\{.*?char \*name;.*?struct ihk_device_ops \*ops;.*?void \*priv;.*?int flag;.*?\};", "provider registration payload"),
        (r"ihk_device_t ihk_register_device\(struct ihk_register_device_data \*\);", "registration declaration"),
        (r"int ihk_unregister_device\(ihk_device_t\);", "unregister declaration"),
    ):
        _require_pattern(public, pattern, label)

    _require_pattern(
        private,
        r"struct ihk_host_linux_device_data\s*\{.*?spinlock_t lock;.*?struct cdev cdev;.*?dev_t dev_num;.*?int flag;.*?int minor;.*?char \*name;.*?atomic_t refcount;.*?struct ihk_device_ops \*ops;.*?void \*priv;.*?\};",
        "legacy provider payload layout",
    )

    for pattern, label in (
        (r"^static struct ihk_device_ops smp_ihk_device_ops = \{", "separate SMP callback table"),
        (r"^static struct ihk_register_device_data builtin_dev_reg_data = \{.*?\.flag = IHK_DEVICE_FLAG_SHARABLE,.*?\.priv = &builtin_data,.*?\.ops = &smp_ihk_device_ops,.*?\};", "borrowed SMP provider payload"),
        (r"ihk_register_device\(&builtin_dev_reg_data\)", "SMP provider registration"),
        (r"static void __exit smp_module_exit\(void\).*?ihk_unregister_device\(builtin_data\.ihk_dev\);", "unchecked SMP provider unregister"),
    ):
        _require_pattern(smp, pattern, label)
    if "try_module_get" in host or "module_put" in host:
        raise ContractError("legacy core unexpectedly gained provider module pinning")


def _test_names(text):
    return tuple(re.findall(r"#\[test\]\s*fn\s+([A-Za-z0-9_]+)\s*\(", text))


def _validate_rust(data):
    rust = _text(data, "device registry Rust source")
    marker = "#[cfg(test)]\nmod tests {"
    if rust.count(marker) != 1:
        raise ContractError("device registry must contain one in-file test module")
    production = rust.split(marker, 1)[0]
    production_code = _rust_code_view(production, "device registry Rust source")
    for pattern, label in (
        (r"\bunsafe\b", "unsafe code"),
        (r"\bextern\b", "FFI or external linkage"),
        (r"\b(?:alloc|std|kernel)::", "non-core dependency"),
        (r"\b(?:Box|Vec|String|Arc|Rc)\b", "allocation"),
        (r"\binclude(?:_bytes)?\s*!\s*\(", "textual source inclusion"),
        (r"\b(?:global_asm|asm)\s*!\s*\(", "assembly escape hatch"),
    ):
        if re.search(pattern, production_code):
            raise ContractError(
                "device registry contains forbidden {0}".format(label)
            )

    required = (
        "use core::sync::atomic::{AtomicU64, Ordering};",
        "pub(crate) const DEVICE_CAPACITY: usize = 64;",
        "const PRODUCTION_DEVICE_REGISTRY_ID: u64 = 1;",
        "static NEXT_DEVICE_REGISTRY_ID: AtomicU64 = AtomicU64::new(2);",
        "const PROVIDER_TOKEN_VERSION: u64 = 1;",
        "const PROVIDER_TOKEN_MAGIC: u64 = 0x49_48_4b;",
        "const PROVIDER_TOKEN_HEADER_SHIFT: u32 = 34;",
        "slots: [Slot; DEVICE_CAPACITY]",
        "const PHASE_VACANT: u64 = 0;",
        "const PHASE_PUBLISHING: u64 = 1;",
        "const PHASE_LIVE: u64 = 2;",
        "const PHASE_UNPUBLISHING: u64 = 3;",
        "const PHASE_RETIRED: u64 = 4;",
        "const SHAREABLE_SHIFT: u32 = 3;",
        "const PROVIDER_REFERENCE_SHIFT: u32 = 4;",
        "const OS_REFERENCE_SHIFT: u32 = 20;",
        "const GENERATION_SHIFT: u32 = 36;",
        "const MAX_REFERENCES: u16 = u16::MAX;",
        "const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;",
        "const ENOENT: i32 = 2;",
        "const ENOMEM: i32 = 12;",
        "const EBUSY: i32 = 16;",
        "const EINVAL: i32 = 22;",
        "const EOVERFLOW: i32 = 75;",
        "const ESTALE: i32 = 116;",
        "const EUCLEAN: i32 = 117;",
        "for minor in 0..DEVICE_CAPACITY {",
        "old_generation == MAX_GENERATION",
        ".checked_add(1)",
        "handle.registry_id != self.registry_id",
        "generation(current) != handle.generation",
        "pub(crate) static IHK_DEVICE_REGISTRY: DeviceRegistry = DeviceRegistry::production();",
        "const fn production() -> Self",
        "pub(crate) fn encode_provider_token(",
        "pub(crate) fn decode_provider_token(",
        "pub(crate) fn attach_provider_token(",
        "pub(crate) fn detach_provider_token(",
        "pub(crate) fn retire_owned_provider_token(",
        "pub(crate) fn acquire_open_token(",
        "pub(crate) fn release_owned_open_token(",
        "fn release_open_checked(",
        "impl Drop for ReservationGuard",
        "impl Drop for OpenLease",
        "impl Drop for DeviceOsLease",
        "impl Drop for UnregisterGuard",
        "share_policy(current) == SharePolicy::Exclusive && references != 0",
        "references == MAX_REFERENCES",
        "os_references(current) == MAX_REFERENCES",
        "provider_references(current) != 0 || os_references(current) != 0",
        "PHASE_LIVE | PHASE_UNPUBLISHING",
    )
    for fragment in required:
        if fragment not in production_code:
            raise ContractError(
                "device registry lacks locked marker: {0}".format(fragment)
            )
    for fragment in (
        "pin the provider module behind every callback table",
        "compensate any",
    ):
        if fragment not in production:
            raise ContractError(
                "device registry lacks locked safety documentation: {0}".format(
                    fragment
                )
            )
    if production_code.count("compare_exchange(") < 10:
        raise ContractError("device registry lacks the reviewed atomic transition surface")
    if "wrapping_add" in production_code:
        raise ContractError("device registry permits reference or identity wrapping")
    _validate_native_transactions(production)
    if _test_names(rust) != IN_FILE_TESTS:
        raise ContractError("device registry in-file test closure differs")
    return production


def _validate_fixture(data):
    fixture = _text(data, "device registry standalone fixture")
    required = (
        "#![cfg_attr(not(test), no_std)]",
        "../../../host-kernel/native-rust/device_registry.rs",
        "Barrier::new(2)",
    )
    for fragment in required:
        if fragment not in fixture:
            raise ContractError(
                "device registry fixture lacks locked marker: {0}".format(fragment)
            )
    if _test_names(fixture) != FIXTURE_TESTS:
        raise ContractError("device registry fixture test closure differs")


def _validate_boundaries(crate_root_data, ioctl_contract_data):
    source = _text(crate_root_data, "IHK crate root")
    crate_root = _rust_code_view(source, "IHK crate root")
    declaration = "#[allow(dead_code)]\nmod device_registry;"
    _require_active_count(
        source, crate_root, declaration, 1, "IHK private device-registry edge"
    )
    if crate_root.count(_rust_code_view(declaration, "device-registry declaration")) != 1:
        raise ContractError("IHK crate root lacks the private device-registry edge")
    required = (
        "use self::device_registry::{IHK_DEVICE_REGISTRY, SharePolicy};",
        "IHK_DEVICE_REGISTRY.attach_provider_token()",
        "IHK_DEVICE_REGISTRY.retire_owned_provider_token(token)",
        "IHK_DEVICE_REGISTRY.reserve(SharePolicy::Shared)",
        ".decode_provider_token(token)",
        "IHK_DEVICE_REGISTRY.active_count()",
        "IHK_DEVICE_REGISTRY.acquire_open_token(minor as usize)",
        "IHK_DEVICE_REGISTRY.release_owned_open_token(receipt)",
    )
    for fragment in required:
        _require_active_count(
            source, crate_root, fragment, 1, "IHK provider-lease boundary"
        )
        if crate_root.count(_rust_code_view(fragment, "provider-lease fragment")) != 1:
            raise ContractError(
                "IHK crate root lacks exact provider-lease boundary: {0}".format(
                    fragment
                )
            )
    if crate_root.count("IHK_DEVICE_REGISTRY") != 12:
        raise ContractError("IHK crate root has an unreviewed production-registry use")
    if len(re.findall(r"\bdevice_registry\b", crate_root)) != 2:
        raise ContractError("IHK crate root has an unreviewed device-registry alias")
    for forbidden in (
        ".acquire_open(",
        ".acquire_os(",
        ".resolve_minor(",
        "miscdevice",
        "cdev",
        "file_operations",
    ):
        if forbidden in crate_root:
            raise ContractError(
                "IHK provider lease reaches forbidden adapter: {0}".format(forbidden)
            )

    attach_signature = _rust_code_view(
        'pub extern "C" fn {0}('.format(PROVIDER_ATTACH_SYMBOL),
        "IHK SMP provider attach signature",
    )
    attach = _function_body(
        crate_root,
        attach_signature,
        "IHK SMP provider attach export",
    )
    _require_order(
        attach,
        (
            "callback_abi != IHK_SMP_PROVIDER_CALLBACK_ABI_V1",
            "IHK_DEVICE_REGISTRY.reserve(SharePolicy::Shared)",
            "let init_status = provider_init_status(init());",
            "reservation.abort()",
            "compare_exchange(",
            "reservation.publish()",
            "IHK_DEVICE_REGISTRY.encode_provider_token(handle)",
            "pr_info!(",
            "token",
        ),
        "IHK callback-bound provider attach export",
    )
    _require_active_count(
        source,
        crate_root,
        'pr_info!("provider_lease=attach status=live minor=0 callback_abi=1\\n");',
        1,
        "IHK provider attach diagnostic",
    )
    detach_signature = _rust_code_view(
        'pub extern "C" fn {0}('.format(PROVIDER_DETACH_SYMBOL),
        "IHK SMP provider detach signature",
    )
    detach = _function_body(
        crate_root,
        detach_signature,
        "IHK SMP provider detach export",
    )
    _require_order(
        detach,
        (
            "IHK_SMP_PROVIDER_EXIT_V2.load(Ordering::Acquire)",
            "IHK_DEVICE_REGISTRY",
            ".decode_provider_token(token)",
            ".begin_unregister(handle)",
            "IHK_DEVICE_REGISTRY.snapshot(handle)",
            "exit();",
            "unregister.commit()",
            "compare_exchange(",
            "pr_info!(",
            "handle.minor(),",
            "handle.generation(),",
        ),
        "IHK callback-bound provider detach export",
    )
    _require_active_count(
        source,
        crate_root,
        '"provider_lease=detach status=vacant minor={} generation={} callback_abi=1\\n",',
        1,
        "IHK provider detach diagnostic",
    )

    open_signature = _rust_code_view(
        'pub extern "C" fn {0}('.format(PROVIDER_OPEN_SYMBOL),
        "IHK SMP provider open signature",
    )
    open_export = _function_body(
        crate_root,
        open_signature,
        "IHK SMP provider open export",
    )
    _require_order(
        open_export,
        (
            "IHK_DEVICE_REGISTRY.acquire_open_token(minor as usize)",
            "Ok(receipt) => receipt,",
            "return error.errno() as i64;",
            "receipt",
        ),
        "IHK scalar provider-open receipt export",
    )
    _require_active_count(
        source,
        crate_root,
        'pr_info!("provider_open=acquire status=live minor=0\\n");',
        1,
        "IHK provider-open acquire diagnostic",
    )

    close_signature = _rust_code_view(
        'pub extern "C" fn {0}('.format(PROVIDER_CLOSE_SYMBOL),
        "IHK SMP provider close signature",
    )
    close_export = _function_body(
        crate_root,
        close_signature,
        "IHK SMP provider close export",
    )
    _require_order(
        close_export,
        (
            "IHK_DEVICE_REGISTRY.release_owned_open_token(receipt)",
        ),
        "IHK fail-stop provider-open receipt release export",
    )
    _require_active_count(
        source,
        crate_root,
        'pr_info!("provider_open=release status=complete minor=0\\n");',
        1,
        "IHK provider-open release diagnostic",
    )
    for symbol in PROVIDER_COMPATIBILITY_EXPORTS + (
        PROVIDER_ATTACH_SYMBOL,
        PROVIDER_DETACH_SYMBOL,
        PROVIDER_OPEN_SYMBOL,
        PROVIDER_CLOSE_SYMBOL,
    ):
        required_export = (
            '#[export_name = "{0}"]'.format(symbol),
            '#[export_name = "__export_symbol_{0}"]'.format(symbol),
            "symbol: {0} as *const () as *const u8,".format(symbol),
        )
        for fragment in required_export:
            _require_active_count(
                source, crate_root, fragment, 1, "IHK provider lease export"
            )
    if len(
        _active_fragment_positions(
            source,
            crate_root,
            'pub extern "C" fn ',
            "IHK C-ABI export",
        )
    ) != 6:
        raise ContractError("IHK crate root contains an unreviewed C-ABI export")

    ioctl_contract = _load_json_bytes(ioctl_contract_data, "ioctl contract")
    implementation = ioctl_contract.get("implementation", {})
    if ioctl_contract.get("gate_id") != "IHK-005-ioctl-dispatch-foundation":
        raise ContractError("ioctl boundary contract identity differs")
    if implementation.get("registration_supported") is not False:
        raise ContractError("ioctl boundary overclaims device registration support")
    if implementation.get("user_copy_reachable") is not False:
        raise ContractError("ioctl boundary overclaims userspace reachability")


def derive_contract(
    repo_root,
    rust_override=None,
    fixture_override=None,
    legacy_overrides=None,
    crate_root_override=None,
    ioctl_contract_override=None,
    reference_inventory_override=None,
):
    sources = load_legacy_sources(repo_root, legacy_overrides)
    _validate_legacy(sources)
    rust = rust_override if rust_override is not None else _read(repo_root, RUST_PATH)
    fixture = (
        fixture_override
        if fixture_override is not None
        else _read(repo_root, FIXTURE_PATH)
    )
    crate_root = (
        crate_root_override
        if crate_root_override is not None
        else _read(repo_root, CRATE_ROOT_PATH)
    )
    ioctl_contract = (
        ioctl_contract_override
        if ioctl_contract_override is not None
        else _read(repo_root, IOCTL_CONTRACT_PATH)
    )
    reference_inventory = (
        reference_inventory_override
        if reference_inventory_override is not None
        else _read(repo_root, REFERENCE_INVENTORY_PATH)
    )
    _validate_rust(rust)
    _validate_fixture(fixture)
    _validate_boundaries(crate_root, ioctl_contract)
    inventory = _validate_reference_inventory(reference_inventory)

    return {
        "attachment_boundary": {
            "crate_root_path": CRATE_ROOT_PATH,
            "crate_root_sha256": _sha(crate_root),
            "crate_root_size": len(crate_root),
            "crate_root_constructs_registry_instance": True,
            "private_module_edge_validated": True,
            "production_registry_static": "IHK_DEVICE_REGISTRY",
            "provider_lease_exports": [
                PROVIDER_COMPATIBILITY_EXPORTS[0],
                PROVIDER_COMPATIBILITY_EXPORTS[1],
                PROVIDER_ATTACH_SYMBOL,
                PROVIDER_DETACH_SYMBOL,
                PROVIDER_OPEN_SYMBOL,
                PROVIDER_CLOSE_SYMBOL,
            ],
        },
        "behavior": {
            "capacity": 64,
            "generation_bits": 28,
            "generation_policy": "monotonic-per-minor-consume-on-abort-retire-before-wrap",
            "minor_policy": "first-reusable-scan; legacy-stable first-fit requires outer serialization",
            "open_policy": {
                "exclusive": "at-most-one-provider-open-lease",
                "shared": "bounded-multiple-provider-open-leases",
            },
            "phase_sequence": [
                "vacant",
                "publishing",
                "live",
                "unpublishing",
                "vacant-or-retired",
            ],
            "reference_bits": {"os": 16, "provider_open": 16},
            "slot_atomic_bits": 64,
            "unregister_policy": "exclude-new-leases-drain-os-refs-commit-or-rollback",
        },
        "errno_map": ERRNO_MAP,
        "evidence_policy": {
            "credit_eligible": False,
            "exact_kbuild_validated": False,
            "legacy_differential_validated": False,
            "linux_adapter_validated": False,
            "rocky_runtime_validated": False,
            "source_and_fixture_validated": True,
        },
        "fixture": {
            "edition": "2021",
            "expected_fixture_tests": len(FIXTURE_TESTS),
            "expected_in_file_tests": len(IN_FILE_TESTS),
            "expected_total_tests": len(FIXTURE_TESTS) + len(IN_FILE_TESTS),
            "fixture_test_names": list(FIXTURE_TESTS),
            "in_file_test_names": list(IN_FILE_TESTS),
            "minimum_rustc": "1.92.0",
            "no_std_library_mode": True,
            "path": FIXTURE_PATH,
            "sha256": _sha(fixture),
        },
        "foundation_status": "production-crate-owned-allocation-free-device-registry-lifecycle-and-open-receipt-boundary",
        "gate_id": "IHK-004-device-registry-foundation",
        "intentional_safety_deltas": list(INTENTIONAL_DELTAS),
        "ioctl_boundary": {
            "contract_path": IOCTL_CONTRACT_PATH,
            "contract_sha256": _sha(ioctl_contract),
            "contract_size": len(ioctl_contract),
            "registration_supported": False,
            "user_copy_reachable": False,
        },
        "legacy_oracle": {
            "capacity": 64,
            "entry_points": [
                "ihk_register_device",
                "ihk_unregister_device",
                "ihk_host_device_open",
                "ihk_host_device_release",
                "__destroy_all_os",
            ],
            "ihk_ref": IHK_REF,
            "known_legacy_hazards": [
                "registration failure clears reserved slots without the device-table lock",
                "provider init failure decrements os_max_minor instead of dev_max_minor",
                "cdev failure leaks provider-init effects, name, and device record",
                "device-node failure additionally leaves the added cdev behind",
                "kstrdup failure is unchecked and the node is visible before slot publication",
                "open reads the device table without locking and accepts idx equal to dev_max_minor",
                "shared open uses unchecked atomic_inc and can overflow",
                "unregister has no handle validation or exclusion against racing opens and OS creation",
                "child destruction is partial on failure and unregister maps every child error to EBUSY",
                "provider callbacks are borrowed across modules without a provider module pin",
            ],
            "open_reference_policy": "shareable-unchecked-atomic-inc-or-exclusive-cmpxchg-zero-to-one; callback failure decrements",
            "provider_payload": ["name", "ops", "priv", "flag"],
            "reference_inventory": {
                "active_input_set_sha256": inventory["source_capture"]["active_input_set_sha256"],
                "ihk_commit": IHK_REF,
                "parent_commit": REFERENCE_PARENT,
                "path": REFERENCE_INVENTORY_PATH,
                "sha256": REFERENCE_INVENTORY_SHA256,
                "size": REFERENCE_INVENTORY_SIZE,
            },
            "registration_return": "nullable-provider-handle",
            "reservation": "dev-data-invalid-sentinel-under-irqsave-spinlock",
            "sources": [
                {
                    "id": source_id,
                    "path": path,
                    "sha256": digest,
                    "size": size,
                }
                for source_id, path, size, digest in SOURCE_LOCKS
            ],
            "unregister_observations": [
                "unlocked positive-open-refcount check",
                "ascending force-destroy of provider child OS objects until first failure",
                "only the currently failing child is restored; earlier destruction is not rolled back",
                "slot clearing occurs after cdev, node, provider exit, and global kmsg teardown",
            ],
        },
        "production_source": {
            "allocation_free": True,
            "ffi_free": True,
            "minimum_compare_exchange_sites": 10,
            "path": RUST_PATH,
            "sha256": _sha(rust),
            "size": len(rust),
        },
        "provider_lease_boundary": {
            "attach_return": "positive-i64-token-or-negative-errno",
            "attach_symbol": PROVIDER_ATTACH_SYMBOL,
            "callback_abi": 1,
            "callback_payload_reachable": False,
            "compatibility_exports": list(PROVIDER_COMPATIBILITY_EXPORTS),
            "credit_eligible": False,
            "detach_return": "infallible-owned-token-retirement-or-fail-stop",
            "detach_symbol": PROVIDER_DETACH_SYMBOL,
            "device_node_reachable": False,
            "import_namespace": "MCKERNEL_IHK_V1",
            "lifecycle_callbacks": {
                "arguments": "none",
                "exit_before_vacate": True,
                "exit_identity_retained": True,
                "init_before_publish": True,
                "operation_callbacks_reachable": False,
                "raw_data_pointer": False,
                "unpublishing_guard_across_exit": True,
            },
            "minor": 0,
            "open_close": {
                "close_return": "void-or-fail-stop",
                "close_symbol": PROVIDER_CLOSE_SYMBOL,
                "concurrent_shared_receipts": True,
                "duplicate_close_detectable_while_other_references_exist": False,
                "open_return": "positive-generation-token-or-negative-errno",
                "open_symbol": PROVIDER_OPEN_SYMBOL,
                "raw_pointer": False,
                "source_validated": True,
                "trusted_noncopy_owner_balance_required": True,
            },
            "runtime_validated": False,
            "token": {
                "generation_bits": [6, 33],
                "magic": "IHK",
                "magic_bits": [39, 62],
                "minor_bits": [0, 5],
                "positive_i64": True,
                "version": 1,
                "version_bits": [34, 38],
            },
        },
        "readiness": {
            "blockers": list(READINESS_BLOCKERS),
            "credit_eligible": False,
            "status": "TODO",
        },
        "schema_version": 1,
    }


def render_contract(contract):
    return (
        json.dumps(
            contract,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def check(
    repo_root,
    rust_override=None,
    fixture_override=None,
    legacy_overrides=None,
    crate_root_override=None,
    ioctl_contract_override=None,
    reference_inventory_override=None,
    contract_override=None,
):
    expected = derive_contract(
        repo_root,
        rust_override=rust_override,
        fixture_override=fixture_override,
        legacy_overrides=legacy_overrides,
        crate_root_override=crate_root_override,
        ioctl_contract_override=ioctl_contract_override,
        reference_inventory_override=reference_inventory_override,
    )
    actual = (
        contract_override
        if contract_override is not None
        else _read(repo_root, CONTRACT_PATH)
    )
    _load_json_bytes(actual, "device registry contract")
    if actual != render_contract(expected):
        raise ContractError(
            "checked-in device registry contract differs from deterministic capture"
        )
    return expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    parser.add_argument("--print-contract", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        contract = (
            derive_contract(arguments.repo)
            if arguments.print_contract
            else check(arguments.repo)
        )
    except ContractError as error:
        print("IHK device registry contract: FAIL: {0}".format(error), file=sys.stderr)
        return 1
    if arguments.print_contract:
        sys.stdout.write(render_contract(contract).decode("utf-8"))
    else:
        print("IHK device registry contract: OK (TODO; no credit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
