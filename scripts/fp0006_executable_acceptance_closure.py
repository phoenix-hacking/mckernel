#!/usr/bin/env python3
"""Census the still-incomplete executable acceptance surface for FP-0006.

This checker deliberately separates declarations from results.  It can prove
the exact committed 1,326 behavior/acceptance declarations and can recognize
the frozen identities of the historical compiler-site and failure-flow
artifacts.  It cannot manufacture the absent semantic or runtime authorities,
so every completion, execution, review, durability, gate, tracker, and credit
claim remains false.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = "host-kernel/contracts/fp0006-executable-acceptance-closure-v1.json"
EXPECTED_CONTRACT_SHA256 = "17e0e3fd73befbc56809f4235f0630436e0a154a5ade23e17f5f27232f2cf928"
EXPECTED_CONTRACT_SIZE = 5938
MAX_INPUT_SIZE = 32 * 1024 * 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HFS_ID = re.compile(r"^HFS-[0-9A-F]{24}$")
HFF_ID = re.compile(r"^HFF-[0-9A-F]{24}$")


class ClosureError(RuntimeError):
    """Raised when any authority or noncrediting boundary changes."""


def canonical_bytes(value):
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def pretty_bytes(value):
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def strict_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            strict_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ClosureError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def load_json(data, label):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ClosureError("{0} is not UTF-8: {1}".format(label, error))
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ClosureError(
                    "{0} contains non-finite JSON: {1}".format(label, value)
                )
            ),
        )
    except ClosureError:
        raise
    except (TypeError, ValueError) as error:
        raise ClosureError("{0} is not valid JSON: {1}".format(label, error))


def require_keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ClosureError("{0} keys differ".format(label))
    return value


def require_string(value, label):
    if type(value) is not str or not value or "\0" in value:
        raise ClosureError("{0} must be an exact non-empty string".format(label))
    return value


def require_int(value, label, minimum=None):
    if type(value) is not int:
        raise ClosureError("{0} must be an exact integer".format(label))
    if minimum is not None and value < minimum:
        raise ClosureError("{0} is below its minimum".format(label))
    return value


def require_false(value, label):
    if type(value) is not bool or value is not False:
        raise ClosureError("{0} must remain the exact boolean false".format(label))
    return value


def require_digest(value, label):
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise ClosureError("{0} is not a lowercase SHA-256".format(label))
    return value


def _identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1000000000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1000000000)),
    )


def _relative_parts(path, label):
    if type(path) is not str or not path or "\0" in path or "\\" in path:
        raise ClosureError("{0} path must be an exact repository-relative string".format(label))
    candidate = Path(path)
    if candidate.is_absolute():
        raise ClosureError("{0} path must be repository-relative".format(label))
    parts = candidate.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ClosureError("{0} path has a forbidden component".format(label))
    return parts


def _open_directory_no_follow(path):
    """Open an absolute directory without following any path component."""

    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ClosureError("no-follow directory traversal is unavailable")
    absolute = os.path.abspath(str(path))
    parts = Path(absolute).parts
    if not parts or parts[0] != "/":
        raise ClosureError("repository root is not absolute")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open("/", flags)
    try:
        for component in parts[1:]:
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise ClosureError("repository root is not a directory")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


class SealedInput(object):
    def __init__(self, path, descriptor, metadata, data):
        self.path = path
        self.descriptor = descriptor
        self.identity = _identity(metadata)
        self.data = data


class RepositorySnapshot(object):
    """Retain every input descriptor through the aggregate decision."""

    def __init__(self, root):
        self.root = os.path.abspath(str(root))
        self.root_descriptor = _open_directory_no_follow(self.root)
        self.inputs = []
        self.closed = False

    def _open_relative(self, path, label):
        parts = _relative_parts(path, label)
        directory = os.dup(self.root_descriptor)
        file_descriptor = None
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory_flags |= getattr(os, "O_CLOEXEC", 0)
        file_flags = os.O_RDONLY | os.O_NOFOLLOW
        file_flags |= getattr(os, "O_CLOEXEC", 0)
        try:
            for component in parts[:-1]:
                next_directory = os.open(
                    component, directory_flags, dir_fd=directory
                )
                os.close(directory)
                directory = next_directory
            file_descriptor = os.open(parts[-1], file_flags, dir_fd=directory)
            metadata = os.fstat(file_descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ClosureError("{0} must be a regular file".format(label))
            if metadata.st_nlink != 1:
                raise ClosureError("{0} must not be hard-linked".format(label))
            return file_descriptor, metadata
        except Exception as error:
            if file_descriptor is not None:
                os.close(file_descriptor)
            if isinstance(error, OSError):
                raise ClosureError(
                    "cannot open {0} without following links: {1}".format(label, error)
                )
            raise
        finally:
            os.close(directory)

    def read(self, path, label, maximum=MAX_INPUT_SIZE):
        if self.closed:
            raise ClosureError("repository snapshot is closed")
        require_int(maximum, label + " maximum", 1)
        descriptor, before = self._open_relative(path, label)
        try:
            if before.st_size < 1 or before.st_size > maximum:
                raise ClosureError("{0} size is outside its bound".format(label))
            chunks = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    raise ClosureError("{0} ended before its retained size".format(label))
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                raise ClosureError("{0} grew beyond its retained size".format(label))
            after = os.fstat(descriptor)
            if _identity(before) != _identity(after):
                raise ClosureError("{0} changed while being read".format(label))
            sealed = SealedInput(path, descriptor, before, b"".join(chunks))
            self.inputs.append(sealed)
            return sealed
        except Exception:
            os.close(descriptor)
            raise

    def _current_path_identity(self, item):
        descriptor, metadata = self._open_relative(item.path, item.path)
        try:
            return _identity(metadata)
        finally:
            os.close(descriptor)

    def finalize(self):
        if self.closed:
            raise ClosureError("repository snapshot is closed")
        for item in self.inputs:
            retained = os.fstat(item.descriptor)
            if _identity(retained) != item.identity:
                raise ClosureError("{0} changed before aggregate decision".format(item.path))
            if self._current_path_identity(item) != item.identity:
                raise ClosureError("{0} path identity changed before decision".format(item.path))

    def close(self):
        if not self.closed:
            for item in self.inputs:
                try:
                    os.close(item.descriptor)
                except OSError:
                    pass
            os.close(self.root_descriptor)
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _read_exact(snapshot, metadata, label):
    require_keys(metadata, {"path", "sha256", "size"}, label + " metadata")
    path = require_string(metadata["path"], label + " path")
    expected_size = require_int(metadata["size"], label + " size", 1)
    expected_sha = require_digest(metadata["sha256"], label + " sha256")
    sealed = snapshot.read(path, label, min(MAX_INPUT_SIZE, expected_size))
    if len(sealed.data) != expected_size:
        raise ClosureError("{0} byte size changed".format(label))
    if sha256_bytes(sealed.data) != expected_sha:
        raise ClosureError("{0} SHA-256 changed".format(label))
    return sealed.data


def _false_claims():
    return {
        "credit_eligible": False,
        "durable": False,
        "executable_acceptance_complete": False,
        "executable_results_present": False,
        "fp0006_complete": False,
        "full_census_join_complete": False,
        "gate_pass": False,
        "independent_review_complete": False,
        "legacy_runtime_executed": False,
        "native_runtime_executed": False,
        "runtime_reachability_proven": False,
        "tracker_credit": False,
    }


def validate_contract(contract, _claims_factory=_false_claims):
    require_keys(
        contract,
        {
            "census_policy",
            "claims",
            "contract_id",
            "expected_census",
            "frozen_inputs",
            "gate",
            "required_missing",
            "schema_version",
        },
        "closure contract",
    )
    if type(contract["schema_version"]) is not int or contract["schema_version"] != 1:
        raise ClosureError("closure schema version changed")
    if contract["contract_id"] != "fp-0006-executable-acceptance-closure-v1":
        raise ClosureError("closure contract identity changed")
    expected_policy = {
        "absent_rows_may_be_synthesized": False,
        "declarative_acceptance_ids_are_executed_results": False,
        "exact_external_identity_required_before_parsing": True,
        "incomplete_sets_force_noncrediting_result": True,
        "runtime_result_authority_required": True,
    }
    if not strict_equal(contract["census_policy"], expected_policy):
        raise ClosureError("closure census policy changed")
    if not strict_equal(contract["claims"], _claims_factory()):
        raise ClosureError("closure contract claims must all remain false")
    expected_census = {
        "acceptance_test_declaration_count": 1326,
        "behavior_declaration_count": 1326,
        "bounded_failure_flow_count": 2602,
        "c_semantic_question_count": 205,
        "compiler_failure_site_count": 971,
        "declarative_behavior_acceptance_join": "complete",
        "direct_strong_same_module_ctu_structural_inventory_status": (
            "required-missing"
        ),
        "executable_result_count": 0,
        "full_cross_authority_join": "required-missing",
        "rust_mir_site_count": 420,
    }
    if not strict_equal(contract["expected_census"], expected_census):
        raise ClosureError("closure expected census changed")
    if not strict_equal(
        contract["gate"],
        {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
    ):
        raise ClosureError("FP-0006 gate boundary changed")
    expected_missing = [
        "bounded_failure_flow_rows",
        "compiler_failure_site_rows",
        "direct_strong_same_module_ctu_structural_inventory",
        "durable_runtime_result_authority",
        "independent_runtime_result_review",
        "runtime_result_rows",
        "semantic_c_question_rows",
        "semantic_rust_mir_rows",
        "semantic_v3_independent_review",
    ]
    if not strict_equal(contract["required_missing"], expected_missing):
        raise ClosureError("required-missing closure changed")
    inputs = require_keys(
        contract["frozen_inputs"],
        {
            "bounded_failure_flow_authority",
            "compiler_failure_site_authority",
            "legacy_behavior_authority",
            "negative_dispatch_reference",
            "runtime_capture_reference",
            "semantic_evidence_authority",
        },
        "frozen inputs",
    )
    legacy = require_keys(
        inputs["legacy_behavior_authority"],
        {
            "acceptance_id_set_sha256",
            "acceptance_module_id_set_sha256",
            "acceptance_reverse_edge_set_sha256",
            "acceptance_test_count",
            "artifact_availability",
            "behavior_count",
            "behavior_edge_set_sha256",
            "behavior_id_set_sha256",
            "behavior_module_id_set_sha256",
            "behavior_test_edge_count",
            "path",
            "profile",
            "sha256",
            "size",
        },
        "legacy behavior authority metadata",
    )
    if (
        legacy["artifact_availability"] != "committed"
        or legacy["profile"] != "rocky-8.10-x86_64-rust-helper-reference"
        or type(legacy["behavior_count"]) is not int
        or legacy["behavior_count"] != 1326
        or type(legacy["acceptance_test_count"]) is not int
        or legacy["acceptance_test_count"] != 1326
        or type(legacy["behavior_test_edge_count"]) is not int
        or legacy["behavior_test_edge_count"] != 1326
    ):
        raise ClosureError("legacy behavior authority metadata changed")
    require_string(legacy["path"], "legacy authority path")
    require_digest(legacy["sha256"], "legacy authority digest")
    require_int(legacy["size"], "legacy authority size", 1)
    for field in (
        "acceptance_id_set_sha256",
        "acceptance_module_id_set_sha256",
        "acceptance_reverse_edge_set_sha256",
        "behavior_edge_set_sha256",
        "behavior_id_set_sha256",
        "behavior_module_id_set_sha256",
    ):
        require_digest(legacy[field], "legacy " + field)
    for name in ("bounded_failure_flow_authority", "compiler_failure_site_authority"):
        record = inputs[name]
        require_keys(
            record,
            {
                "artifact_availability",
                "path",
                "profile",
                "repository_commit",
                "row_count",
                "sha256",
                "size",
            },
            name,
        )
        if record["artifact_availability"] != "required-missing":
            raise ClosureError("{0} availability overclaims".format(name))
        require_string(record["path"], name + " path")
        require_string(record["profile"], name + " profile")
        require_digest(record["sha256"], name + " digest")
        require_int(record["size"], name + " size", 1)
        require_int(record["row_count"], name + " row count", 1)
    for name, vector_count, surface_count in (
        ("negative_dispatch_reference", 2, None),
        ("runtime_capture_reference", 2, 2),
    ):
        record = inputs[name]
        expected_keys = {
            "path",
            "result_authority_path",
            "result_authority_status",
            "sha256",
            "size",
            "vector_count",
        }
        if surface_count is not None:
            expected_keys.add("surface_count")
        require_keys(record, expected_keys, name)
        if (
            record["result_authority_path"] is not None
            or record["result_authority_status"] != "required-missing"
            or type(record["vector_count"]) is not int
            or record["vector_count"] != vector_count
        ):
            raise ClosureError("{0} result boundary changed".format(name))
        if surface_count is not None and (
            type(record["surface_count"]) is not int
            or record["surface_count"] != surface_count
        ):
            raise ClosureError("runtime surface reference count changed")
        require_string(record["path"], name + " path")
        require_digest(record["sha256"], name + " digest")
        require_int(record["size"], name + " size", 1)
    semantics = inputs["semantic_evidence_authority"]
    require_keys(
        semantics,
        {
            "artifact",
            "direct_ctu_structural_inventory",
            "generator",
            "independent_review_artifact",
            "independent_review_generator",
            "profile",
        },
        "semantic evidence authority",
    )
    artifact = require_keys(
        semantics["artifact"],
        {
            "artifact_availability",
            "c_semantic_question_count",
            "path",
            "rust_mir_site_count",
            "sha256",
            "size",
        },
        "semantic artifact",
    )
    review_artifact = require_keys(
        semantics["independent_review_artifact"],
        {"artifact_availability", "path", "sha256", "size"},
        "semantic review artifact",
    )
    direct_ctu = require_keys(
        semantics["direct_ctu_structural_inventory"],
        {
            "artifact_availability",
            "blocker_retained",
            "fresh_execution_authority",
            "inventory_kind",
            "status",
        },
        "semantic direct CTU structural inventory",
    )
    expected_direct_ctu = {
        "artifact_availability": "required-missing",
        "blocker_retained": "cross_translation_unit_call_graph_not_linked",
        "fresh_execution_authority": False,
        "inventory_kind": (
            "gcc_initial_ipa_cgraph_direct_strong_same_module_cross_tu_"
            "structural_inventory"
        ),
        "status": "required-missing",
    }
    if not strict_equal(direct_ctu, expected_direct_ctu):
        raise ClosureError("semantic direct CTU structural inventory changed")
    for name, record in (("artifact", artifact), ("independent review", review_artifact)):
        if record["artifact_availability"] != "required-missing":
            raise ClosureError("semantic {0} availability overclaims".format(name))
        if record["sha256"] is not None or record["size"] is not None:
            raise ClosureError("semantic {0} unexpectedly has result identity".format(name))
        require_string(record["path"], "semantic {0} path".format(name))
    if (
        type(artifact["c_semantic_question_count"]) is not int
        or artifact["c_semantic_question_count"] != 205
        or type(artifact["rust_mir_site_count"]) is not int
        or artifact["rust_mir_site_count"] != 420
    ):
        raise ClosureError("semantic row reference counts changed")
    for name in ("generator", "independent_review_generator"):
        record = semantics[name]
        require_keys(record, {"path", "sha256", "size"}, "semantic " + name)
        require_string(record["path"], "semantic " + name + " path")
        require_digest(record["sha256"], "semantic " + name + " digest")
        require_int(record["size"], "semantic " + name + " size", 1)
    if semantics["profile"] != "compiler-backed-host-module-failure-semantics-v3":
        raise ClosureError("semantic evidence profile changed")
    for claim_name, claim_value in contract["claims"].items():
        require_false(claim_value, "contract claim " + claim_name)
    return inputs


def _id_set_digest(values):
    return sha256_bytes(canonical_bytes(sorted(values)))


def _pair_set_digest(values):
    return sha256_bytes(canonical_bytes(sorted([list(value) for value in values])))


def validate_legacy_authority(document, metadata):
    require_keys(
        document,
        {
            "acceptance_tests",
            "behaviors",
            "comparison_profiles",
            "coverage",
            "failure_mapping",
            "generator",
            "inventory_file_sha256",
            "inventory_profile",
            "policy_file_sha256",
            "policy_id",
            "provenance",
            "schema_version",
        },
        "legacy behavior authority",
    )
    behaviors = document["behaviors"]
    tests = document["acceptance_tests"]
    if document["inventory_profile"] != metadata["profile"]:
        raise ClosureError("legacy inventory profile changed")
    if type(behaviors) is not list or type(tests) is not list:
        raise ClosureError("legacy behavior/test declarations must be lists")
    expected_behavior_count = require_int(metadata["behavior_count"], "behavior count", 1)
    expected_test_count = require_int(metadata["acceptance_test_count"], "test count", 1)
    if len(behaviors) != expected_behavior_count or len(tests) != expected_test_count:
        raise ClosureError("legacy behavior/test declaration count changed")

    behavior_ids = []
    behavior_modules = []
    behavior_edges = []
    behavior_by_id = {}
    for index, record in enumerate(behaviors):
        require_keys(
            record,
            {
                "acceptance_test_ids",
                "id",
                "kind",
                "legacy",
                "module",
                "oracle_path",
                "rust_replacement",
            },
            "behavior[{0}]".format(index),
        )
        identifier = require_string(record["id"], "behavior id")
        if not identifier.startswith("BHV-") or identifier in behavior_by_id:
            raise ClosureError("behavior ID is malformed or duplicated")
        module = require_string(record["module"], "behavior module")
        links = record["acceptance_test_ids"]
        if type(links) is not list or not links:
            raise ClosureError("behavior acceptance links are missing")
        if len(links) != len(set(links)):
            raise ClosureError("behavior acceptance links are duplicated")
        for acceptance_id in links:
            require_string(acceptance_id, "behavior acceptance ID")
            behavior_edges.append((identifier, acceptance_id))
        behavior_ids.append(identifier)
        behavior_modules.append((module, identifier))
        behavior_by_id[identifier] = record

    test_ids = []
    test_modules = []
    reverse_edges = []
    join_edges = []
    test_by_id = {}
    for index, record in enumerate(tests):
        require_keys(
            record,
            {"assertions", "behavior_ids", "gate_targets", "harness", "id", "module"},
            "acceptance_test[{0}]".format(index),
        )
        identifier = require_string(record["id"], "acceptance test id")
        if not identifier.startswith("AT-") or identifier in test_by_id:
            raise ClosureError("acceptance test ID is malformed or duplicated")
        module = require_string(record["module"], "acceptance test module")
        links = record["behavior_ids"]
        if type(links) is not list or not links or len(links) != len(set(links)):
            raise ClosureError("acceptance behavior links are missing or duplicated")
        for behavior_id in links:
            require_string(behavior_id, "acceptance behavior ID")
            reverse_edges.append((identifier, behavior_id))
            join_edges.append((behavior_id, identifier))
        test_ids.append(identifier)
        test_modules.append((module, identifier))
        test_by_id[identifier] = record

    if set(behavior_edges) != set(join_edges):
        raise ClosureError("behavior and acceptance declaration edges do not join")
    for behavior_id, acceptance_id in behavior_edges:
        if behavior_id not in behavior_by_id or acceptance_id not in test_by_id:
            raise ClosureError("behavior/acceptance edge names an unknown declaration")
        if behavior_by_id[behavior_id]["module"] != test_by_id[acceptance_id]["module"]:
            raise ClosureError("behavior/acceptance edge crosses modules")
    if len(behavior_edges) != require_int(
        metadata["behavior_test_edge_count"], "behavior edge count", 1
    ):
        raise ClosureError("behavior/acceptance edge count changed")

    observed = {
        "acceptance_id_set_sha256": _id_set_digest(test_ids),
        "acceptance_module_id_set_sha256": _pair_set_digest(test_modules),
        "acceptance_reverse_edge_set_sha256": _pair_set_digest(reverse_edges),
        "behavior_edge_set_sha256": _pair_set_digest(behavior_edges),
        "behavior_id_set_sha256": _id_set_digest(behavior_ids),
        "behavior_module_id_set_sha256": _pair_set_digest(behavior_modules),
    }
    for field, value in observed.items():
        if value != metadata[field]:
            raise ClosureError("legacy {0} changed".format(field))
    coverage = document["coverage"]
    if type(coverage) is not dict:
        raise ClosureError("legacy coverage is missing")
    if (
        type(coverage.get("behavior_count")) is not int
        or coverage["behavior_count"] != expected_behavior_count
        or type(coverage.get("test_count")) is not int
        or coverage["test_count"] != expected_test_count
    ):
        raise ClosureError("legacy coverage counts changed")
    return {
        "acceptance_id_set_sha256": observed["acceptance_id_set_sha256"],
        "acceptance_test_declaration_count": len(test_ids),
        "behavior_acceptance_edge_count": len(behavior_edges),
        "behavior_id_set_sha256": observed["behavior_id_set_sha256"],
        "behavior_declaration_count": len(behavior_ids),
        "declarative_join_complete": True,
        "executed_result_count": 0,
    }


def _all_claim_values_false(claims, label):
    if type(claims) is not dict or not claims:
        raise ClosureError("{0} claims are missing".format(label))
    for name, value in claims.items():
        require_false(value, "{0} claim {1}".format(label, name))


def validate_negative_reference(document, metadata, site_meta, flow_meta):
    if document.get("contract_id") != "fp-0006-ihk-device-negative-dispatch-v1":
        raise ClosureError("negative-dispatch contract identity changed")
    _all_claim_values_false(document.get("claims"), "negative-dispatch")
    if not strict_equal(
        document.get("gate"),
        {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
    ):
        raise ClosureError("negative-dispatch gate boundary changed")
    authority = document.get("artifact_contract", {}).get("result_authority")
    if not strict_equal(
        authority,
        {
            "durable_artifact_required": True,
            "independent_review_required": True,
            "path": None,
            "status": "required-missing",
        },
    ):
        raise ClosureError("negative-dispatch result authority changed")
    vectors = document.get("vectors")
    if type(vectors) is not list or len(vectors) != metadata["vector_count"]:
        raise ClosureError("negative-dispatch vector count changed")
    vector_ids = [item.get("vector_id") if type(item) is dict else None for item in vectors]
    if any(type(item) is not str for item in vector_ids) or len(set(vector_ids)) != len(vector_ids):
        raise ClosureError("negative-dispatch vector IDs are malformed")
    evidence = document.get("failure_evidence")
    if type(evidence) is not dict:
        raise ClosureError("negative-dispatch failure evidence is missing")
    site_reference = evidence.get("failure_site_authority")
    flow_reference = evidence.get("failure_flow_artifact")
    if type(site_reference) is not dict or type(flow_reference) is not dict:
        raise ClosureError("negative-dispatch external references are missing")
    expected_site = {
        "external_path_hint": site_meta["path"],
        "repository_commit": site_meta["repository_commit"],
        "sha256": site_meta["sha256"],
        "size": site_meta["size"],
        "status": "external-required-for-provenance",
    }
    if not strict_equal(site_reference, expected_site):
        raise ClosureError("negative-dispatch failure-site reference changed")
    if (
        flow_reference.get("external_path_hint") != flow_meta["path"]
        or flow_reference.get("repository_commit") != flow_meta["repository_commit"]
        or flow_reference.get("sha256") != flow_meta["sha256"]
        or type(flow_reference.get("size")) is not int
        or flow_reference.get("size") != flow_meta["size"]
        or flow_reference.get("status") != "external-required-for-provenance"
    ):
        raise ClosureError("negative-dispatch failure-flow reference changed")
    inner = flow_reference.get("input_failure_sites")
    expected_inner = {
        "artifact_bytes": site_meta["size"],
        "artifact_sha256": site_meta["sha256"],
        "profile": site_meta["profile"],
        "repository_commit": site_meta["repository_commit"],
    }
    if not strict_equal(inner, expected_inner):
        raise ClosureError("negative-dispatch flow/site binding changed")
    return vector_ids


def validate_runtime_reference(document, metadata, negative_vector_ids):
    if document.get("contract_id") != "fp-0006-runtime-capture-integration-v1":
        raise ClosureError("runtime integration contract identity changed")
    _all_claim_values_false(document.get("claims"), "runtime integration")
    if not strict_equal(
        document.get("gate"),
        {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
    ):
        raise ClosureError("runtime integration gate boundary changed")
    if not strict_equal(
        document.get("result_authority"),
        {"independent_review_required": True, "path": None, "status": "required-missing"},
    ):
        raise ClosureError("runtime result authority changed")
    vectors = document.get("vectors")
    surfaces = document.get("surfaces")
    if type(vectors) is not list or len(vectors) != metadata["vector_count"]:
        raise ClosureError("runtime vector count changed")
    if type(surfaces) is not dict or len(surfaces) != metadata["surface_count"]:
        raise ClosureError("runtime surface count changed")
    vector_ids = [item.get("vector_id") if type(item) is dict else None for item in vectors]
    if vector_ids != negative_vector_ids:
        raise ClosureError("runtime and negative-dispatch vectors no longer join")
    return {"surface_count": len(surfaces), "vector_count": len(vectors)}


def validate_semantic_sources(generator_data, review_data, metadata):
    generator_text = generator_data.decode("utf-8")
    review_text = review_data.decode("utf-8")
    c_count = metadata["artifact"]["c_semantic_question_count"]
    rust_count = metadata["artifact"]["rust_mir_site_count"]
    c_pattern = re.compile(r"^EXPECTED_C_ROW_COUNT = {0}$".format(c_count), re.MULTILINE)
    rust_pattern = re.compile(
        r"^EXPECTED_RUST_SITE_COUNT = {0}$".format(rust_count), re.MULTILINE
    )
    if len(c_pattern.findall(generator_text)) != 1 or len(rust_pattern.findall(generator_text)) != 1:
        raise ClosureError("semantic generator count authority changed")
    if "semantic_error_domains_proven\": False" not in generator_text:
        raise ClosureError("semantic generator noncrediting boundary changed")
    if "def validate_semantics" not in review_text:
        raise ClosureError("semantic independent-review generator changed")
    required_generator_markers = (
        "RAW_SCHEMA_VERSION = 2",
        '("cgraph", "-fdump-ipa-cgraph-lineno", ".cgraph")',
        'DIRECT_CTU_INVENTORY_KIND = (',
        'DIRECT_CTU_HISTORICAL_STATUS = "historical_raw_not_independently_anchored"',
        "def validate_fresh_capture_receipt",
        "def capture_continuity_diagnostic",
        "def compare_independent_fresh_captures",
        "def validate_normalized_cgraph_dump",
        '"fresh_execution_authority": False,',
        'reason = caller_record["traits"][0] + "_caller"',
        'reason = declared["traits"][0] + "_declaration"',
        '    if (\n'
        '        type_text.startswith("function definition analyzed")\n'
        '        and "external" in visibility\n'
        '    ):\n'
        '        traits.add("inline")',
    )
    required_review_markers = (
        "def independently_derive_direct_graph",
        "semantics.compare_independent_fresh_captures(",
        "independent_fresh_comparison=independent_comparison",
        '"direct_ctu_fresh_execution_authority": False,',
        '"direct_ctu_structural_match_status": (',
        '"blocked_edges": sorted(',
        'if caller["traits"]:',
        'if declared["traits"] or not declared["global"]:',
        "independent normalized cgraph retains a raw or misplaced allocator address",
        '    if (\n'
        '        type_text.startswith("function definition analyzed")\n'
        '        and "external" in visibility\n'
        '    ):\n'
        '        traits.add("inline")',
    )
    if any(
        generator_text.count(marker) != 1
        for marker in required_generator_markers
    ):
        raise ClosureError("semantic direct CTU generator marker changed")
    if any(
        review_text.count(marker) != 1 for marker in required_review_markers
    ):
        raise ClosureError("semantic direct CTU independent-review marker changed")
    return {
        "c_semantic_question_count": c_count,
        "direct_strong_same_module_ctu_structural_inventory_status": (
            metadata["direct_ctu_structural_inventory"]["status"]
        ),
        "rust_mir_site_count": rust_count,
        "semantic_rows_status": "required-missing",
        "independent_review_status": "required-missing",
    }


def _validate_external_sites(document, metadata):
    if document.get("profile") != metadata["profile"]:
        raise ClosureError("external failure-site profile changed")
    sites = document.get("failure_sites")
    coverage = document.get("coverage")
    if type(sites) is not list or type(coverage) is not dict:
        raise ClosureError("external failure-site rows are missing")
    if len(sites) != metadata["row_count"]:
        raise ClosureError("external failure-site row count changed")
    if type(coverage.get("failure_site_count")) is not int or coverage.get(
        "failure_site_count"
    ) != len(sites):
        raise ClosureError("external failure-site coverage count changed")
    identifiers = []
    for item in sites:
        identifier = item.get("id") if type(item) is dict else None
        if type(identifier) is not str or HFS_ID.fullmatch(identifier) is None:
            raise ClosureError("external failure-site ID is malformed")
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise ClosureError("external failure-site IDs are duplicated")
    return len(identifiers)


def _validate_external_flows(document, metadata, site_metadata):
    if document.get("profile") != metadata["profile"]:
        raise ClosureError("external failure-flow profile changed")
    flows = document.get("failure_flows")
    coverage = document.get("coverage")
    if type(flows) is not list or type(coverage) is not dict:
        raise ClosureError("external failure-flow rows are missing")
    if len(flows) != metadata["row_count"]:
        raise ClosureError("external failure-flow row count changed")
    if type(coverage.get("flow_count")) is not int or coverage.get("flow_count") != len(flows):
        raise ClosureError("external failure-flow coverage count changed")
    binding = document.get("input_failure_sites")
    expected_binding = {
        "artifact_bytes": site_metadata["size"],
        "artifact_sha256": site_metadata["sha256"],
        "profile": site_metadata["profile"],
        "repository_commit": site_metadata["repository_commit"],
    }
    if not strict_equal(binding, expected_binding):
        raise ClosureError("external flow/site authority binding changed")
    identifiers = []
    for item in flows:
        identifier = item.get("id") if type(item) is dict else None
        if type(identifier) is not str or HFF_ID.fullmatch(identifier) is None:
            raise ClosureError("external failure-flow ID is malformed")
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise ClosureError("external failure-flow IDs are duplicated")
    return len(identifiers)


def _present_external(snapshot, supplied_path, metadata, label, validator):
    if supplied_path is None:
        return {"presentation": "not-presented", "reference_status": "required-missing"}
    if type(supplied_path) is not str or supplied_path != metadata["path"]:
        raise ClosureError("{0} must use its exact frozen path".format(label))
    data = _read_exact(
        snapshot,
        {"path": metadata["path"], "sha256": metadata["sha256"], "size": metadata["size"]},
        label,
    )
    document = load_json(data, label)
    row_count = validator(document)
    return {
        "presentation": "exact-external-bytes-presented",
        "reference_status": "required-missing",
        "verified_row_count": row_count,
    }


def _reject_unfrozen_presentation(supplied_path, exact_path, label):
    if supplied_path is None:
        return {"presentation": "not-presented", "status": "required-missing"}
    if type(supplied_path) is not str or supplied_path != exact_path:
        raise ClosureError("{0} must use its exact frozen path".format(label))
    raise ClosureError(
        "{0} has no frozen digest/size authority and cannot be accepted".format(label)
    )


def _build_census_anchored(
    repo,
    failure_sites=None,
    failure_flows=None,
    failure_semantics_v3=None,
    semantic_review_v3=None,
    runtime_result_authority=None,
    _contract_path=CONTRACT_PATH,
    _contract_sha256=EXPECTED_CONTRACT_SHA256,
    _contract_size=EXPECTED_CONTRACT_SIZE,
    _contract_validator=validate_contract,
    _claims_factory=_false_claims,
):
    """Build a noncrediting census from one aggregate retained snapshot."""

    if runtime_result_authority is not None:
        raise ClosureError("runtime result authority has no frozen path/digest")
    with RepositorySnapshot(repo) as snapshot:
        contract_data = _read_exact(
            snapshot,
            {"path": _contract_path, "sha256": _contract_sha256, "size": _contract_size},
            "closure contract",
        )
        contract = load_json(contract_data, "closure contract")
        if pretty_bytes(contract) != contract_data:
            raise ClosureError("closure contract is not canonical pretty JSON")
        inputs = _contract_validator(contract)

        legacy_meta = inputs["legacy_behavior_authority"]
        legacy_data = _read_exact(
            snapshot,
            {"path": legacy_meta["path"], "sha256": legacy_meta["sha256"], "size": legacy_meta["size"]},
            "legacy behavior authority",
        )
        legacy = validate_legacy_authority(
            load_json(legacy_data, "legacy behavior authority"), legacy_meta
        )

        negative_meta = inputs["negative_dispatch_reference"]
        negative_data = _read_exact(
            snapshot,
            {"path": negative_meta["path"], "sha256": negative_meta["sha256"], "size": negative_meta["size"]},
            "negative-dispatch reference",
        )
        site_meta = inputs["compiler_failure_site_authority"]
        flow_meta = inputs["bounded_failure_flow_authority"]
        negative_vectors = validate_negative_reference(
            load_json(negative_data, "negative-dispatch reference"),
            negative_meta,
            site_meta,
            flow_meta,
        )

        runtime_meta = inputs["runtime_capture_reference"]
        runtime_data = _read_exact(
            snapshot,
            {"path": runtime_meta["path"], "sha256": runtime_meta["sha256"], "size": runtime_meta["size"]},
            "runtime capture reference",
        )
        runtime = validate_runtime_reference(
            load_json(runtime_data, "runtime capture reference"),
            runtime_meta,
            negative_vectors,
        )

        semantic_meta = inputs["semantic_evidence_authority"]
        generator_data = _read_exact(
            snapshot, semantic_meta["generator"], "semantic generator"
        )
        review_generator_data = _read_exact(
            snapshot,
            semantic_meta["independent_review_generator"],
            "semantic review generator",
        )
        semantic = validate_semantic_sources(
            generator_data, review_generator_data, semantic_meta
        )

        site_presentation = _present_external(
            snapshot,
            failure_sites,
            site_meta,
            "compiler failure-site authority",
            lambda value: _validate_external_sites(value, site_meta),
        )
        flow_presentation = _present_external(
            snapshot,
            failure_flows,
            flow_meta,
            "bounded failure-flow authority",
            lambda value: _validate_external_flows(value, flow_meta, site_meta),
        )
        semantics_presentation = _reject_unfrozen_presentation(
            failure_semantics_v3,
            semantic_meta["artifact"]["path"],
            "semantic v3 artifact",
        )
        review_presentation = _reject_unfrozen_presentation(
            semantic_review_v3,
            semantic_meta["independent_review_artifact"]["path"],
            "semantic v3 independent review",
        )

        result = {
            "assurance": {
                "direct_strong_same_module_ctu_structural_inventory": semantic[
                    "direct_strong_same_module_ctu_structural_inventory_status"
                ],
                "durable_runtime_result_authority": "required-missing",
                "execution": "required-missing",
                "independent_runtime_result_review": "required-missing",
                "semantic_v3_review": "required-missing",
            },
            "authority_status": {
                "bounded_failure_flows": flow_presentation,
                "compiler_failure_sites": site_presentation,
                "legacy_behavior_declarations": "verified-committed",
                "runtime_capture_references": "verified-committed-nonresult",
                "semantic_evidence": semantics_presentation,
                "semantic_review": review_presentation,
            },
            "claims": _claims_factory(),
            "contract": {
                "id": contract["contract_id"],
                "path": _contract_path,
                "sha256": _contract_sha256,
                "size": _contract_size,
            },
            "declarative_census": {
                "acceptance_test_declaration_count": legacy[
                    "acceptance_test_declaration_count"
                ],
                "behavior_acceptance_edge_count": legacy[
                    "behavior_acceptance_edge_count"
                ],
                "behavior_declaration_count": legacy["behavior_declaration_count"],
                "bounded_failure_flow_reference_count": flow_meta["row_count"],
                "c_semantic_question_reference_count": semantic[
                    "c_semantic_question_count"
                ],
                "compiler_failure_site_reference_count": site_meta["row_count"],
                "declarative_behavior_acceptance_join_complete": legacy[
                    "declarative_join_complete"
                ],
                "direct_strong_same_module_ctu_structural_inventory_reference_status": semantic[
                    "direct_strong_same_module_ctu_structural_inventory_status"
                ],
                "rust_mir_site_reference_count": semantic["rust_mir_site_count"],
            },
            "execution_census": {
                "declarative_ids_are_results": False,
                "result_authority_status": "required-missing",
                "runtime_result_count": 0,
                "surface_reference_count": runtime["surface_count"],
                "vector_reference_count": runtime["vector_count"],
            },
            "gate": {
                "gate_id": "FP-0006",
                "points_awarded": 0,
                "status": "IN_PROGRESS",
            },
            "joins": {
                "behavior_to_acceptance_declarations": {
                    "complete": True,
                    "kind": "declarative-only",
                },
                "declarations_to_compiler_sites": {
                    "complete": False,
                    "status": "required-missing",
                },
                "failure_flows_to_executable_results": {
                    "complete": False,
                    "status": "required-missing",
                },
                "full_cross_authority_join": {
                    "complete": False,
                    "status": "required-missing",
                },
                "semantic_rows_to_runtime_results": {
                    "complete": False,
                    "status": "required-missing",
                },
            },
            "profile": "fp0006-executable-acceptance-closure-census-v1",
            "required_missing": list(contract["required_missing"]),
            "schema_version": 1,
        }
        snapshot.finalize()
        return result


class _CliCensusEmitter(object):
    """Run decisive validation in a fresh CLI interpreter over retained bytes."""

    __slots__ = ()

    def emit(self, repo, output, *args, **kwargs):
        def same(left, right):
            if type(left) is not type(right):
                return False
            if type(left) is dict:
                return set(left) == set(right) and all(
                    same(left[key], right[key]) for key in left
                )
            if type(left) is list:
                return len(left) == len(right) and all(
                    same(a, b) for a, b in zip(left, right)
                )
            return left == right

        if args:
            raise TypeError("public census accepts optional inputs by keyword only")
        allowed = {
            "failure_flows",
            "failure_semantics_v3",
            "failure_sites",
            "runtime_result_authority",
            "semantic_review_v3",
        }
        if set(kwargs) - allowed:
            unexpected = sorted(set(kwargs) - allowed)[0]
            raise TypeError("unexpected keyword argument: {0}".format(unexpected))
        request = {"repo": os.path.abspath(str(repo))}
        for name in sorted(allowed):
            value = kwargs.get(name)
            if value is not None and (type(value) is not str or "\0" in value):
                raise ClosureError("{0} must be an exact string or null".format(name))
            request[name] = value
        request_data = canonical_bytes(request)
        if len(request_data) > 16384:
            raise ClosureError("isolated census request is too large")

        # The digest marker itself is normalized, so it can bind these exact
        # helper bytes without a recursive self-hash.  co_filename avoids the
        # mutable module-level __file__ global.
        script_path = os.path.abspath(type(self).emit.__code__.co_filename)
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = None
        try:
            descriptor = os.open(script_path, flags)
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size < 1
                or before.st_size > 1024 * 1024
            ):
                raise ClosureError("isolated checker source identity is invalid")
            chunks = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    raise ClosureError("isolated checker source ended early")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                raise ClosureError("isolated checker source grew while reading")
            after_read = os.fstat(descriptor)
            if _identity(before) != _identity(after_read):
                raise ClosureError("isolated checker source changed while reading")
            source_data = b"".join(chunks)
            normalized = re.sub(
                br"SELF_DIGEST:[0-9a-f]{64}",
                b"SELF_DIGEST:" + b"0" * 64,
                source_data,
            )
            expected_self = (
                "SELF_DIGEST:e642eb188883f789394b0c48a6fc13dfbb38f85691dc3a7d2451ee659f53f717"
            ).split(":", 1)[1]
            if sha256_bytes(normalized) != expected_self:
                raise ClosureError("isolated checker normalized SHA-256 changed")

            os.lseek(descriptor, 0, os.SEEK_SET)
            command = [
                sys.executable,
                "-I",
                "/proc/self/fd/{0}".format(descriptor),
                "--isolated-census-worker",
            ]
            environment = {
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
            }
            try:
                process = subprocess.run(
                    command,
                    input=request_data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    check=False,
                    env=environment,
                    pass_fds=(descriptor,),
                )
            except subprocess.TimeoutExpired:
                raise ClosureError("isolated census worker timed out")
            after_worker = os.fstat(descriptor)
            if _identity(before) != _identity(after_worker):
                raise ClosureError("isolated checker source changed during worker")
        finally:
            if descriptor is not None:
                os.close(descriptor)

        if type(process.returncode) is not int or process.returncode != 0:
            error = process.stderr[:512].decode("utf-8", "replace").strip()
            raise ClosureError("isolated census worker failed: {0}".format(error))
        if process.stderr:
            raise ClosureError("isolated census worker emitted unexpected stderr")
        if not process.stdout or len(process.stdout) > 1024 * 1024:
            raise ClosureError("isolated census worker output size is invalid")
        result = load_json(process.stdout, "isolated census result")
        if canonical_bytes(result) != process.stdout:
            raise ClosureError("isolated census result is not canonical")

        false_claims = {
            "credit_eligible": False,
            "durable": False,
            "executable_acceptance_complete": False,
            "executable_results_present": False,
            "fp0006_complete": False,
            "full_census_join_complete": False,
            "gate_pass": False,
            "independent_review_complete": False,
            "legacy_runtime_executed": False,
            "native_runtime_executed": False,
            "runtime_reachability_proven": False,
            "tracker_credit": False,
        }
        false_gate = {
            "gate_id": "FP-0006",
            "points_awarded": 0,
            "status": "IN_PROGRESS",
        }
        expected_missing = [
            "bounded_failure_flow_rows",
            "compiler_failure_site_rows",
            "direct_strong_same_module_ctu_structural_inventory",
            "durable_runtime_result_authority",
            "independent_runtime_result_review",
            "runtime_result_rows",
            "semantic_c_question_rows",
            "semantic_rust_mir_rows",
            "semantic_v3_independent_review",
        ]
        expected_counts = {
            "acceptance_test_declaration_count": 1326,
            "behavior_acceptance_edge_count": 1326,
            "behavior_declaration_count": 1326,
            "bounded_failure_flow_reference_count": 2602,
            "c_semantic_question_reference_count": 205,
            "compiler_failure_site_reference_count": 971,
            "declarative_behavior_acceptance_join_complete": True,
            "direct_strong_same_module_ctu_structural_inventory_reference_status": (
                "required-missing"
            ),
            "rust_mir_site_reference_count": 420,
        }
        if type(result) is not dict or set(result) != {
            "assurance",
            "authority_status",
            "claims",
            "contract",
            "declarative_census",
            "execution_census",
            "gate",
            "joins",
            "profile",
            "required_missing",
            "schema_version",
        }:
            raise ClosureError("isolated census result schema changed")
        if (
            type(result["schema_version"]) is not int
            or result["schema_version"] != 1
            or result["profile"] != "fp0006-executable-acceptance-closure-census-v1"
            or not same(result["claims"], false_claims)
            or not same(result["gate"], false_gate)
            or not same(result["required_missing"], expected_missing)
            or not same(result["declarative_census"], expected_counts)
        ):
            raise ClosureError("isolated census result identity or counts changed")
        expected_assurance = {
            "direct_strong_same_module_ctu_structural_inventory": (
                "required-missing"
            ),
            "durable_runtime_result_authority": "required-missing",
            "execution": "required-missing",
            "independent_runtime_result_review": "required-missing",
            "semantic_v3_review": "required-missing",
        }
        expected_execution = {
            "declarative_ids_are_results": False,
            "result_authority_status": "required-missing",
            "runtime_result_count": 0,
            "surface_reference_count": 2,
            "vector_reference_count": 2,
        }
        expected_joins = {
            "behavior_to_acceptance_declarations": {
                "complete": True,
                "kind": "declarative-only",
            },
            "declarations_to_compiler_sites": {
                "complete": False,
                "status": "required-missing",
            },
            "failure_flows_to_executable_results": {
                "complete": False,
                "status": "required-missing",
            },
            "full_cross_authority_join": {
                "complete": False,
                "status": "required-missing",
            },
            "semantic_rows_to_runtime_results": {
                "complete": False,
                "status": "required-missing",
            },
        }
        if (
            not same(result["assurance"], expected_assurance)
            or not same(result["execution_census"], expected_execution)
            or not same(result["joins"], expected_joins)
        ):
            raise ClosureError("isolated census noncrediting boundary changed")
        authority = result["authority_status"]
        if type(authority) is not dict or set(authority) != {
            "bounded_failure_flows",
            "compiler_failure_sites",
            "legacy_behavior_declarations",
            "runtime_capture_references",
            "semantic_evidence",
            "semantic_review",
        }:
            raise ClosureError("isolated census authority status changed")
        if (
            authority["legacy_behavior_declarations"] != "verified-committed"
            or authority["runtime_capture_references"] != "verified-committed-nonresult"
            or authority["semantic_evidence"] != {
                "presentation": "not-presented",
                "status": "required-missing",
            }
            or authority["semantic_review"] != {
                "presentation": "not-presented",
                "status": "required-missing",
            }
        ):
            raise ClosureError("isolated census fixed authority status changed")
        for name, count in (
            ("compiler_failure_sites", 971),
            ("bounded_failure_flows", 2602),
        ):
            value = authority[name]
            if type(value) is not dict or value.get("reference_status") != "required-missing":
                raise ClosureError("isolated external authority status changed")
            if value.get("presentation") == "not-presented":
                if set(value) != {"presentation", "reference_status"}:
                    raise ClosureError("isolated missing authority schema changed")
            elif value.get("presentation") == "exact-external-bytes-presented":
                if (
                    set(value) != {"presentation", "reference_status", "verified_row_count"}
                    or type(value["verified_row_count"]) is not int
                    or value["verified_row_count"] != count
                ):
                    raise ClosureError("isolated presented authority count changed")
            else:
                raise ClosureError("isolated external presentation status changed")

        # Never trust the worker to supply claim/gate objects, even after the
        # exact comparison above.  Recreate and recheck the final envelope.
        result["claims"] = {
            "credit_eligible": False,
            "durable": False,
            "executable_acceptance_complete": False,
            "executable_results_present": False,
            "fp0006_complete": False,
            "full_census_join_complete": False,
            "gate_pass": False,
            "independent_review_complete": False,
            "legacy_runtime_executed": False,
            "native_runtime_executed": False,
            "runtime_reachability_proven": False,
            "tracker_credit": False,
        }
        result["gate"] = {
            "gate_id": "FP-0006",
            "points_awarded": 0,
            "status": "IN_PROGRESS",
        }
        if any(type(value) is not bool or value is not False for value in result["claims"].values()):
            raise ClosureError("final public claims are not exact false booleans")
        if result["gate"] != false_gate:
            raise ClosureError("final public gate boundary changed")
        data = pretty_bytes(result)
        if output:
            _atomic_write(output, data)
        else:
            sys.stdout.write(data.decode("ascii"))


class _ImportedCensusEmitter(object):
    """Fail closed when an imported caller asks to emit acceptance bytes."""

    __slots__ = ()

    def emit(self, repo, output, *args, **kwargs):
        raise ClosureError(
            "public census emission is available only from a fresh CLI interpreter"
        )


# A caller that imports this module receives only the fail-closed facade.  The
# output-capable implementation is selected while a fresh interpreter loads the
# file as its main program, before any imported caller can rebind module globals,
# serializer helpers, or output sinks.  Delete both implementation names so the
# imported namespace does not retain an alternate output authority.
if __name__ == "__main__":
    _PublicCensusEmitter = _CliCensusEmitter
else:
    _PublicCensusEmitter = _ImportedCensusEmitter
del _CliCensusEmitter
del _ImportedCensusEmitter


def _atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, str(path))
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--failure-sites")
    parser.add_argument("--failure-flows")
    parser.add_argument("--failure-semantics-v3")
    parser.add_argument("--semantic-review-v3")
    parser.add_argument("--runtime-result-authority")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def _isolated_worker_main():
    try:
        data = sys.stdin.buffer.read(16385)
        if not data or len(data) > 16384:
            raise ClosureError("isolated request size is invalid")
        request = load_json(data, "isolated request")
        if canonical_bytes(request) != data:
            raise ClosureError("isolated request is not canonical")
        require_keys(
            request,
            {
                "failure_flows",
                "failure_semantics_v3",
                "failure_sites",
                "repo",
                "runtime_result_authority",
                "semantic_review_v3",
            },
            "isolated request",
        )
        require_string(request["repo"], "isolated repository")
        for name in (
            "failure_flows",
            "failure_semantics_v3",
            "failure_sites",
            "runtime_result_authority",
            "semantic_review_v3",
        ):
            value = request[name]
            if value is not None and (type(value) is not str or not value or "\0" in value):
                raise ClosureError("isolated {0} is malformed".format(name))
        result = _build_census_anchored(
            request["repo"],
            failure_sites=request["failure_sites"],
            failure_flows=request["failure_flows"],
            failure_semantics_v3=request["failure_semantics_v3"],
            semantic_review_v3=request["semantic_review_v3"],
            runtime_result_authority=request["runtime_result_authority"],
        )
        sys.stdout.buffer.write(canonical_bytes(result))
        sys.stdout.buffer.flush()
    except (ClosureError, OSError, TypeError, ValueError) as error:
        sys.stderr.write("isolated FP-0006 census failed: {0}\n".format(error))
        return 1
    return 0


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        _PublicCensusEmitter().emit(
            args.repo,
            args.output,
            failure_sites=args.failure_sites,
            failure_flows=args.failure_flows,
            failure_semantics_v3=args.failure_semantics_v3,
            semantic_review_v3=args.semantic_review_v3,
            runtime_result_authority=args.runtime_result_authority,
        )
    except (ClosureError, OSError, ValueError) as error:
        sys.stderr.write("FP-0006 executable acceptance closure failed: {0}\n".format(error))
        return 1
    sys.stderr.write(
        "FP-0006 executable acceptance closure remains required-missing and noncrediting\n"
    )
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--isolated-census-worker"]:
        sys.exit(_isolated_worker_main())
    sys.exit(main())
