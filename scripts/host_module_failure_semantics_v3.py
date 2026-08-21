#!/usr/bin/env python3
"""Capture structural C value and Rust MIR evidence for FP-0006.

Schema v3 is deliberately non-crediting.  It binds the 205 C return-domain
questions and 420 Rust errno tokens left by the immutable v1/v2 artifacts to
compiler-produced evidence, but it does not turn numeric ranges into API error
semantics and it does not claim executable acceptance coverage.

Fresh mode can create a canonical raw tar from two deterministic compiler
replays.  Historical mode never runs a compiler: callers must supply a
separate tar and checksum sidecar whose manifest binds the exact archived HFS,
v1, and derived v2 bytes.
"""

import sys as _fp0006_entry_sys


if __name__ == "__main__" and not hasattr(
    _fp0006_entry_sys, "_mckernel_fp0006_authority_context"
):
    _fp0006_entry_sys.stderr.write(
        "host-module failure semantics v3 CLI requires the isolated "
        "failure-site authority launcher; refusing direct execution\n"
    )
    raise SystemExit(2)


import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict, deque
from pathlib import Path

import host_module_failure_flows as flows_v1
import host_module_failure_flows_v2 as flows_v2
import host_module_failure_sites as sites


SCHEMA_VERSION = 3
PROFILE = "compiler-backed-host-module-failure-semantics-v3"
RAW_SCHEMA_VERSION = 1
RAW_PROFILE = "compiler-backed-host-module-failure-semantics-raw-v3"
MAX_JSON_BYTES = 256 * 1024 * 1024
MAX_RAW_BUNDLE_BYTES = 768 * 1024 * 1024
MAX_RAW_MEMBER_BYTES = 256 * 1024 * 1024
MAX_RAW_MEMBERS = 20000
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
SAFE_MEMBER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")

# JSON deliberately has one numeric type, while Python's ``bool`` is an
# ``int`` subclass.  Every integer-bearing v3 field is therefore named here
# and checked with ``type(value) is int`` before any equality comparison.  The
# count-map entries need the same treatment even though their keys are module
# or disposition names rather than numeric field names.
INTEGER_FIELD_NAMES = frozenset(
    {
        "artifact_bytes", "basic_block", "bytes", "column", "end_column",
        "end_line", "errno_negative_value", "line", "matching_line_count",
        "number", "schema_version", "sha256_sidecar_bytes", "start_column",
        "start_line",
    }
)
COUNT_MAP_FIELD_NAMES = frozenset(
    {
        "c_return_contract_count_by_module",
        "c_return_contract_count_by_status",
        "rust_mir_site_count_by_mapping_status",
    }
)
BOOLEAN_FIELD_NAMES = frozenset(
    {
        "credit_eligible", "executable_acceptance_coverage", "exhaustive",
        "negative_numeric_values_are_not_semantic_errno_proof",
        "object_byte_equality", "reachable_from_bb0",
        "semantic_error_domains_proven", "test_mapped", "tracker_credit",
        "two_run_normalized_determinism",
    }
)

EXPECTED_C_ROW_COUNT = 205
EXPECTED_C_TERMINAL_COUNT = 208
EXPECTED_C_FUNCTION_COUNT = 166
EXPECTED_C_SOURCE_COUNT = 15
EXPECTED_C_ROWS_BY_MODULE = {
    "ihk": 33,
    "ihk_smp_x86_64": 17,
    "mcctrl": 155,
}
EXPECTED_RUST_SITE_COUNT = 420
EXPECTED_RUST = {
    "argv_sha256": "aee4212351d81c7c94c19f514272314058b56156e8d4166aa3bdb31770caafeb",
    "compiler_sha256": "70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09",
    "launcher_sha256": "4acc9acc76d5079515b46346a485974457b5a79893cfb01112423c89aeb5aa10",
    "source_sha256": "abc99c0e160d3a8aa1aa182f37f297cf3827f86faaac559117ae4df3197e9d14",
    "version_first_line": "rustc 1.95.0-nightly (c04308580 2026-02-18)",
}
C_DUMP_OPTIONS = (
    ("original", "-fdump-tree-original-lineno", ".original"),
    ("gimple", "-fdump-tree-gimple-lineno", ".gimple"),
    ("ssa", "-fdump-tree-ssa-lineno", ".ssa"),
    ("evrp", "-fdump-tree-evrp-lineno", ".evrp"),
    ("vrp", "-fdump-tree-vrp1-lineno", ".vrp1"),
)
RUST_MIR_OPTIONS = (
    "-Zdump-mir=all",
    "-Zdump-mir-exclude-pass-number",
)
RUST_SELECTED_STAGE_SUFFIXES = (
    ".built.after.mir",
    ".runtime-optimized.after.mir",
)

ANALYSIS_CLAIM = {
    "credit_eligible": False,
    "executable_acceptance_coverage": False,
    "exhaustive": False,
    "fp_0006_status": "IN_PROGRESS",
    "semantic_error_domains_proven": False,
    "test_mapped": False,
    "tracker_credit": False,
    "reason": (
        "v3 records structural GCC and Rust MIR evidence only; numeric ranges "
        "are not API error-domain proofs, MIR mappings are not executable "
        "acceptance results, and cross-boundary reachability remains open"
    ),
}

BLOCKERS = (
    "205_c_returns_require_semantic_oracle",
    "420_rust_sites_require_semantic_oracle_or_executable_acceptance",
    "acceptance_ids_are_declarations_not_executable_results",
    "cross_translation_unit_reachability_not_proven",
    "indirect_callback_reachability_not_proven",
    "macro_expansion_dataflow_not_proven",
    "module_api_reachability_not_proven",
    "full_compiler_statement_extents_not_a_semantic_contract",
    "2602_executable_acceptance_mappings_not_captured",
)


class SemanticsV3Error(RuntimeError):
    """Raised when raw or derived v3 authority is malformed."""


def canonical_bytes(value):
    return (
        json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def strict_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            strict_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            strict_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def require_exact_keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise SemanticsV3Error("{0} schema changed".format(label))
    return value


def require_string(value, label):
    if type(value) is not str or not value or "\0" in value:
        raise SemanticsV3Error("{0} must be a non-empty string".format(label))
    return value


def require_integer(value, label, minimum=None, maximum=None):
    if type(value) is not int:
        raise SemanticsV3Error("{0} must be an exact integer".format(label))
    if minimum is not None and value < minimum:
        raise SemanticsV3Error("{0} integer is below its minimum".format(label))
    if maximum is not None and value > maximum:
        raise SemanticsV3Error("{0} integer is above its maximum".format(label))
    return value


def require_exact_integer(value, expected, label):
    require_integer(value, label)
    if value != expected:
        raise SemanticsV3Error("{0} integer changed".format(label))
    return value


def require_boolean(value, label):
    if type(value) is not bool:
        raise SemanticsV3Error("{0} must be an exact boolean".format(label))
    return value


def require_enum(value, choices, label):
    require_string(value, label)
    if value not in choices:
        raise SemanticsV3Error("{0} enum changed".format(label))
    return value


def validate_type_strict_json(value, label, path=None):
    """Recursively reject JSON/Python scalar type confusion in v3 schemas."""

    path = list(path or ())
    value_type = type(value)
    location = label + ("." + ".".join(path) if path else "")
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str or not key:
                raise SemanticsV3Error(
                    "{0} has a non-string or empty object key".format(location)
                )
            child_location = location + "." + key
            if key in INTEGER_FIELD_NAMES or key.endswith("_count"):
                require_integer(item, child_location)
            if key in BOOLEAN_FIELD_NAMES:
                require_boolean(item, child_location)
            if key in COUNT_MAP_FIELD_NAMES:
                if type(item) is not dict:
                    raise SemanticsV3Error(
                        "{0} must be an exact count object".format(child_location)
                    )
                for count_key, count in item.items():
                    if type(count_key) is not str or not count_key:
                        raise SemanticsV3Error(
                            "{0} has an invalid count key".format(child_location)
                        )
                    require_integer(
                        count,
                        "{0}.{1}".format(child_location, count_key),
                        minimum=0,
                    )
            validate_type_strict_json(item, label, path + [key])
        return value
    if value_type is list:
        for index, item in enumerate(value):
            validate_type_strict_json(
                item, label, path + ["[{0}]".format(index)]
            )
        return value
    if value_type is float:
        raise SemanticsV3Error(
            "{0} contains a forbidden floating-point JSON number".format(location)
        )
    if value_type not in (str, int, bool, type(None)):
        raise SemanticsV3Error(
            "{0} contains a non-JSON scalar type".format(location)
        )
    return value


def validate_artifact_binding(binding, label):
    require_exact_keys(
        binding,
        {"artifact_bytes", "artifact_sha256", "profile", "schema_version"},
        label,
    )
    require_integer(binding["artifact_bytes"], label + " artifact bytes", minimum=1)
    require_digest(binding["artifact_sha256"], label + " artifact digest")
    require_string(binding["profile"], label + " profile")
    require_integer(binding["schema_version"], label + " schema version", minimum=1)
    return binding


def require_count_map(value, label, expected_keys=None):
    if type(value) is not dict:
        raise SemanticsV3Error("{0} must be an exact count object".format(label))
    if expected_keys is not None and set(value) != set(expected_keys):
        raise SemanticsV3Error("{0} count keys changed".format(label))
    for key, count in value.items():
        require_string(key, label + " key")
        require_integer(count, label + " " + key, minimum=0)
    return value


def validate_raw_bundle_record(record, label):
    require_exact_keys(
        record,
        {
            "artifact_bytes", "artifact_sha256", "manifest_sha256",
            "sha256_sidecar_bytes", "sha256_sidecar_sha256",
        },
        label,
    )
    require_integer(record["artifact_bytes"], label + " artifact bytes", minimum=1)
    require_integer(
        record["sha256_sidecar_bytes"], label + " sidecar bytes", minimum=1
    )
    for field in (
        "artifact_sha256", "manifest_sha256", "sha256_sidecar_sha256"
    ):
        require_digest(record[field], label + " " + field)
    return record


def require_digest(value, label):
    if not isinstance(value, str) or not HEX_DIGEST.fullmatch(value):
        raise SemanticsV3Error("{0} is not an exact SHA-256".format(label))
    return value


def require_safe_relative_path(value, label):
    require_string(value, label)
    if (
        len(value.encode("utf-8")) > 4096
        or value.startswith("/")
        or "\\" in value
        or ".." in Path(value).parts
        or any(ord(character) < 0x20 or ord(character) == 0x7f for character in value)
    ):
        raise SemanticsV3Error("{0} is not a safe relative path".format(label))
    return value


def duplicate_rejecting_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SemanticsV3Error("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def reject_nonfinite_constant(value):
    raise SemanticsV3Error("non-finite JSON constant is forbidden: {0}".format(value))


def read_regular_bytes(path, label, maximum):
    """Read one stable regular file through held no-follow descriptors."""

    return read_confined_object_bytes(path, label, maximum)


def decode_json(data, label):
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=duplicate_rejecting_object,
            parse_constant=reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, SemanticsV3Error):
            raise
        raise SemanticsV3Error("cannot parse {0}: {1}".format(label, exc))
    if not isinstance(value, dict):
        raise SemanticsV3Error("{0} must be a JSON object".format(label))
    return value


def read_json_record(path, label):
    data = read_regular_bytes(path, label, MAX_JSON_BYTES)
    return decode_json(data, label), {
        "artifact_bytes": len(data),
        "artifact_sha256": sha256_bytes(data),
    }, data


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, str(path))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def input_binding(value, record):
    return {
        "artifact_bytes": record["artifact_bytes"],
        "artifact_sha256": record["artifact_sha256"],
        "profile": value["profile"],
        "schema_version": value["schema_version"],
    }


def load_inputs(
    repo,
    failure_site_path,
    failure_flow_v1_path,
    failure_flow_v2_path,
    build_dir=None,
    kernel_dir=None,
    historical_ef58=False,
    repository_authority=None,
):
    hfs, hfs_file, hfs_data = read_json_record(failure_site_path, "failure sites v1")
    flow_v1, flow_v1_file, flow_v1_data = read_json_record(
        failure_flow_v1_path, "failure flows v1"
    )
    flow_v2, flow_v2_file, _ = read_json_record(
        failure_flow_v2_path, "failure flows v2"
    )
    for value, label in (
        (hfs, "failure sites v1"),
        (flow_v1, "failure flows v1"),
        (flow_v2, "failure flows v2"),
    ):
        validate_type_strict_json(value, label)
    try:
        with tempfile.TemporaryDirectory(prefix="host-module-semantics-v3-input.") as temp:
            root = Path(temp)
            hfs_snapshot = flows_v2.write_private_snapshot(root, "hfs.", hfs_data)
            v1_snapshot = flows_v2.write_private_snapshot(root, "v1.", flow_v1_data)
            expected_v2 = flows_v2.build_capture(
                repo,
                hfs_snapshot,
                v1_snapshot,
                build_dir,
                kernel_dir,
                historical_ef58,
                repository_authority,
            )
    except (OSError, flows_v2.FlowV2Error) as exc:
        raise SemanticsV3Error("cannot derive exact v2 input: {0}".format(exc))
    if not strict_equal(flow_v2, expected_v2):
        raise SemanticsV3Error("supplied v2 artifact is not the exact v1 derivation")
    if historical_ef58:
        if not strict_equal(hfs_file, flows_v2.EXPECTED_HFS_ARTIFACT):
            raise SemanticsV3Error("historical HFS bytes differ from ef58860e")
        if not strict_equal(flow_v1_file, flows_v2.EXPECTED_V1_FLOW_ARTIFACT):
            raise SemanticsV3Error("historical v1 bytes differ from ef58860e")

    sources = {record["source"]: record for record in hfs.get("sources", [])}
    if len(sources) != len(sites.EXPECTED_SOURCES):
        raise SemanticsV3Error("HFS source closure changed")
    rust_records = [record for record in sources.values() if record["language"] == "rust"]
    if len(rust_records) != 1:
        raise SemanticsV3Error("HFS Rust source closure changed")
    rust = rust_records[0]
    rust_digests = rust.get("digests", {})
    rust_compiler = rust.get("recorded_compiler", {})
    rust_launcher = rust_compiler.get("launcher", {})
    observed_rust = {
        "argv_sha256": rust_digests.get("recorded_compile_argv_sha256"),
        "compiler_sha256": rust_digests.get("compiler_sha256"),
        "launcher_sha256": rust_launcher.get("sha256"),
        "source_sha256": rust_digests.get("effective_source_sha256"),
        "version_first_line": rust_compiler.get("version_first_line"),
    }
    if not strict_equal(observed_rust, EXPECTED_RUST):
        raise SemanticsV3Error("pinned Rust compiler, argv, launcher, or source changed")
    return {
        "authority_mode": (
            flows_v2.HISTORICAL_AUTHORITY_MODE
            if historical_ef58
            else flows_v2.FRESH_AUTHORITY_MODE
        ),
        "flow_v1": flow_v1,
        "flow_v1_file": flow_v1_file,
        "flow_v2": flow_v2,
        "flow_v2_file": flow_v2_file,
        "hfs": hfs,
        "hfs_file": hfs_file,
        "sources": sources,
    }


def canonical_tar(payloads):
    """Return a byte-for-byte canonical USTAR archive of payload byte maps."""

    if not isinstance(payloads, dict) or not payloads:
        raise SemanticsV3Error("raw payload map is empty")
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name in sorted(payloads):
            data = payloads[name]
            if (
                not isinstance(name, str)
                or not SAFE_MEMBER.fullmatch(name)
                or name.startswith("/")
                or ".." in Path(name).parts
                or not isinstance(data, bytes)
                or not data
                or len(data) > MAX_RAW_MEMBER_BYTES
            ):
                raise SemanticsV3Error("raw payload name or bytes are invalid")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.mtime = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    data = output.getvalue()
    if len(data) > MAX_RAW_BUNDLE_BYTES:
        raise SemanticsV3Error("raw tar exceeds the size cap")
    return data


def raw_sidecar_bytes(bundle_name, bundle_data):
    if not isinstance(bundle_name, str) or not SAFE_MEMBER.fullmatch(bundle_name):
        raise SemanticsV3Error("raw bundle basename is unsafe")
    return "{0}  {1}\n".format(sha256_bytes(bundle_data), bundle_name).encode("ascii")


def decode_raw_bundle(bundle_data, sidecar_data):
    """Decode already-held raw authority bytes without reopening either path."""

    payloads = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(bundle_data), mode="r:") as archive:
            members = archive.getmembers()
            if not members or len(members) > MAX_RAW_MEMBERS:
                raise SemanticsV3Error("raw tar member count is invalid")
            for member in members:
                name = member.name
                if (
                    not member.isfile()
                    or not SAFE_MEMBER.fullmatch(name)
                    or name.startswith("/")
                    or ".." in Path(name).parts
                    or name in payloads
                    or member.mode != 0o644
                    or member.uid != 0
                    or member.gid != 0
                    or member.mtime != 0
                    or member.uname
                    or member.gname
                    or member.pax_headers
                    or member.size <= 0
                    or member.size > MAX_RAW_MEMBER_BYTES
                ):
                    raise SemanticsV3Error("raw tar member metadata is not canonical")
                handle = archive.extractfile(member)
                if handle is None:
                    raise SemanticsV3Error("raw tar member cannot be read")
                payloads[name] = handle.read()
    except (tarfile.TarError, OSError) as exc:
        raise SemanticsV3Error("cannot parse raw tar: {0}".format(exc))
    if canonical_tar(payloads) != bundle_data:
        raise SemanticsV3Error("raw tar bytes are not canonical USTAR")
    manifest_data = payloads.get("manifest.json")
    if manifest_data is None:
        raise SemanticsV3Error("raw tar omits manifest.json")
    manifest = decode_json(manifest_data, "raw manifest")
    if canonical_bytes(manifest) != manifest_data:
        raise SemanticsV3Error("raw manifest JSON bytes are not canonical")
    return manifest, payloads, {
        "artifact_bytes": len(bundle_data),
        "artifact_sha256": sha256_bytes(bundle_data),
        "manifest_sha256": sha256_bytes(manifest_data),
        "sha256_sidecar_bytes": len(sidecar_data),
        "sha256_sidecar_sha256": sha256_bytes(sidecar_data),
    }


def replay_raw_authority_pair(bundle_authority, sidecar_authority):
    """Bracket pair checks so neither held or named authority can move."""

    bundle_authority.replay_namespace()
    sidecar_authority.replay_namespace()
    bundle_authority.replay_namespace()
    sidecar_authority.replay_namespace()


def read_raw_bundle(bundle_path, sidecar_path):
    bundle_path = Path(bundle_path)
    with hold_confined_object(
        bundle_path, "raw bundle", MAX_RAW_BUNDLE_BYTES
    ) as bundle_authority:
        with hold_confined_object(
            sidecar_path, "raw bundle checksum", 4096
        ) as sidecar_authority:
            replay_raw_authority_pair(bundle_authority, sidecar_authority)
            bundle_data = bundle_authority.data
            sidecar_data = sidecar_authority.data
            expected_sidecar = raw_sidecar_bytes(bundle_path.name, bundle_data)
            replay_raw_authority_pair(bundle_authority, sidecar_authority)
            if sidecar_data != expected_sidecar:
                raise SemanticsV3Error(
                    "raw bundle checksum sidecar is non-canonical or stale"
                )
            replay_raw_authority_pair(bundle_authority, sidecar_authority)
            result = decode_raw_bundle(bundle_data, sidecar_data)
            replay_raw_authority_pair(bundle_authority, sidecar_authority)
            return result


def normalized_roots(repo, build_dir, kernel_dir):
    return (("$REPO", Path(repo)), ("$BUILD", Path(build_dir)), ("$KERNEL", Path(kernel_dir)))


def lexical_path_components(value, label, absolute):
    if not isinstance(value, str) or not value or "\0" in value or "\\" in value:
        raise SemanticsV3Error("{0} is not a safe lexical path".format(label))
    if any(ord(character) < 0x20 or ord(character) == 0x7f for character in value):
        raise SemanticsV3Error("{0} contains control characters".format(label))
    observed_absolute = value.startswith("/")
    if observed_absolute != absolute:
        raise SemanticsV3Error("{0} has the wrong path form".format(label))
    if absolute and value == "/":
        return ()
    components = value.split("/")[1:] if absolute else value.split("/")
    if absolute and not components:
        components = []
    if any(component in ("", ".", "..") for component in components):
        raise SemanticsV3Error("{0} contains an empty/dot component".format(label))
    return tuple(components)


def lexical_absolute_root(value, label):
    text = str(value)
    if not text.startswith("/"):
        text = str(Path.cwd() / text)
    components = lexical_path_components(text, label, True)
    return Path("/" + "/".join(components)) if components else Path("/")


def compiler_output_path(argv, language, cwd, allowed_absolute_roots=None):
    found = []
    index = 1
    while index < len(argv):
        word = argv[index]
        if language == "c" and word in ("-o", "--output"):
            if index + 1 >= len(argv):
                raise SemanticsV3Error("recorded output flag has no value")
            found.append(argv[index + 1])
            index += 2
            continue
        if language == "c" and (word.startswith("-o") and word != "-o"):
            found.append(word[2:])
        if language == "c" and word.startswith("--output="):
            found.append(word.split("=", 1)[1])
        if language == "rust" and word.startswith("--emit=obj="):
            found.append(word.split("=", 2)[2])
        index += 1
    if len(found) != 1 or not found[0]:
        raise SemanticsV3Error("recorded compiler argv has an ambiguous object output")
    raw_path = found[0]
    root = lexical_absolute_root(cwd, "compiler working directory")
    if raw_path.startswith("/"):
        output_components = lexical_path_components(
            raw_path, "recorded compiler object output", True
        )
        roots = tuple(allowed_absolute_roots or (root,))
        allowed = []
        for value in roots:
            candidate = lexical_absolute_root(value, "allowed object root")
            candidate_components = lexical_path_components(
                str(candidate), "allowed object root", True
            )
            if not candidate_components:
                raise SemanticsV3Error("allowed object root cannot be filesystem root")
            if output_components[:len(candidate_components)] == candidate_components:
                allowed.append(candidate_components)
        if not allowed:
            raise SemanticsV3Error("recorded compiler object output escapes allowed root")
        return Path("/" + "/".join(output_components))
    relative = lexical_path_components(
        raw_path, "recorded compiler object output", False
    )
    root_components = lexical_path_components(
        str(root), "compiler working directory", True
    )
    return Path("/" + "/".join(root_components + relative))


def object_identity(metadata, leaf):
    common = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
    )
    if not leaf:
        return common
    return common + (
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def read_fd_bytes(descriptor, maximum):
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    remaining = maximum + 1
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def replay_object_namespace(entries, label):
    for parent_fd, component, descriptor, expected, leaf in entries:
        try:
            held = object_identity(os.fstat(descriptor), leaf)
            namespace = object_identity(
                os.stat(component, dir_fd=parent_fd, follow_symlinks=False), leaf
            )
        except OSError as exc:
            raise SemanticsV3Error(
                "{0} namespace cannot be replayed: {1}".format(label, exc)
            )
        if held != expected or namespace != expected:
            raise SemanticsV3Error(
                "{0} descriptor or namespace identity changed".format(label)
            )


class HeldObject(object):
    __slots__ = (
        "data", "descriptors", "entries", "label", "leaf", "maximum"
    )

    def __init__(self, descriptors, entries, leaf, data, label, maximum):
        self.descriptors = descriptors
        self.entries = entries
        self.leaf = leaf
        self.data = data
        self.label = label
        self.maximum = maximum

    def replay(self):
        self.replay_namespace()
        current = read_fd_bytes(self.leaf, self.maximum)
        if current != self.data:
            raise SemanticsV3Error(
                "{0} bytes changed during held-descriptor replay".format(self.label)
            )
        self.replay_namespace()

    def replay_namespace(self):
        replay_object_namespace(self.entries, self.label)

    def close(self):
        descriptors = self.descriptors
        self.descriptors = []
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.close()
        return False


def hold_confined_object(path, label, maximum):
    """Open a single-link file through held no-follow descriptors for replay."""

    absolute = lexical_absolute_root(path, label + " path")
    components = lexical_path_components(str(absolute), label + " path", True)
    if not components:
        raise SemanticsV3Error("{0} path has no leaf".format(label))
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise SemanticsV3Error("no-follow file traversal is unavailable")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
        file_flags |= os.O_CLOEXEC
    descriptors = []
    entries = []
    try:
        current = os.open("/", directory_flags)
        descriptors.append(current)
        for component in components[:-1]:
            try:
                child = os.open(component, directory_flags, dir_fd=current)
            except OSError as exc:
                raise SemanticsV3Error(
                    "{0} has a symlink/non-directory ancestor: {1}".format(label, exc)
                )
            metadata = os.fstat(child)
            if not stat.S_ISDIR(metadata.st_mode):
                raise SemanticsV3Error("{0} ancestor is not a directory".format(label))
            entries.append(
                (current, component, child, object_identity(metadata, False), False)
            )
            descriptors.append(child)
            current = child
        leaf_name = components[-1]
        try:
            leaf = os.open(leaf_name, file_flags, dir_fd=current)
        except OSError as exc:
            raise SemanticsV3Error(
                "{0} leaf must be a regular non-symlink file: {1}".format(label, exc)
            )
        descriptors.append(leaf)
        metadata = os.fstat(leaf)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise SemanticsV3Error(
                "{0} leaf must be a single-link regular file".format(label)
            )
        if metadata.st_size <= 0 or metadata.st_size > maximum:
            raise SemanticsV3Error("{0} has an invalid size".format(label))
        entries.append(
            (current, leaf_name, leaf, object_identity(metadata, True), True)
        )
        first = read_fd_bytes(leaf, maximum)
        if not first or len(first) > maximum or len(first) != metadata.st_size:
            raise SemanticsV3Error("{0} has an invalid size".format(label))
        replay_object_namespace(entries, label)
        second = read_fd_bytes(leaf, maximum)
        if first != second:
            raise SemanticsV3Error("{0} bytes changed during descriptor replay".format(label))
        replay_object_namespace(entries, label)
        return HeldObject(descriptors, entries, leaf, first, label, maximum)
    except OSError as exc:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise SemanticsV3Error("cannot read {0}: {1}".format(label, exc))
    except Exception:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def read_confined_object_bytes(path, label, maximum):
    """Read and close one fully replayed, descriptor-confined object snapshot."""

    with hold_confined_object(path, label, maximum) as held:
        held.replay()
        return held.data


def read_object(path, label):
    data = read_confined_object_bytes(path, label, MAX_RAW_MEMBER_BYTES)
    return {"bytes": len(data), "sha256": sha256_bytes(data)}, data


def reconstruct_c_argv(original, source_index, output):
    if not isinstance(original, list) or source_index <= 0 or source_index >= len(original):
        raise SemanticsV3Error("recorded C compiler argv is malformed")
    source_word = original[source_index]
    result = [original[0]]
    index = 1
    saw_compile = False
    while index < len(original):
        word = original[index]
        if index == source_index:
            index += 1
            continue
        if word in flows_v1.DEPENDENCY_FLAGS:
            index += 1
            continue
        if word in flows_v1.DEPENDENCY_VALUE_FLAGS or word in flows_v1.OUTPUT_VALUE_FLAGS:
            if index + 1 >= len(original):
                raise SemanticsV3Error("recorded C flag lacks a value")
            index += 2
            continue
        if any(
            word.startswith(flag) and word != flag
            for flag in flows_v1.DEPENDENCY_VALUE_FLAGS
        ):
            index += 1
            continue
        if (
            (word.startswith("-o") and word != "-o")
            or word.startswith("--output=")
            or word.startswith("-Wp,-MD,")
            or word.startswith("-Wp,-MMD,")
        ):
            index += 1
            continue
        if flows_v1.unsafe_replay_option(word):
            raise SemanticsV3Error("recorded C argv has an unsafe replay option")
        if (
            word in ("-E", "-S")
            or word.startswith("-fdump-")
            or word.startswith("-save-temps")
            or word.startswith("-dumpbase")
            or word.startswith("-dumpdir")
            or word.startswith("-auxbase")
            or word == "-flto"
            or word.startswith("-flto=")
        ):
            raise SemanticsV3Error("recorded C argv has unsupported persistent analysis state")
        if word == "-c":
            saw_compile = True
        result.append(word)
        index += 1
    if not saw_compile:
        result.append("-c")
    result.extend(option for _, option, _ in C_DUMP_OPTIONS)
    result.extend(("-fno-diagnostics-color", "-o", str(output), source_word))
    return result


def reconstruct_c_baseline_argv(original, source_index, output):
    """Replay the recorded compiler profile without analysis-only dump flags."""

    semantic = reconstruct_c_argv(original, source_index, output)
    dump_options = {option for _, option, _ in C_DUMP_OPTIONS}
    return [word for word in semantic if word not in dump_options]


def reconstruct_rust_argv(original, output, mir_dir):
    if not isinstance(original, list) or len(original) < 2:
        raise SemanticsV3Error("recorded Rust compiler argv is malformed")
    result = []
    replaced = 0
    for word in original:
        if word.startswith("--emit=obj="):
            result.append("--emit=obj={0}".format(output))
            replaced += 1
            continue
        if word.startswith("-Zdump-mir"):
            raise SemanticsV3Error("recorded Rust argv already requests MIR dumps")
        if word.startswith("@") or "\0" in word:
            raise SemanticsV3Error("recorded Rust argv has an unsafe response/control word")
        result.append(word)
    if replaced != 1:
        raise SemanticsV3Error("recorded Rust object redirection is ambiguous")
    result.extend(RUST_MIR_OPTIONS)
    result.append("-Zdump-mir-dir={0}".format(mir_dir))
    return result


def run_compiler(argv, cwd, environment):
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SemanticsV3Error("semantic compiler replay failed: {0}".format(exc))
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-8000:]
        raise SemanticsV3Error(
            "semantic compiler replay exited {0}: {1}".format(
                completed.returncode, stderr.strip()
            )
        )
    return completed


def one_c_run(record, source_path, source_index, kernel_dir, roots, run_dir, environment):
    run_roots = tuple(roots) + (("$SEMANTIC", run_dir),)
    baseline_output = run_dir / "baseline.o"
    baseline_argv = reconstruct_c_baseline_argv(
        record["compile_argv"], source_index, baseline_output
    )
    baseline_completed = run_compiler(baseline_argv, kernel_dir, environment)
    with hold_confined_object(
        baseline_output, "C recorded-profile replay object", MAX_RAW_MEMBER_BYTES
    ) as baseline_authority:
        baseline_data = baseline_authority.data
        baseline_record = {
            "bytes": len(baseline_data),
            "sha256": sha256_bytes(baseline_data),
        }
        output = run_dir / "semantic.o"
        argv = reconstruct_c_argv(record["compile_argv"], source_index, output)
        completed = run_compiler(argv, kernel_dir, environment)
        object_record, object_data = read_object(output, "C semantic replay object")
        if object_data != baseline_data:
            raise SemanticsV3Error(
                "C semantic replay object differs from recorded-profile replay"
            )
        baseline_authority.replay()
    dumps = {}
    for label, _, suffix in C_DUMP_OPTIONS:
        matches = sorted(run_dir.glob("*" + suffix))
        if len(matches) != 1:
            raise SemanticsV3Error(
                "C semantic replay produced {0} {1} dumps".format(len(matches), label)
            )
        data = read_regular_bytes(matches[0], "C {0} dump".format(label), MAX_RAW_MEMBER_BYTES)
        dumps[label] = flows_v1.normalized_dump(data, run_roots, output)
    return {
        "argv": flows_v1.normalized_argv(argv, run_roots, output),
        "baseline_argv": flows_v1.normalized_argv(
            baseline_argv, run_roots, baseline_output
        ),
        "baseline_object": baseline_record,
        "dumps": dumps,
        "object": object_record,
        "object_data": object_data,
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "baseline_stderr_sha256": sha256_bytes(baseline_completed.stderr),
        "baseline_stdout_sha256": sha256_bytes(baseline_completed.stdout),
    }


def capture_c_source(record, source_path, kernel_dir, roots, temporary, environment):
    try:
        compiler = sites.compiler_provenance(record["compile_argv"][0], environment)
    except sites.CaptureError as exc:
        raise SemanticsV3Error("cannot probe C compiler: {0}".format(exc))
    if compiler["sha256"] != record["digests"]["compiler_sha256"]:
        raise SemanticsV3Error("C semantic compiler differs from HFS")
    if not strict_equal(compiler, record["preprocessor"]):
        raise SemanticsV3Error("C compiler version probe differs from HFS")
    source_index = flows_v1.source_index_in_argv(
        record["compile_argv"], source_path, kernel_dir
    )
    runs = []
    for number in (1, 2):
        run_dir = temporary / "c-{0}-{1}".format(
            sha256_bytes(record["source"].encode("utf-8"))[:16], number
        )
        run_dir.mkdir(mode=0o700)
        runs.append(
            one_c_run(
                record, source_path, source_index, kernel_dir, roots,
                run_dir, environment,
            )
        )
    if (
        runs[0]["argv"] != runs[1]["argv"]
        or runs[0]["baseline_argv"] != runs[1]["baseline_argv"]
        or runs[0]["dumps"] != runs[1]["dumps"]
        or runs[0]["object"] != runs[1]["object"]
        or runs[0]["baseline_object"] != runs[1]["baseline_object"]
        or runs[0]["stdout_sha256"] != runs[1]["stdout_sha256"]
        or runs[0]["stderr_sha256"] != runs[1]["stderr_sha256"]
        or runs[0]["baseline_stdout_sha256"] != runs[1]["baseline_stdout_sha256"]
        or runs[0]["baseline_stderr_sha256"] != runs[1]["baseline_stderr_sha256"]
    ):
        raise SemanticsV3Error("C semantic replay is not deterministic across two runs")
    return compiler, runs[0]["baseline_object"], runs[0]


def probe_rust_mir_options(executable, environment):
    try:
        completed = subprocess.run(
            [executable, "-Z", "help"],
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SemanticsV3Error("cannot probe Rust MIR options: {0}".format(exc))
    if completed.returncode != 0:
        raise SemanticsV3Error("pinned rustc rejected -Z help")
    output = completed.stdout.decode("utf-8", errors="replace")
    for spelling in ("dump-mir", "dump-mir-dir", "dump-mir-exclude-pass-number"):
        if spelling not in output:
            raise SemanticsV3Error("pinned rustc omits -Z {0}".format(spelling))
    return {
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout_sha256": sha256_bytes(completed.stdout),
    }


def one_rust_run(record, kernel_dir, roots, run_dir, environment):
    run_roots = tuple(roots) + (("$SEMANTIC", run_dir),)
    output = run_dir / "semantic-rust.o"
    mir_dir = run_dir / "mir"
    mir_dir.mkdir(mode=0o700)
    argv = reconstruct_rust_argv(record["compile_argv"], output, mir_dir)
    completed = run_compiler(argv, kernel_dir, environment)
    object_record, object_data = read_object(output, "Rust semantic replay object")
    mir = {}
    for path in sorted(mir_dir.rglob("*")):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise SemanticsV3Error("rustc MIR directory contains a non-regular entry")
        if not path.is_file():
            continue
        relative = path.relative_to(mir_dir).as_posix()
        require_safe_relative_path(relative, "rustc MIR filename")
        if not relative.endswith(RUST_SELECTED_STAGE_SUFFIXES):
            continue
        data = read_regular_bytes(path, "Rust MIR dump", MAX_RAW_MEMBER_BYTES)
        mir[relative] = flows_v1.normalized_dump(data, run_roots, output)
    if not mir:
        raise SemanticsV3Error("rustc produced no MIR dumps")
    return {
        "argv": flows_v1.normalized_argv(argv, run_roots, output),
        "mir": mir,
        "object": object_record,
        "object_data": object_data,
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout_sha256": sha256_bytes(completed.stdout),
    }


def capture_rust_source(
    record, kernel_dir, build_dir, roots, temporary, environment
):
    try:
        compiler = sites.compiler_provenance(record["compile_argv"][0], environment)
    except sites.CaptureError as exc:
        raise SemanticsV3Error("cannot probe Rust compiler: {0}".format(exc))
    if not strict_equal(compiler, record["recorded_compiler"]):
        raise SemanticsV3Error("Rust semantic compiler differs from exact HFS provenance")
    probe = probe_rust_mir_options(record["compile_argv"][0], environment)
    production_path = compiler_output_path(
        record["compile_argv"], "rust", kernel_dir, (build_dir,)
    )
    with hold_confined_object(
        production_path, "production Rust object", MAX_RAW_MEMBER_BYTES
    ) as production_authority:
        production_data = production_authority.data
        production_record = {
            "bytes": len(production_data),
            "sha256": sha256_bytes(production_data),
        }
        runs = []
        for number in (1, 2):
            run_dir = temporary / "rust-{0}".format(number)
            run_dir.mkdir(mode=0o700)
            runs.append(one_rust_run(record, kernel_dir, roots, run_dir, environment))
        if (
            runs[0]["object_data"] != production_data
            or runs[1]["object_data"] != production_data
        ):
            raise SemanticsV3Error("Rust MIR replay object differs from production")
        if (
            runs[0]["argv"] != runs[1]["argv"]
            or runs[0]["mir"] != runs[1]["mir"]
            or runs[0]["object"] != runs[1]["object"]
            or runs[0]["stdout_sha256"] != runs[1]["stdout_sha256"]
            or runs[0]["stderr_sha256"] != runs[1]["stderr_sha256"]
        ):
            raise SemanticsV3Error("Rust MIR replay is not deterministic across two runs")
        production_authority.replay()
    return compiler, probe, production_record, runs[0]


def manifest_input_bindings(inputs):
    return {
        "failure_flows_v1": input_binding(inputs["flow_v1"], inputs["flow_v1_file"]),
        "failure_flows_v2": input_binding(inputs["flow_v2"], inputs["flow_v2_file"]),
        "failure_sites_v1": input_binding(inputs["hfs"], inputs["hfs_file"]),
    }


def capture_raw_bundle(inputs, repo, build_dir, kernel_dir, output, sidecar, environment=None):
    if inputs["authority_mode"] != flows_v2.FRESH_AUTHORITY_MODE:
        raise SemanticsV3Error("historical mode cannot execute semantic compilers")
    repo = Path(repo).resolve()
    build_dir = Path(build_dir).resolve()
    kernel_dir = Path(kernel_dir).resolve()
    if not repo.is_dir() or not build_dir.is_dir() or not kernel_dir.is_dir():
        raise SemanticsV3Error("fresh raw capture requires repo/build/kernel directories")
    environment = dict(environment or os.environ)
    roots = normalized_roots(repo, build_dir, kernel_dir)
    unresolved_sources = {
        row["source"]
        for row in inputs["flow_v1"]["unresolved_paths"]
        if row.get("kind") == "return_value_error_domain_unresolved"
    }
    payloads = {}
    invocations = []
    toolchains = {"c": [], "rust": None}
    files = []
    with tempfile.TemporaryDirectory(prefix="host-module-semantics-v3-raw.") as temp:
        temporary = Path(temp)
        for source in sorted(unresolved_sources):
            record = inputs["sources"].get(source)
            if record is None or record.get("language") != "c":
                raise SemanticsV3Error("C semantic row names an unknown C source")
            source_path = repo / source
            compiler, production, run = capture_c_source(
                record, source_path, kernel_dir, roots, temporary, environment
            )
            toolchain = {
                "compiler": compiler,
                "source": source,
            }
            toolchains["c"].append(toolchain)
            prefix = "c/{0}".format(sha256_bytes(source.encode("utf-8"))[:24])
            dump_bindings = {}
            for label, _, _ in C_DUMP_OPTIONS:
                name = "{0}/{1}.txt".format(prefix, label)
                data = run["dumps"][label]
                payloads[name] = data
                binding = {"bytes": len(data), "path": name, "sha256": sha256_bytes(data)}
                files.append({"kind": "c_{0}".format(label), "source": source, **binding})
                dump_bindings[label] = binding
            invocations.append(
                {
                    "baseline_stderr_sha256": run["baseline_stderr_sha256"],
                    "baseline_stdout_sha256": run["baseline_stdout_sha256"],
                    "compiler_sha256": compiler["sha256"],
                    "dumps": dump_bindings,
                    "language": "c",
                    "normalized_baseline_argv": run["baseline_argv"],
                    "normalized_baseline_argv_sha256": sha256_bytes(
                        canonical_bytes(run["baseline_argv"])
                    ),
                    "normalized_replay_argv": run["argv"],
                    "normalized_replay_argv_sha256": sha256_bytes(canonical_bytes(run["argv"])),
                    "production_object": production,
                    "production_object_kind": "recorded_profile_side_effect_free_replay",
                    "recorded_argv": record["compile_argv"],
                    "recorded_argv_sha256": sha256_bytes(canonical_bytes(record["compile_argv"])),
                    "replay_object": run["object"],
                    "object_byte_equality": True,
                    "source": source,
                    "stderr_sha256": run["stderr_sha256"],
                    "stdout_sha256": run["stdout_sha256"],
                    "two_run_normalized_determinism": True,
                }
            )

        rust_record = next(
            record for record in inputs["sources"].values() if record["language"] == "rust"
        )
        compiler, probe, production, run = capture_rust_source(
            rust_record, kernel_dir, build_dir, roots, temporary, environment
        )
        toolchains["rust"] = {"compiler": compiler, "mir_option_probe": probe}
        mir_bindings = []
        for compiler_path in sorted(run["mir"]):
            data = run["mir"][compiler_path]
            name = "rust/mir/{0}.mir".format(
                sha256_bytes(compiler_path.encode("utf-8"))
            )
            payloads[name] = data
            binding = {
                "bytes": len(data),
                "compiler_path": compiler_path,
                "path": name,
                "sha256": sha256_bytes(data),
            }
            files.append(
                {
                    "bytes": binding["bytes"],
                    "kind": "rust_mir",
                    "path": binding["path"],
                    "sha256": binding["sha256"],
                    "source": rust_record["source"],
                }
            )
            mir_bindings.append(binding)
        invocations.append(
            {
                "compiler_sha256": compiler["sha256"],
                "language": "rust",
                "mir_files": mir_bindings,
                "normalized_replay_argv": run["argv"],
                "normalized_replay_argv_sha256": sha256_bytes(canonical_bytes(run["argv"])),
                "production_object": production,
                "production_object_kind": "built_rust_object",
                "recorded_argv": rust_record["compile_argv"],
                "recorded_argv_sha256": sha256_bytes(canonical_bytes(rust_record["compile_argv"])),
                "replay_object": run["object"],
                "object_byte_equality": True,
                "source": rust_record["source"],
                "stderr_sha256": run["stderr_sha256"],
                "stdout_sha256": run["stdout_sha256"],
                "two_run_normalized_determinism": True,
            }
        )

    manifest = {
        "authority_mode": inputs["authority_mode"],
        "compiler_invocations": sorted(invocations, key=lambda item: (item["language"], item["source"])),
        "files": sorted(files, key=lambda item: item["path"]),
        "generator": "scripts/host_module_failure_semantics_v3.py",
        "inputs": manifest_input_bindings(inputs),
        "profile": RAW_PROFILE,
        "schema_version": RAW_SCHEMA_VERSION,
        "toolchains": toolchains,
    }
    payloads["manifest.json"] = canonical_bytes(manifest)
    bundle_data = canonical_tar(payloads)
    sidecar_data = raw_sidecar_bytes(Path(output).name, bundle_data)
    atomic_write(output, bundle_data)
    atomic_write(sidecar, sidecar_data)
    return manifest


def validate_file_binding(binding, payloads, label, extra_keys=None):
    expected = {"bytes", "path", "sha256"} | set(extra_keys or ())
    require_exact_keys(binding, expected, label)
    path = require_string(binding["path"], label + " path")
    if path == "manifest.json" or path not in payloads:
        raise SemanticsV3Error("{0} names a missing payload".format(label))
    data = payloads[path]
    if (
        type(binding["bytes"]) is not int
        or binding["bytes"] != len(data)
        or binding["sha256"] != sha256_bytes(data)
    ):
        raise SemanticsV3Error("{0} digest or size differs".format(label))
    return data


def invocation_source_index(argv, source):
    """Locate the one recorded source word without trusting a manifest index."""

    if not isinstance(argv, list) or not argv:
        raise SemanticsV3Error("recorded compiler argv is malformed")
    suffix = "/" + require_safe_relative_path(source, "compiler source")
    candidates = []
    for index, word in enumerate(argv):
        if not isinstance(word, str) or "\0" in word:
            raise SemanticsV3Error("recorded compiler argv contains a non-string/control word")
        normalized_word = os.path.normpath(word).replace("\\", "/")
        if not word.startswith("-") and (
            normalized_word == source or normalized_word.endswith(suffix)
        ):
            candidates.append(index)
    if len(candidates) != 1:
        raise SemanticsV3Error("recorded compiler argv source is ambiguous")
    return candidates[0]


def validate_normalized_word(expected, observed, bindings, label):
    """Prove that a normalized word differs only by one captured root prefix."""

    if not isinstance(observed, str) or "\0" in observed:
        raise SemanticsV3Error("{0} contains a non-string/control word".format(label))
    if observed == expected:
        return
    root_labels = ("$REPO", "$BUILD", "$KERNEL")
    present = [item for item in root_labels if item in observed]
    if len(present) != 1 or observed.count(present[0]) != 1:
        raise SemanticsV3Error("{0} changes a recorded compiler word".format(label))
    root_label = present[0]
    before, after = observed.split(root_label)
    if not expected.startswith(before) or (after and not expected.endswith(after)):
        raise SemanticsV3Error("{0} changes a recorded compiler word".format(label))
    end = len(expected) - len(after) if after else len(expected)
    candidate = expected[len(before):end]
    if (
        not candidate.startswith("/")
        or candidate == "/"
        or os.path.normpath(candidate) != candidate
        or "\0" in candidate
    ):
        raise SemanticsV3Error("{0} has an invalid normalized root".format(label))
    previous = bindings.get(root_label)
    if previous is not None and previous != candidate:
        raise SemanticsV3Error("{0} changes a normalized root binding".format(label))
    bindings[root_label] = candidate


def validate_normalized_argv(expected, observed, bindings, label):
    if not isinstance(observed, list) or len(observed) != len(expected):
        raise SemanticsV3Error("{0} does not preserve recorded argv".format(label))
    for index, (expected_word, observed_word) in enumerate(zip(expected, observed)):
        validate_normalized_word(
            expected_word,
            observed_word,
            bindings,
            "{0} word {1}".format(label, index),
        )


def validate_raw_manifest(manifest, payloads, inputs):
    validate_type_strict_json(manifest, "raw manifest")
    require_exact_keys(
        manifest,
        {
            "authority_mode", "compiler_invocations", "files", "generator",
            "inputs", "profile", "schema_version", "toolchains",
        },
        "raw manifest",
    )
    require_exact_integer(
        manifest["schema_version"], RAW_SCHEMA_VERSION, "raw manifest schema version"
    )
    require_enum(
        manifest["authority_mode"],
        {flows_v2.FRESH_AUTHORITY_MODE, flows_v2.HISTORICAL_AUTHORITY_MODE},
        "raw manifest authority mode",
    )
    if (
        manifest["profile"] != RAW_PROFILE
        or manifest["generator"] != "scripts/host_module_failure_semantics_v3.py"
        or manifest["authority_mode"] != inputs["authority_mode"]
        or not strict_equal(manifest["inputs"], manifest_input_bindings(inputs))
    ):
        raise SemanticsV3Error("raw manifest authority changed")
    require_exact_keys(
        manifest["inputs"],
        {"failure_flows_v1", "failure_flows_v2", "failure_sites_v1"},
        "raw manifest inputs",
    )
    for name in sorted(manifest["inputs"]):
        validate_artifact_binding(
            manifest["inputs"][name], "raw manifest input " + name
        )
    files = manifest["files"]
    if (
        type(files) is not list
        or any(type(item) is not dict for item in files)
        or files != sorted(files, key=lambda item: item.get("path", ""))
    ):
        raise SemanticsV3Error("raw manifest files are not canonical")
    observed_paths = set()
    files_by_path = {}
    for index, binding in enumerate(files):
        require_exact_keys(binding, {"bytes", "kind", "path", "sha256", "source"}, "raw file")
        if binding["path"] in observed_paths:
            raise SemanticsV3Error("raw manifest file paths are duplicated")
        observed_paths.add(binding["path"])
        files_by_path[binding["path"]] = binding
        validate_file_binding(
            {key: binding[key] for key in ("bytes", "path", "sha256")},
            payloads,
            "raw file {0}".format(index),
        )
        require_enum(
            binding["kind"],
            {"c_original", "c_gimple", "c_ssa", "c_evrp", "c_vrp", "rust_mir"},
            "raw manifest file kind",
        )
        require_string(binding["source"], "raw manifest file source")
    if observed_paths != set(payloads) - {"manifest.json"}:
        raise SemanticsV3Error("raw manifest does not close the tar payload set")

    invocations = manifest["compiler_invocations"]
    if (
        type(invocations) is not list
        or any(type(item) is not dict for item in invocations)
        or invocations != sorted(
            invocations,
            key=lambda item: (item.get("language", ""), item.get("source", "")),
        )
    ):
        raise SemanticsV3Error("raw compiler invocations are not canonical")
    by_source = {}
    referenced_paths = set()
    normalization_bindings = {}
    for invocation in invocations:
        language = invocation.get("language") if isinstance(invocation, dict) else None
        require_enum(language, {"c", "rust"}, "raw compiler language")
        common = {
            "compiler_sha256", "language", "normalized_replay_argv",
            "normalized_replay_argv_sha256", "production_object", "recorded_argv",
            "recorded_argv_sha256", "replay_object", "source", "stderr_sha256",
            "stdout_sha256", "two_run_normalized_determinism",
            "object_byte_equality", "production_object_kind",
        }
        expected = common | (
            {
                "baseline_stderr_sha256", "baseline_stdout_sha256", "dumps",
                "normalized_baseline_argv", "normalized_baseline_argv_sha256",
            }
            if language == "c"
            else {"mir_files"}
            if language == "rust"
            else set()
        )
        require_exact_keys(invocation, expected, "raw compiler invocation")
        source = invocation["source"]
        require_string(source, "raw compiler source")
        source_record = inputs["sources"].get(source)
        if source_record is None or source in by_source or source_record["language"] != language:
            raise SemanticsV3Error("raw compiler invocation source is unknown or duplicated")
        by_source[source] = invocation
        if (
            not strict_equal(invocation["recorded_argv"], source_record["compile_argv"])
            or invocation["recorded_argv_sha256"] != sha256_bytes(canonical_bytes(source_record["compile_argv"]))
            or invocation["compiler_sha256"] != source_record["digests"]["compiler_sha256"]
            or invocation["two_run_normalized_determinism"] is not True
            or invocation["object_byte_equality"] is not True
            or not isinstance(invocation["normalized_replay_argv"], list)
            or invocation["normalized_replay_argv_sha256"] != sha256_bytes(canonical_bytes(invocation["normalized_replay_argv"]))
        ):
            raise SemanticsV3Error("raw compiler invocation authority differs")
        require_boolean(
            invocation["two_run_normalized_determinism"],
            "raw compiler two-run determinism",
        )
        require_boolean(
            invocation["object_byte_equality"], "raw compiler object equality"
        )
        for field in ("production_object", "replay_object"):
            require_exact_keys(invocation[field], {"bytes", "sha256"}, field)
            if type(invocation[field]["bytes"]) is not int or invocation[field]["bytes"] <= 0:
                raise SemanticsV3Error("raw object byte count is invalid")
            require_digest(invocation[field]["sha256"], field)
        if not strict_equal(invocation["production_object"], invocation["replay_object"]):
            raise SemanticsV3Error("semantic replay object differs from production object")
        for field in ("compiler_sha256", "recorded_argv_sha256", "normalized_replay_argv_sha256", "stderr_sha256", "stdout_sha256"):
            require_digest(invocation[field], field)
        if language == "c":
            if (
                invocation["production_object_kind"]
                != "recorded_profile_side_effect_free_replay"
                or not isinstance(invocation["normalized_baseline_argv"], list)
                or invocation["normalized_baseline_argv_sha256"]
                != sha256_bytes(canonical_bytes(invocation["normalized_baseline_argv"]))
            ):
                raise SemanticsV3Error("C baseline compiler replay binding differs")
            source_index = invocation_source_index(
                invocation["recorded_argv"], source
            )
            expected_baseline = reconstruct_c_baseline_argv(
                invocation["recorded_argv"], source_index, Path("$OUTPUT")
            )
            expected_replay = reconstruct_c_argv(
                invocation["recorded_argv"], source_index, Path("$OUTPUT")
            )
            validate_normalized_argv(
                expected_baseline,
                invocation["normalized_baseline_argv"],
                normalization_bindings,
                "C normalized baseline argv",
            )
            validate_normalized_argv(
                expected_replay,
                invocation["normalized_replay_argv"],
                normalization_bindings,
                "C normalized replay argv",
            )
            if (
                "$REPO" not in invocation["normalized_baseline_argv"][-1]
                or "$REPO" not in invocation["normalized_replay_argv"][-1]
            ):
                raise SemanticsV3Error("C normalized argv does not bind the repository source")
            for field in (
                "baseline_stderr_sha256", "baseline_stdout_sha256",
                "normalized_baseline_argv_sha256",
            ):
                require_digest(invocation[field], field)
            dumps = require_exact_keys(invocation["dumps"], {item[0] for item in C_DUMP_OPTIONS}, "C dump map")
            for label in sorted(dumps):
                validate_file_binding(dumps[label], payloads, "C {0} dump".format(label))
                path = dumps[label]["path"]
                file_record = files_by_path.get(path)
                if (
                    file_record is None
                    or file_record["kind"] != "c_" + label
                    or file_record["source"] != source
                    or path in referenced_paths
                ):
                    raise SemanticsV3Error("C dump file authority differs")
                referenced_paths.add(path)
        else:
            if invocation["production_object_kind"] != "built_rust_object":
                raise SemanticsV3Error("Rust production object binding differs")
            if source_record["digests"]["recorded_compile_argv_sha256"] != EXPECTED_RUST["argv_sha256"]:
                raise SemanticsV3Error("Rust recorded argv digest changed")
            expected_replay = reconstruct_rust_argv(
                invocation["recorded_argv"], Path("$OUTPUT"), Path("$SEMANTIC/mir")
            )
            validate_normalized_argv(
                expected_replay,
                invocation["normalized_replay_argv"],
                normalization_bindings,
                "Rust normalized replay argv",
            )
            rust_source_index = invocation_source_index(
                invocation["recorded_argv"], source
            )
            if "$REPO" not in invocation["normalized_replay_argv"][rust_source_index]:
                raise SemanticsV3Error("Rust normalized argv does not bind the repository source")
            mir_files = invocation["mir_files"]
            if not isinstance(mir_files, list) or not mir_files:
                raise SemanticsV3Error("Rust MIR file closure is empty")
            compiler_paths = set()
            for binding in mir_files:
                validate_file_binding(binding, payloads, "Rust MIR", {"compiler_path"})
                compiler_path = require_safe_relative_path(
                    binding["compiler_path"], "Rust compiler MIR path"
                )
                if (
                    compiler_path in compiler_paths
                    or not compiler_path.endswith(RUST_SELECTED_STAGE_SUFFIXES)
                ):
                    raise SemanticsV3Error("Rust compiler MIR paths are unsafe or duplicated")
                compiler_paths.add(compiler_path)
                path = binding["path"]
                file_record = files_by_path.get(path)
                if (
                    file_record is None
                    or file_record["kind"] != "rust_mir"
                    or file_record["source"] != source
                    or path in referenced_paths
                ):
                    raise SemanticsV3Error("Rust MIR file authority differs")
                referenced_paths.add(path)

    unresolved_sources = {
        row["source"] for row in inputs["flow_v1"]["unresolved_paths"]
        if row.get("kind") == "return_value_error_domain_unresolved"
    }
    rust_source = next(record["source"] for record in inputs["sources"].values() if record["language"] == "rust")
    if set(by_source) != unresolved_sources | {rust_source}:
        raise SemanticsV3Error("raw compiler invocation source closure changed")
    if referenced_paths != observed_paths:
        raise SemanticsV3Error("raw compiler invocations do not close the payload set")
    toolchains = require_exact_keys(manifest["toolchains"], {"c", "rust"}, "raw toolchains")
    if (
        type(toolchains["c"]) is not list
        or any(type(item) is not dict for item in toolchains["c"])
        or len(toolchains["c"]) != EXPECTED_C_SOURCE_COUNT
    ):
        raise SemanticsV3Error("raw C toolchain closure changed")
    if toolchains["c"] != sorted(toolchains["c"], key=lambda item: item.get("source", "")):
        raise SemanticsV3Error("raw C toolchains are not canonical")
    c_toolchain_sources = set()
    for toolchain in toolchains["c"]:
        require_exact_keys(toolchain, {"compiler", "source"}, "raw C toolchain")
        source = toolchain["source"]
        source_record = inputs["sources"].get(source)
        if (
            source_record is None
            or source_record.get("language") != "c"
            or source in c_toolchain_sources
            or not strict_equal(toolchain["compiler"], source_record.get("preprocessor"))
        ):
            raise SemanticsV3Error("raw C toolchain authority differs")
        c_toolchain_sources.add(source)
    rust_toolchain = require_exact_keys(toolchains["rust"], {"compiler", "mir_option_probe"}, "raw Rust toolchain")
    compiler = rust_toolchain["compiler"]
    if (
        not strict_equal(
            compiler,
            next(
                record["recorded_compiler"]
                for record in inputs["sources"].values()
                if record["language"] == "rust"
            ),
        )
        or
        compiler.get("sha256") != EXPECTED_RUST["compiler_sha256"]
        or compiler.get("version_first_line") != EXPECTED_RUST["version_first_line"]
        or compiler.get("launcher", {}).get("sha256") != EXPECTED_RUST["launcher_sha256"]
    ):
        raise SemanticsV3Error("raw Rust toolchain binding differs")
    require_exact_keys(rust_toolchain["mir_option_probe"], {"stderr_sha256", "stdout_sha256"}, "Rust MIR probe")
    for field in ("stderr_sha256", "stdout_sha256"):
        require_digest(rust_toolchain["mir_option_probe"][field], "Rust MIR probe " + field)
    if c_toolchain_sources != {
        source for source, record in inputs["sources"].items()
        if record["language"] == "c" and source in by_source
    }:
        raise SemanticsV3Error("raw C toolchain source closure differs")
    manifest_payload = payloads.get("manifest.json")
    if manifest_payload is not None and manifest_payload != canonical_bytes(manifest):
        raise SemanticsV3Error("raw manifest payload is not the exact canonical schema")
    return by_source


def validate_semantics_output_schema(capture):
    """Validate v3's derived JSON schema without relying on re-derivation."""

    validate_type_strict_json(capture, "v3 semantics")
    require_exact_keys(
        capture,
        {
            "analysis_claim", "authority_mode", "blockers", "c_return_contracts",
            "compiler_invocations", "coverage", "generator", "inputs", "profile",
            "raw_bundle", "rust_mir_sites", "schema_version", "toolchains",
        },
        "v3 semantics artifact",
    )
    require_exact_integer(
        capture["schema_version"], SCHEMA_VERSION, "v3 semantics schema version"
    )
    require_enum(
        capture["authority_mode"],
        {flows_v2.FRESH_AUTHORITY_MODE, flows_v2.HISTORICAL_AUTHORITY_MODE},
        "v3 semantics authority mode",
    )
    if (
        capture["profile"] != PROFILE
        or capture["generator"]
        != "scripts/host_module_failure_semantics_v3.py"
        or not strict_equal(capture["analysis_claim"], ANALYSIS_CLAIM)
        or not strict_equal(capture["blockers"], list(BLOCKERS))
    ):
        raise SemanticsV3Error("v3 semantics identity or non-crediting claim changed")
    require_exact_keys(
        capture["inputs"],
        {"failure_flows_v1", "failure_flows_v2", "failure_sites_v1"},
        "v3 semantics inputs",
    )
    for name in sorted(capture["inputs"]):
        validate_artifact_binding(
            capture["inputs"][name], "v3 semantics input " + name
        )
    validate_raw_bundle_record(capture["raw_bundle"], "v3 semantics raw bundle")
    coverage = require_exact_keys(
        capture["coverage"],
        {
            "c_function_count", "c_return_contract_count",
            "c_return_contract_count_by_module",
            "c_return_contract_count_by_status", "c_source_count",
            "c_terminal_count", "rust_mir_body_count", "rust_mir_site_count",
            "rust_mir_site_count_by_mapping_status",
            "semantic_error_domain_resolved_count", "tracker_credit_count",
        },
        "v3 semantics coverage",
    )
    for field in (
        "c_function_count", "c_return_contract_count", "c_source_count",
        "c_terminal_count", "rust_mir_body_count", "rust_mir_site_count",
        "semantic_error_domain_resolved_count", "tracker_credit_count",
    ):
        require_integer(coverage[field], "v3 semantics coverage " + field, minimum=0)
    require_count_map(
        coverage["c_return_contract_count_by_module"],
        "v3 C module coverage",
        EXPECTED_C_ROWS_BY_MODULE,
    )
    require_count_map(
        coverage["c_return_contract_count_by_status"],
        "v3 C status coverage",
    )
    require_count_map(
        coverage["rust_mir_site_count_by_mapping_status"],
        "v3 Rust mapping coverage",
    )
    if type(capture["c_return_contracts"]) is not list:
        raise SemanticsV3Error("v3 C return contracts must be an exact list")
    if type(capture["rust_mir_sites"]) is not list:
        raise SemanticsV3Error("v3 Rust MIR sites must be an exact list")
    if type(capture["compiler_invocations"]) is not list:
        raise SemanticsV3Error("v3 compiler invocations must be an exact list")
    if type(capture["toolchains"]) is not dict:
        raise SemanticsV3Error("v3 toolchains must be an exact object")
    for record in capture["c_return_contracts"]:
        if type(record) is not dict:
            raise SemanticsV3Error("v3 C return contract must be an exact object")
        require_enum(
            record.get("module"), set(EXPECTED_C_ROWS_BY_MODULE),
            "v3 C return contract module",
        )
        disposition = record.get("semantic_disposition")
        if type(disposition) is not dict:
            raise SemanticsV3Error("v3 C semantic disposition must be an exact object")
        require_enum(
            disposition.get("status"),
            {
                "mixed_or_unknown", "proven_error", "proven_non_error",
                "requires_semantic_oracle",
            },
            "v3 C semantic status",
        )
        require_enum(
            disposition.get("domain_kind"),
            {"compiler_domain_unbounded", "compiler_numeric_interval_observed"},
            "v3 C domain kind",
        )
        require_enum(
            disposition.get("proof_kind"),
            {"structural_compiler_evidence_only"},
            "v3 C proof kind",
        )
    mapping_statuses = {
        "multiple_unoptimized_mappings_semantics_unresolved",
        "optimized_only_mapping_semantics_unresolved",
        "unique_structural_mapping_semantics_unresolved",
    }
    for record in capture["rust_mir_sites"]:
        if type(record) is not dict:
            raise SemanticsV3Error("v3 Rust MIR site must be an exact object")
        require_enum(
            record.get("mapping_status"), mapping_statuses,
            "v3 Rust mapping status",
        )
        require_enum(
            record.get("semantic_status"), {"requires_semantic_oracle"},
            "v3 Rust semantic status",
        )
    return capture


def v1_semantic_rows(inputs):
    unresolved = [
        row for row in inputs["flow_v1"]["unresolved_paths"]
        if row.get("kind") == "return_value_error_domain_unresolved"
    ]
    terminals = [
        flow for flow in inputs["flow_v1"]["failure_flows"]
        if flow.get("expression_role") == "unresolved_return_candidate"
    ]
    source_modules = {source: record["module"] for source, record in inputs["sources"].items()}
    rows_by_module = Counter(source_modules[row["source"]] for row in unresolved)
    if (
        len(unresolved) != EXPECTED_C_ROW_COUNT
        or len(terminals) != EXPECTED_C_TERMINAL_COUNT
        or len({(row["source"], row["function"]) for row in unresolved}) != EXPECTED_C_FUNCTION_COUNT
        or len({row["source"] for row in unresolved}) != EXPECTED_C_SOURCE_COUNT
        or dict(sorted(rows_by_module.items())) != EXPECTED_C_ROWS_BY_MODULE
    ):
        raise SemanticsV3Error("immutable C semantic row/terminal closure changed")
    terminal_map = defaultdict(list)
    for flow in terminals:
        terminal_map[(flow["source"], flow["function"], flow["location"]["line"])].append(flow)
    for key in terminal_map:
        terminal_map[key].sort(key=lambda item: item["id"])
    return sorted(unresolved, key=canonical_bytes), terminal_map


def restore_dump_paths(data, repo, build_dir, kernel_dir):
    replacements = ((b"$REPO", str(Path(repo).resolve()).encode("utf-8")),
                    (b"$BUILD", str(Path(build_dir).resolve()).encode("utf-8")),
                    (b"$KERNEL", str(Path(kernel_dir).resolve()).encode("utf-8")))
    for old, new in replacements:
        data = data.replace(old, new)
    return data


def compiler_text(data, label):
    if isinstance(data, str):
        return data
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SemanticsV3Error("{0} is not UTF-8: {1}".format(label, exc))


def compiler_function_signatures(data):
    text = compiler_text(data, "GCC dump")
    header = re.compile(r"^;; Function\s+(?P<name>[^\s(]+).*?$", re.MULTILINE)
    matches = list(header.finditer(text))
    result = {}
    for index, match in enumerate(matches):
        name = match.group("name")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end():end]
        signature = None
        return_type = None
        pattern = re.compile(
            r"^\s*(?P<return>[^\n{};]+?)\s+" + re.escape(name) + r"\s*\([^;{}]*\)\s*$",
            re.MULTILINE,
        )
        found = pattern.search(section)
        if found:
            signature = found.group(0).strip()
            return_type = found.group("return").strip()
        result[name] = {
            "compiler_signature": signature,
            "return_type": return_type or "compiler_dump_unclassified",
        }
    return result


def dump_line_evidence(data, line):
    text = compiler_text(data, "GCC dump")
    location = re.compile(r"(?<![0-9]){0}(?::[0-9]+)?(?=[:\]])".format(line))
    matches = []
    for row in text.splitlines():
        if location.search(row):
            matches.append(row.strip())
    unique = sorted(set(item for item in matches if item))
    return {
        "matching_line_count": len(unique),
        "matching_lines_sha256": sha256_bytes(canonical_bytes(unique)),
        "sample": unique[:8],
    }


def vrp_interval_index(data):
    text = compiler_text(data, "GCC VRP dump")
    interval_pattern = re.compile(
        r"(?P<name>[A-Za-z_]\w*(?:\.[0-9]+)?|_[0-9]+)\s*[:=].*?"
        r"\[(?P<low>-?\d+|-INF),\s*(?P<high>-?\d+|\+?INF)\]"
    )
    intervals = defaultdict(list)
    for match in interval_pattern.finditer(text):
        intervals[match.group("name")].append(
            {
                "high": match.group("high"),
                "low": match.group("low"),
                "ssa_name": match.group("name"),
            }
        )
    return {
        name: sorted(
            {canonical_bytes(item): item for item in values}.values(),
            key=canonical_bytes,
        )
        for name, values in intervals.items()
    }


def vrp_intervals(data_or_index, terminal):
    index = (
        data_or_index
        if isinstance(data_or_index, dict)
        else vrp_interval_index(data_or_index)
    )
    names = set(
        re.findall(
            r"\b(?:[A-Za-z_]\w*|_[0-9]+)(?:\.[0-9]+)?\b",
            terminal["expression"],
        )
    )
    values = []
    for name in sorted(names):
        values.extend(index.get(name, []))
    return sorted(
        {canonical_bytes(item): item for item in values}.values(),
        key=canonical_bytes,
    )


def analyze_c_contracts(inputs, invocations, payloads, repo, build_dir, kernel_dir):
    rows, terminal_map = v1_semantic_rows(inputs)
    records = []
    source_cache = {}
    for row in rows:
        key = (row["source"], row["function"], row["line"])
        terminals = terminal_map.get(key, [])
        if len(terminals) not in (1, 2):
            raise SemanticsV3Error("C semantic row does not bind one or two HFF terminals")
        invocation = invocations.get(row["source"])
        if invocation is None or invocation["language"] != "c":
            raise SemanticsV3Error("C semantic row has no raw compiler invocation")
        cached = source_cache.get(row["source"])
        if cached is None:
            dump_data = {
                label: validate_file_binding(binding, payloads, "C {0}".format(label))
                for label, binding in invocation["dumps"].items()
            }
            restored_ssa = restore_dump_paths(
                dump_data["ssa"], repo, build_dir, kernel_dir
            )
            source_path = Path(repo) / row["source"]
            try:
                functions = flows_v1.parse_functions(
                    restored_ssa, source_path, kernel_dir
                )
            except flows_v1.FlowError as exc:
                raise SemanticsV3Error(
                    "cannot parse exact GCC SSA: {0}".format(exc)
                )
            cached = {
                "dump_data": dump_data,
                "dump_text": {
                    label: compiler_text(data, "GCC {0} dump".format(label))
                    for label, data in dump_data.items()
                },
                "functions": {item["name"]: item for item in functions},
                "signatures": compiler_function_signatures(dump_data["gimple"]),
                "vrp": vrp_interval_index(dump_data["vrp"]),
            }
            source_cache[row["source"]] = cached
        dump_data = cached["dump_data"]
        functions_by_name = cached["functions"]
        function = functions_by_name.get(row["function"])
        if function is None:
            raise SemanticsV3Error("C semantic row function is absent from SSA")
        signature = cached["signatures"].get(row["function"], {
            "compiler_signature": None,
            "return_type": "compiler_dump_unclassified",
        })
        terminal_records = []
        intervals = []
        for terminal in terminals:
            terminal_sha = sha256_bytes(canonical_bytes(terminal))
            terminal_intervals = vrp_intervals(cached["vrp"], terminal)
            intervals.extend(terminal_intervals)
            terminal_records.append(
                {
                    "compiler_generic": dump_line_evidence(
                        cached["dump_text"]["original"], row["line"]
                    ),
                    "compiler_ssa": {
                        "expression": terminal["expression"],
                        "location": terminal["location"],
                        "origins": terminal["origin"].get("ssa_origins", []),
                    },
                    "hff_id": terminal["id"],
                    "hff_sha256": terminal_sha,
                    "source_span": {
                        "column": terminal["location"]["column"],
                        "line": terminal["location"]["line"],
                    },
                    "vrp_intervals": terminal_intervals,
                }
            )
        intervals = sorted(
            {canonical_bytes(item): item for item in intervals}.values(),
            key=canonical_bytes,
        )
        row_sha = sha256_bytes(canonical_bytes(row))
        identity = {
            "v1_unresolved_row_sha256": row_sha,
            "hff_ids": [item["id"] for item in terminals],
        }
        digest = sha256_bytes(canonical_bytes(identity))
        records.append(
            {
                "compiler_function": {
                    "name": row["function"],
                    "return_type": signature["return_type"],
                    "signature": signature["compiler_signature"],
                    "ssa_statement_range": function["statement_range"],
                },
                "id": "HFC3-" + digest[:24].upper(),
                "module": inputs["sources"][row["source"]]["module"],
                "semantic_disposition": {
                    "domain_kind": (
                        "compiler_numeric_interval_observed" if intervals else "compiler_domain_unbounded"
                    ),
                    "proof_inputs": [
                        "gcc-original", "gcc-gimple", "gcc-ssa", "gcc-evrp", "gcc-vrp"
                    ],
                    "proof_kind": "structural_compiler_evidence_only",
                    "status": "requires_semantic_oracle",
                },
                "source": row["source"],
                "terminals": terminal_records,
                "v1_unresolved_row": row,
                "v1_unresolved_row_sha256": row_sha,
                "value_domain": {
                    "intervals": intervals,
                    "negative_numeric_values_are_not_semantic_errno_proof": True,
                },
            }
        )
    return sorted(records, key=lambda item: item["id"])


MIR_SPAN = re.compile(
    r"\bat\s+(?P<path>[^\s:][^:]*\.rs):(?P<sl>[0-9]+):(?P<sc>[0-9]+):\s*"
    r"(?P<el>[0-9]+):(?P<ec>[0-9]+)"
)
MIR_BLOCK = re.compile(r"^\s*bb(?P<number>[0-9]+)(?:\s*\([^)]*\))?\s*:\s*\{", re.MULTILINE)
MIR_OWNER = re.compile(
    r"^\s*(?:fn|const|static)\s+(?P<name>.+?)(?:\(|:).*?\{",
    re.MULTILINE,
)
MIR_SCOPE_SPAN = re.compile(
    r"scope\s+(?P<scope>[0-9]+).*?\bat\s+(?P<path>[^\s:][^:]*\.rs):"
    r"(?P<sl>[0-9]+):(?P<sc>[0-9]+):\s*(?P<el>[0-9]+):(?P<ec>[0-9]+)"
)


def span_record(match):
    return {
        "end_column": int(match.group("ec")),
        "end_line": int(match.group("el")),
        "path": match.group("path"),
        "start_column": int(match.group("sc")),
        "start_line": int(match.group("sl")),
    }


def mir_terminator(block_text):
    significant = []
    for line in block_text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("//"):
            significant.append(stripped)
    joined = " ".join(significant)
    kinds = (
        ("switchInt", "switch_int"),
        ("goto ->", "goto"),
        ("return;", "return"),
        ("resume;", "resume"),
        ("abort;", "abort"),
        ("unreachable;", "unreachable"),
        ("terminate(", "terminate"),
        ("drop(", "drop"),
        ("assert(", "assert"),
        ("yield(", "yield"),
        ("falseEdge", "false_edge"),
        ("falseUnwind", "false_unwind"),
        ("inline asm", "inline_asm"),
        ("tailcall", "tail_call"),
        ("coroutine_drop", "coroutine_drop"),
        ("unwind resume", "unwind_resume"),
        ("unwind terminate", "unwind_terminate"),
    )
    kind = None
    for spelling, candidate in kinds:
        if spelling in joined:
            kind = candidate
            break
    if kind is None and " -> [" in joined and re.search(r"\bbb[0-9]+\b", joined):
        kind = "call"
    if kind is None:
        raise SemanticsV3Error("unknown or missing MIR terminator grammar")
    successors = sorted(set(int(value) for value in re.findall(r"\bbb([0-9]+)\b", joined)))
    return kind, successors, joined


def parse_mir_body(data, compiler_path):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SemanticsV3Error("Rust MIR is not UTF-8: {0}".format(exc))
    owner_matches = list(MIR_OWNER.finditer(text))
    if len(owner_matches) != 1:
        raise SemanticsV3Error("Rust MIR body has no unique owner")
    owner_match = owner_matches[0]
    blocks = list(MIR_BLOCK.finditer(text))
    if not blocks or blocks[0].group("number") != "0":
        raise SemanticsV3Error("Rust MIR body has no bb0 entry")
    block_records = {}
    scope_spans = {}
    for match in MIR_SCOPE_SPAN.finditer(text):
        scope_spans.setdefault(int(match.group("scope")), []).append(span_record(match))
    for index, match in enumerate(blocks):
        number = int(match.group("number"))
        if number in block_records:
            raise SemanticsV3Error("Rust MIR basic blocks are duplicated")
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
        block_text = text[match.end():end]
        kind, successors, terminator = mir_terminator(block_text)
        spans = [span_record(item) for item in MIR_SPAN.finditer(block_text)]
        for scope in set(int(value) for value in re.findall(r"\bscope\s+([0-9]+)\b", block_text)):
            spans.extend(scope_spans.get(scope, []))
        spans = sorted(
            {canonical_bytes(item): item for item in spans}.values(), key=canonical_bytes
        )
        block_records[number] = {
            "number": number,
            "spans": spans,
            "successors": successors,
            "terminator_kind": kind,
            "terminator_sha256": sha256_bytes(terminator.encode("utf-8")),
            "text": block_text,
        }
    for block in block_records.values():
        if any(successor not in block_records for successor in block["successors"]):
            raise SemanticsV3Error("Rust MIR terminator names an unknown basic block")
    reachable = set()
    pending = deque([0])
    while pending:
        number = pending.popleft()
        if number in reachable:
            continue
        reachable.add(number)
        pending.extend(block_records[number]["successors"])
    cfg = [
        {
            "number": number,
            "successors": block_records[number]["successors"],
            "terminator_kind": block_records[number]["terminator_kind"],
        }
        for number in sorted(block_records)
    ]
    return {
        "body_id": compiler_path,
        "cfg_sha256": sha256_bytes(canonical_bytes(cfg)),
        "owner": owner_match.group("name"),
        "blocks": block_records,
        "reachable": reachable,
        "stage": Path(compiler_path).name,
    }


def span_contains(span, line, column, end_column):
    if line < span["start_line"] or line > span["end_line"]:
        return False
    if line == span["start_line"] and column < span["start_column"]:
        return False
    if line == span["end_line"] and end_column > span["end_column"]:
        return False
    return True


def span_equals_token(span, line, column, end_column):
    return (
        span["start_line"] == line
        and span["end_line"] == line
        and span["start_column"] == column
        and span["end_column"] == end_column
    )


def errno_constants(source_data):
    try:
        text = source_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SemanticsV3Error("Rust source is not UTF-8: {0}".format(exc))
    constants = {}
    pattern = re.compile(
        r"^\s*const\s+(E[A-Z0-9_]+)\s*:\s*c_(?:int|long)\s*=\s*([0-9]+)\s*;",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        name = match.group(1)
        if name in constants:
            raise SemanticsV3Error("Rust errno constant is duplicated")
        constants[name] = int(match.group(2))
    return constants


def stage_is_optimized(stage):
    lowered = stage.lower()
    return any(word in lowered for word in ("runtime-optimized", "optimized", "simplifycfg-final"))


def mir_contains_negative_errno(block_text, value):
    semantic_text = "\n".join(
        line.split("//", 1)[0] for line in block_text.splitlines()
    )
    literal = re.compile(r"-\s*{0}(?:_|\b)".format(value))
    unary = re.compile(
        r"\bNeg\s*\(\s*const\s+{0}(?:_|\b)".format(value)
    )
    return bool(literal.search(semantic_text) or unary.search(semantic_text))


def analyze_rust_sites(inputs, invocation, payloads, repo):
    rust_source = invocation["source"]
    source_path = Path(repo) / rust_source
    source_data = read_regular_bytes(source_path, "Rust semantic source", MAX_RAW_MEMBER_BYTES)
    if sha256_bytes(source_data) != EXPECTED_RUST["source_sha256"]:
        raise SemanticsV3Error("Rust semantic source bytes differ from pinned HFS")
    constants = errno_constants(source_data)
    sites_input = sorted(
        [item for item in inputs["hfs"]["failure_sites"] if item["language"] == "rust"],
        key=lambda item: item["id"],
    )
    if (
        len(sites_input) != EXPECTED_RUST_SITE_COUNT
        or len({item["id"] for item in sites_input}) != EXPECTED_RUST_SITE_COUNT
        or len({item["line"] for item in sites_input}) != EXPECTED_RUST_SITE_COUNT
    ):
        raise SemanticsV3Error("immutable Rust HFS site/line closure changed")
    bodies = []
    for binding in invocation["mir_files"]:
        data = validate_file_binding(binding, payloads, "Rust MIR", {"compiler_path"})
        bodies.append(parse_mir_body(data, binding["compiler_path"]))
    records = []
    source_lines = source_data.decode("utf-8").splitlines()
    for site in sites_input:
        value = constants.get(site["errno"])
        if value is None or value <= 0:
            raise SemanticsV3Error("Rust HFS errno has no positive source constant")
        line_text = source_lines[site["line"] - 1]
        start = site["column"] - 1
        end = site["end_column"] - 1
        if start < 0 or end <= start or line_text[start:end] != site["expression"]:
            raise SemanticsV3Error("Rust HFS token span differs from exact source")
        candidates = []
        for body in bodies:
            for number, block in body["blocks"].items():
                if (
                    number not in body["reachable"]
                    or not mir_contains_negative_errno(block["text"], value)
                ):
                    continue
                for span in block["spans"]:
                    normalized_path = span["path"].replace("\\", "/")
                    if not normalized_path.endswith("/" + rust_source):
                        continue
                    if not span_equals_token(
                        span, site["line"], site["column"], site["end_column"]
                    ):
                        continue
                    candidates.append(
                        {
                            "basic_block": number,
                            "body_id": body["body_id"],
                            "cfg_sha256": body["cfg_sha256"],
                            "errno_negative_value": -value,
                            "mir_span": span,
                            "owner": body["owner"],
                            "reachable_from_bb0": True,
                            "stage": body["stage"],
                        }
                    )
        candidates = sorted(
            {canonical_bytes(item): item for item in candidates}.values(), key=canonical_bytes
        )
        if not candidates:
            raise SemanticsV3Error("Rust HFS token has no reachable MIR errno mapping")
        unoptimized = [item for item in candidates if not stage_is_optimized(item["stage"])]
        if len(unoptimized) == 1:
            mapping_status = "unique_structural_mapping_semantics_unresolved"
        elif unoptimized:
            mapping_status = "multiple_unoptimized_mappings_semantics_unresolved"
        else:
            mapping_status = "optimized_only_mapping_semantics_unresolved"
        identity = {
            "hfs_id": site["id"],
            "source_sha256": site["source_sha256"],
            "token_span": {
                "column": site["column"], "end_column": site["end_column"], "line": site["line"]
            },
        }
        digest = sha256_bytes(canonical_bytes(identity))
        records.append(
            {
                "candidates": candidates,
                "errno": site["errno"],
                "errno_negative_value": -value,
                "hfs_id": site["id"],
                "id": "HFR3-" + digest[:24].upper(),
                "mapping_status": mapping_status,
                "semantic_status": "requires_semantic_oracle",
                "source": rust_source,
                "token_span": {
                    "column": site["column"],
                    "end_column": site["end_column"],
                    "line": site["line"],
                    "source_sha256": site["source_sha256"],
                },
            }
        )
    return records, bodies


def build_capture(
    repo,
    failure_site_path,
    failure_flow_v1_path,
    failure_flow_v2_path,
    raw_bundle_path,
    raw_bundle_sha256_path,
    build_dir=None,
    kernel_dir=None,
    historical_ef58=False,
    repository_authority=None,
):
    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise SemanticsV3Error("repository root does not exist")
    inputs = load_inputs(
        repo, failure_site_path, failure_flow_v1_path, failure_flow_v2_path,
        build_dir, kernel_dir, historical_ef58, repository_authority,
    )
    manifest, payloads, raw_record = read_raw_bundle(
        raw_bundle_path, raw_bundle_sha256_path
    )
    invocations = validate_raw_manifest(manifest, payloads, inputs)
    effective_build = Path(build_dir or repo).resolve()
    effective_kernel = Path(kernel_dir or repo).resolve()
    c_contracts = analyze_c_contracts(
        inputs, invocations, payloads, repo, effective_build, effective_kernel
    )
    rust_invocations = [item for item in invocations.values() if item["language"] == "rust"]
    if len(rust_invocations) != 1:
        raise SemanticsV3Error("raw Rust invocation closure changed")
    rust_sites, rust_bodies = analyze_rust_sites(
        inputs, rust_invocations[0], payloads, repo
    )
    c_status = Counter(item["semantic_disposition"]["status"] for item in c_contracts)
    c_modules = Counter(item["module"] for item in c_contracts)
    rust_status = Counter(item["mapping_status"] for item in rust_sites)
    coverage = {
        "c_function_count": len({(item["source"], item["compiler_function"]["name"]) for item in c_contracts}),
        "c_return_contract_count": len(c_contracts),
        "c_return_contract_count_by_module": dict(sorted(c_modules.items())),
        "c_return_contract_count_by_status": dict(sorted(c_status.items())),
        "c_source_count": len({item["source"] for item in c_contracts}),
        "c_terminal_count": sum(len(item["terminals"]) for item in c_contracts),
        "rust_mir_body_count": len(rust_bodies),
        "rust_mir_site_count": len(rust_sites),
        "rust_mir_site_count_by_mapping_status": dict(sorted(rust_status.items())),
        "semantic_error_domain_resolved_count": 0,
        "tracker_credit_count": 0,
    }
    if (
        coverage["c_function_count"] != EXPECTED_C_FUNCTION_COUNT
        or coverage["c_return_contract_count"] != EXPECTED_C_ROW_COUNT
        or coverage["c_return_contract_count_by_module"] != EXPECTED_C_ROWS_BY_MODULE
        or coverage["c_source_count"] != EXPECTED_C_SOURCE_COUNT
        or coverage["c_terminal_count"] != EXPECTED_C_TERMINAL_COUNT
        or coverage["rust_mir_site_count"] != EXPECTED_RUST_SITE_COUNT
    ):
        raise SemanticsV3Error("v3 structural coverage closure changed")
    result = {
        "analysis_claim": dict(ANALYSIS_CLAIM),
        "authority_mode": inputs["authority_mode"],
        "blockers": list(BLOCKERS),
        "c_return_contracts": c_contracts,
        "compiler_invocations": manifest["compiler_invocations"],
        "coverage": coverage,
        "generator": "scripts/host_module_failure_semantics_v3.py",
        "inputs": manifest_input_bindings(inputs),
        "profile": PROFILE,
        "raw_bundle": raw_record,
        "rust_mir_sites": rust_sites,
        "schema_version": SCHEMA_VERSION,
        "toolchains": manifest["toolchains"],
    }
    validate_semantics_output_schema(result)
    if repository_authority is not None:
        try:
            sites.recheck_repository_authority(repo, repository_authority)
        except sites.CaptureError as exc:
            raise SemanticsV3Error("fresh authority changed during v3: {0}".format(exc))
    return result


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--kernel-dir", type=Path)
    parser.add_argument("--failure-sites", type=Path, required=True)
    parser.add_argument("--failure-flows-v1", type=Path, required=True)
    parser.add_argument("--failure-flows-v2", type=Path, required=True)
    parser.add_argument("--raw-bundle", type=Path)
    parser.add_argument("--raw-bundle-sha256", type=Path)
    parser.add_argument("--capture-raw", action="store_true")
    parser.add_argument("--historical-ef58", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.capture_raw:
        if args.historical_ef58:
            parser.error("--capture-raw is fresh-only")
        if args.raw_bundle is None or args.raw_bundle_sha256 is None:
            parser.error("--capture-raw requires raw bundle and checksum output paths")
    elif args.raw_bundle is None or args.raw_bundle_sha256 is None:
        parser.error("raw bundle and checksum inputs are required")
    if not args.historical_ef58 and (args.build_dir is None or args.kernel_dir is None):
        parser.error("fresh mode requires --build-dir and --kernel-dir")
    return args


def main(argv=None, repository_authority=None):
    args = parse_args(argv or sys.argv[1:])
    try:
        if not args.historical_ef58 and repository_authority is None:
            raise SemanticsV3Error("fresh CLI requires isolated repository authority")
        inputs = None
        if args.capture_raw:
            inputs = load_inputs(
                args.repo, args.failure_sites, args.failure_flows_v1,
                args.failure_flows_v2, args.build_dir, args.kernel_dir,
                False, repository_authority,
            )
            capture_raw_bundle(
                inputs, args.repo, args.build_dir, args.kernel_dir,
                args.raw_bundle, args.raw_bundle_sha256,
            )
        capture = build_capture(
            args.repo, args.failure_sites, args.failure_flows_v1,
            args.failure_flows_v2, args.raw_bundle, args.raw_bundle_sha256,
            args.build_dir, args.kernel_dir, args.historical_ef58,
            repository_authority,
        )
        atomic_write(
            args.output,
            (json.dumps(capture, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    except SemanticsV3Error as exc:
        print("host-module failure semantics v3 failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(
        "recorded {0} C semantic questions and {1} Rust MIR sites; FP-0006 remains IN_PROGRESS".format(
            capture["coverage"]["c_return_contract_count"],
            capture["coverage"]["rust_mir_site_count"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
