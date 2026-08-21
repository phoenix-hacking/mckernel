#!/usr/bin/env python3
"""Validate the bounded, noncrediting FP-0006 negative-dispatch witness.

Every public artifact review reloads and validates the exact repository
authority before interpreting capture bytes.  The two capture producers and
the external ef58860e failure evidence remain evidence inputs only: no result
authority, current-head reachability, gate decision, or tracker credit is
created here.
"""

from __future__ import print_function

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path(
    "host-kernel/contracts/fp0006-ihk-device-negative-dispatch-v1.json"
)

# Convenience names for callers.  Security decisions never trust these
# mutable module attributes; they use the freshly validated contract object.
CONTRACT_ID = "fp-0006-ihk-device-negative-dispatch-v1"
LEGACY_SURFACE = "legacy-live-ioctl"
NATIVE_SURFACE = "native-rust-source-fixture"
HEX16 = re.compile(r"^[0-9a-f]{16}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class WitnessError(RuntimeError):
    """Raised when a contract, authority input, or capture fails closed."""


def _exact_json_equal(actual: Any, expected: Any) -> bool:
    """Compare strict JSON values without Python's bool/int equivalence."""

    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        if len(actual) != len(expected):
            return False
        for key, expected_value in expected.items():
            if type(key) is not str or key not in actual:
                return False
            if not _exact_json_equal(actual[key], expected_value):
                return False
        return True
    if type(expected) is list:
        if len(actual) != len(expected):
            return False
        return all(
            _exact_json_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected)
        )
    return bool(actual == expected)


def _require_exact_json(actual: Any, expected: Any, label: str) -> None:
    if not _exact_json_equal(actual, expected):
        raise WitnessError("{0} differs".format(label))


def _duplicate_rejecting_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    value = {}  # type: Dict[str, Any]
    for key, item in pairs:
        if key in value:
            raise WitnessError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise WitnessError("non-finite JSON number is forbidden: {0}".format(value))


def _validate_strict_json(value: Any, label: str) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is list:
        for item in value:
            _validate_strict_json(item, label)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise WitnessError("{0} contains a non-string JSON key".format(label))
            _validate_strict_json(item, label)
        return
    raise WitnessError("{0} contains a non-strict JSON value".format(label))


def _load_json_bytes(data: bytes, label: str) -> Dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_constant,
        )
    except WitnessError:
        raise
    except (UnicodeError, ValueError) as error:
        raise WitnessError("cannot parse {0}: {1}".format(label, error))
    if type(value) is not dict:
        raise WitnessError("{0} must contain one JSON object".format(label))
    _validate_strict_json(value, label)
    return value


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _pretty_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_keys(value: Any, expected: Sequence[str], label: str) -> None:
    if type(value) is not dict:
        raise WitnessError("{0} must be an object".format(label))
    actual = sorted(value.keys())
    wanted = sorted(expected)
    if not _exact_json_equal(actual, wanted):
        raise WitnessError("{0} keys differ".format(label))


def _require_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise WitnessError("{0} must be an exact integer".format(label))
    return value


def _canonical_relative_parts(relative: str, label: str) -> List[str]:
    if type(relative) is not str or not relative or "\\" in relative:
        raise WitnessError("{0} path is not canonical POSIX text".format(label))
    item = Path(relative)
    if item.is_absolute() or ".." in item.parts or item.as_posix() != relative:
        raise WitnessError("{0} path escapes the repository".format(label))
    parts = list(item.parts)
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise WitnessError("{0} path contains an unsafe component".format(label))
    return parts


def _open_flags(directory: bool) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory_only = getattr(os, "O_DIRECTORY", None)
    if no_follow is None or directory_only is None:
        raise WitnessError("descriptor-rooted O_NOFOLLOW/openat support is required")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow
    if directory:
        flags |= directory_only
    return flags


def _close_open_descriptors(descriptors: List[int], label: str) -> None:
    first_error = None  # type: Optional[OSError]
    while descriptors:
        descriptor = descriptors.pop()
        try:
            os.close(descriptor)
        except OSError as error:
            if first_error is None:
                first_error = error
    if first_error is not None:
        raise WitnessError("cannot close retained {0}: {1}".format(label, first_error))


def _replay_retained_directories(
    records: Sequence[Dict[str, Any]], label: str
) -> None:
    for index, record in enumerate(records):
        descriptor_identity = _file_identity(os.fstat(record["descriptor"]))
        if index == 0:
            named_metadata = os.lstat(str(record["path"]))
        else:
            named_metadata = os.stat(
                record["name"],
                dir_fd=records[index - 1]["descriptor"],
                follow_symlinks=False,
            )
        if stat.S_ISLNK(named_metadata.st_mode) or not stat.S_ISDIR(
            named_metadata.st_mode
        ):
            raise WitnessError("{0} ancestor became a non-directory".format(label))
        named_identity = _file_identity(named_metadata)
        _require_exact_json(
            descriptor_identity, record["identity"],
            label + " retained ancestor descriptor replay",
        )
        _require_exact_json(
            named_identity, record["identity"],
            label + " retained named ancestor replay",
        )
        _require_exact_json(
            named_identity, descriptor_identity,
            label + " retained ancestor named/descriptor identity",
        )


def _replay_closed_directories(
    records: Sequence[Dict[str, Any]], label: str
) -> None:
    for record in records:
        metadata = os.lstat(str(record["path"]))
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise WitnessError("{0} ancestor became a non-directory".format(label))
        _require_exact_json(
            _file_identity(metadata), record["identity"],
            label + " post-close named ancestor replay",
        )


def _closed_file_snapshot(
    directories: Sequence[Dict[str, Any]],
    leaf: Optional[Dict[str, Any]],
    target: Path,
    label: str,
) -> Dict[str, Any]:
    return {
        "directories": [
            {"identity": list(record["identity"]), "path": record["path"]}
            for record in directories
        ],
        "label": label,
        "leaf": None
        if leaf is None
        else {"identity": list(leaf["identity"]), "path": leaf["path"]},
        "target": target,
    }


def _replay_closed_file_snapshot(snapshot: Dict[str, Any]) -> None:
    label = snapshot["label"]
    try:
        _replay_closed_directories(snapshot["directories"], label)
        leaf = snapshot["leaf"]
        if leaf is None:
            try:
                os.lstat(str(snapshot["target"]))
            except FileNotFoundError:
                pass
            else:
                raise WitnessError(
                    "{0} appeared after a required-missing snapshot".format(label)
                )
        else:
            metadata = os.lstat(str(leaf["path"]))
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise WitnessError("{0} leaf changed type after close".format(label))
            _require_exact_json(
                _file_identity(metadata), leaf["identity"],
                label + " post-close named leaf replay",
            )
        _replay_closed_directories(snapshot["directories"], label + " final")
    except WitnessError:
        raise
    except OSError as error:
        raise WitnessError("cannot replay closed {0}: {1}".format(label, error))


def _replay_closed_file_snapshots(snapshots: Sequence[Dict[str, Any]]) -> None:
    for snapshot in snapshots:
        _replay_closed_file_snapshot(snapshot)


def _read_rooted_file(
    root: Path,
    relative: str,
    label: str,
    maximum: Optional[int] = None,
    missing_ok: bool = False,
    snapshots: Optional[List[Dict[str, Any]]] = None,
) -> Optional[bytes]:
    """Read one file through a retained openat chain and replay after close."""

    parts = _canonical_relative_parts(relative, label)
    absolute_root = Path(os.path.abspath(str(root)))
    target = absolute_root.joinpath(*parts)
    parent = target.parent
    if not parent.is_absolute() or parent.anchor != target.anchor:
        raise WitnessError("{0} root is not an absolute POSIX directory".format(label))

    directory_flags = _open_flags(True)
    leaf_flags = _open_flags(False)
    directory_records = []  # type: List[Dict[str, Any]]
    open_descriptors = []  # type: List[int]
    leaf_record = None  # type: Optional[Dict[str, Any]]
    first_replay = None  # type: Optional[bytes]
    failure = None  # type: Optional[WitnessError]
    missing = False
    try:
        current = Path(parent.anchor)
        root_named = os.lstat(str(current))
        if stat.S_ISLNK(root_named.st_mode) or not stat.S_ISDIR(root_named.st_mode):
            raise WitnessError("{0} filesystem root is not a directory".format(label))
        descriptor = os.open(str(current), directory_flags)
        open_descriptors.append(descriptor)
        root_fd = os.fstat(descriptor)
        _require_exact_json(
            _file_identity(root_fd), _file_identity(root_named),
            label + " filesystem-root named/descriptor identity",
        )
        directory_records.append(
            {
                "descriptor": descriptor,
                "identity": _file_identity(root_fd),
                "name": current.anchor,
                "path": current,
            }
        )

        for component in parent.parts[1:]:
            parent_descriptor = directory_records[-1]["descriptor"]
            named = os.stat(
                component, dir_fd=parent_descriptor, follow_symlinks=False
            )
            if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
                raise WitnessError(
                    "{0} ancestor is not a non-symlink directory".format(label)
                )
            descriptor = os.open(
                component, directory_flags, dir_fd=parent_descriptor
            )
            open_descriptors.append(descriptor)
            retained = os.fstat(descriptor)
            _require_exact_json(
                _file_identity(retained), _file_identity(named),
                label + " ancestor named/descriptor identity",
            )
            current = current / component
            directory_records.append(
                {
                    "descriptor": descriptor,
                    "identity": _file_identity(retained),
                    "name": component,
                    "path": current,
                }
            )

        parent_descriptor = directory_records[-1]["descriptor"]
        leaf_name = parts[-1]
        named_leaf = os.stat(
            leaf_name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        if stat.S_ISLNK(named_leaf.st_mode) or not stat.S_ISREG(named_leaf.st_mode):
            raise WitnessError("{0} must be a regular non-symlink file".format(label))
        leaf_descriptor = os.open(leaf_name, leaf_flags, dir_fd=parent_descriptor)
        open_descriptors.append(leaf_descriptor)
        retained_leaf = os.fstat(leaf_descriptor)
        leaf_identity = _file_identity(retained_leaf)
        _require_exact_json(
            leaf_identity, _file_identity(named_leaf),
            label + " leaf named/descriptor identity",
        )
        if retained_leaf.st_nlink != 1:
            raise WitnessError("{0} must be a singly linked regular file".format(label))
        if maximum is not None and (
            retained_leaf.st_size <= 0 or retained_leaf.st_size > maximum
        ):
            raise WitnessError("{0} size is outside its limit".format(label))
        leaf_record = {
            "descriptor": leaf_descriptor,
            "identity": leaf_identity,
            "name": leaf_name,
            "path": target,
        }

        first_replay = _read_fd_exact(leaf_descriptor, retained_leaf.st_size, label)
        second_replay = _read_fd_exact(leaf_descriptor, retained_leaf.st_size, label)
        _require_exact_json(
            second_replay, first_replay, label + " retained byte replay"
        )
        retained_after = _file_identity(os.fstat(leaf_descriptor))
        named_after = _file_identity(
            os.stat(leaf_name, dir_fd=parent_descriptor, follow_symlinks=False)
        )
        _require_exact_json(
            retained_after, leaf_identity, label + " retained leaf descriptor replay"
        )
        _require_exact_json(
            named_after, leaf_identity, label + " retained named leaf replay"
        )
        _require_exact_json(
            named_after, retained_after, label + " final leaf named/descriptor identity"
        )
        _replay_retained_directories(directory_records, label)
    except FileNotFoundError as error:
        if missing_ok:
            missing = True
        else:
            failure = WitnessError("{0} path is unavailable: {1}".format(label, error))
    except WitnessError as error:
        failure = error
    except OSError as error:
        failure = WitnessError("cannot retain {0}: {1}".format(label, error))

    try:
        _close_open_descriptors(open_descriptors, label)
    except WitnessError as error:
        if failure is None:
            failure = error
    if failure is not None:
        raise failure
    if missing:
        missing_snapshot = _closed_file_snapshot(
            directory_records, None, target, label
        )
        _replay_closed_file_snapshot(missing_snapshot)
        if snapshots is not None:
            snapshots.append(missing_snapshot)
        return None
    if leaf_record is None or first_replay is None:
        raise WitnessError("{0} retained snapshot is incomplete".format(label))

    snapshot = _closed_file_snapshot(directory_records, leaf_record, target, label)
    _replay_closed_file_snapshot(snapshot)
    if snapshots is not None:
        snapshots.append(snapshot)
    return first_replay


def _select_exact_rows(
    actual_rows: Any, expected_rows: Any, label: str
) -> None:
    if type(actual_rows) is not list or type(expected_rows) is not list:
        raise WitnessError("{0} rows must be lists".format(label))
    by_id = {}  # type: Dict[str, Dict[str, Any]]
    for row in actual_rows:
        if type(row) is not dict or type(row.get("id")) is not str:
            raise WitnessError("{0} contains an invalid row identity".format(label))
        if row["id"] in by_id:
            raise WitnessError("{0} contains a duplicate row identity".format(label))
        by_id[row["id"]] = row
    expected_ids = []  # type: List[str]
    for row in expected_rows:
        if type(row) is not dict or type(row.get("id")) is not str:
            raise WitnessError("{0} authority contains an invalid row".format(label))
        row_id = row["id"]
        if row_id in expected_ids or row_id not in by_id:
            raise WitnessError("{0} authority row is duplicate or missing".format(label))
        expected_ids.append(row_id)
        _require_exact_json(by_id[row_id], row, label + " row " + row_id)


def _verify_legacy_behavior_authority(
    contract: Dict[str, Any], input_bytes: Dict[str, bytes]
) -> None:
    authority = contract["legacy_behavior_authority"]
    behavior = _load_json_bytes(
        input_bytes["legacy_behavior_contract"], "legacy behavior authority"
    )
    _require_exact_json(
        behavior.get("schema_version"), authority["authority"]["schema_version"],
        "legacy behavior schema version",
    )
    _require_exact_json(
        behavior.get("generator"), authority["authority"]["generator"],
        "legacy behavior generator",
    )
    _require_exact_json(
        behavior.get("inventory_file_sha256"),
        authority["inputs"]["inventory"]["sha256"],
        "legacy behavior inventory binding",
    )
    _require_exact_json(
        behavior.get("policy_file_sha256"), authority["inputs"]["policy"]["sha256"],
        "legacy behavior policy binding",
    )
    _require_exact_json(
        behavior.get("policy_id"), authority["inputs"]["policy"]["policy_id"],
        "legacy behavior policy identity",
    )
    _require_exact_json(
        behavior.get("provenance"), authority["provenance"],
        "legacy behavior provenance",
    )
    _select_exact_rows(
        behavior.get("acceptance_tests"), authority["acceptance_tests"],
        "legacy acceptance",
    )
    _select_exact_rows(
        behavior.get("behaviors"), authority["behaviors"], "legacy behavior"
    )


def _verify_external_failure_evidence(
    repo: Path,
    contract: Dict[str, Any],
    snapshots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    evidence = contract["failure_evidence"]
    site_binding = evidence["failure_site_authority"]
    flow_binding = evidence["failure_flow_artifact"]
    evidence_root = Path(os.path.abspath(str(repo))).parent
    site_bytes = _read_rooted_file(
        evidence_root,
        site_binding["external_path_hint"],
        "external failure-site authority",
        site_binding["size"],
        missing_ok=True,
        snapshots=snapshots,
    )
    flow_bytes = _read_rooted_file(
        evidence_root,
        flow_binding["external_path_hint"],
        "external failure-flow artifact",
        flow_binding["size"],
        missing_ok=True,
        snapshots=snapshots,
    )
    if site_bytes is None and flow_bytes is None:
        return {
            "failure_flow_artifact": "required-missing",
            "failure_site_authority": "required-missing",
            "independent_provenance_review_complete": False,
            "records_verified": False,
        }
    if (site_bytes is None) is not (flow_bytes is None):
        raise WitnessError("external failure evidence is only partially available")
    if site_bytes is None or flow_bytes is None:
        raise WitnessError("external failure evidence availability is inconsistent")
    for binding, data, label in (
        (site_binding, site_bytes, "failure-site authority"),
        (flow_binding, flow_bytes, "failure-flow artifact"),
    ):
        _require_exact_json(len(data), binding["size"], label + " size")
        _require_exact_json(_sha256(data), binding["sha256"], label + " digest")

    sites = _load_json_bytes(site_bytes, "external failure-site authority")
    flows = _load_json_bytes(flow_bytes, "external failure-flow artifact")
    _require_exact_json(sites.get("schema_version"), 1, "failure-site schema")
    _require_exact_json(
        sites.get("generator"), "scripts/host_module_failure_sites.py",
        "failure-site generator",
    )
    _require_exact_json(
        sites.get("profile"), "compiler-backed-active-host-module-failure-sites-v1",
        "failure-site profile",
    )
    site_provenance = sites.get("provenance")
    if type(site_provenance) is not dict:
        raise WitnessError("failure-site provenance is unavailable")
    _require_exact_json(
        site_provenance.get("repository_commit"), site_binding["repository_commit"],
        "failure-site repository commit",
    )
    _require_exact_json(flows.get("schema_version"), 1, "failure-flow schema")
    _require_exact_json(
        flows.get("generator"), "scripts/host_module_failure_flows.py",
        "failure-flow generator",
    )
    _require_exact_json(
        flows.get("input_failure_sites"), flow_binding["input_failure_sites"],
        "failure-flow input-failure-sites binding",
    )
    _select_exact_rows(
        flows.get("failure_flows"), evidence["hff_records"], "HFF evidence"
    )
    for record in evidence["hff_records"]:
        _require_exact_json(
            record.get("source_sha256"),
            contract["current_head_boundary"]["hff_effective_source_sha256"],
            "HFF effective source digest",
        )
        _require_exact_json(
            record.get("reachable_entry_roots"), [], "HFF reachable-entry roots"
        )
    return {
        "failure_flow_artifact": "verified-local-external-noncrediting",
        "failure_flow_sha256": _sha256(flow_bytes),
        "failure_site_authority": "verified-local-external-noncrediting",
        "failure_site_sha256": _sha256(site_bytes),
        "independent_provenance_review_complete": False,
        "records_verified": True,
    }


def _load_authority(
    repo: Path, contract_path: Path = DEFAULT_CONTRACT
) -> Tuple[
    Dict[str, Any],
    bytes,
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    List[Dict[str, Any]],
]:
    # Function-local anchors cannot be redirected through mutable module globals.
    expected_relative = "host-kernel/contracts/fp0006-ihk-device-negative-dispatch-v1.json"
    expected_contract_sha256 = "13baf241704c98b5d087abc85af45201c8f345ed3cdd08ae310febe666e789c8"
    expected_contract_size = 19668
    expected_claims = {
        "credit_eligible": False,
        "current_head_legacy_provenance_proven": False,
        "current_head_runtime_reachability_proven": False,
        "fp0006_complete": False,
        "full_failure_semantics_covered": False,
        "gate_pass": False,
        "legacy_runtime_executed": False,
        "native_runtime_executed": False,
        "runtime_reachability_proven": False,
        "tracker_credit": False,
    }
    if Path(contract_path).as_posix() != expected_relative:
        raise WitnessError("FP-0006 contract path differs from the fixed authority")
    repo = Path(repo)
    authority_snapshots = []  # type: List[Dict[str, Any]]
    contract_bytes = _read_rooted_file(
        repo,
        expected_relative,
        "FP-0006 witness contract",
        expected_contract_size,
        snapshots=authority_snapshots,
    )
    if contract_bytes is None:
        raise WitnessError("FP-0006 witness contract is unavailable")
    _require_exact_json(len(contract_bytes), expected_contract_size, "contract size")
    _require_exact_json(_sha256(contract_bytes), expected_contract_sha256, "contract digest")
    contract = _load_json_bytes(contract_bytes, "FP-0006 witness contract")
    if contract_bytes != _pretty_json(contract):
        raise WitnessError("FP-0006 witness contract is not canonical pretty JSON")
    _require_keys(
        contract,
        (
            "artifact_contract", "claims", "contract_id", "current_head_boundary",
            "failure_evidence", "frozen_inputs", "gate", "legacy_behavior_authority",
            "limitations", "producers", "schema_version", "schemas", "vectors",
        ),
        "FP-0006 witness contract",
    )
    _require_exact_json(contract["schema_version"], 1, "contract schema version")
    _require_exact_json(
        contract["contract_id"], "fp-0006-ihk-device-negative-dispatch-v1",
        "contract identity",
    )
    _require_exact_json(contract["claims"], expected_claims, "noncrediting claims")
    _require_exact_json(
        contract["gate"],
        {"gate_id": "FP-0006", "points_awarded": 0, "status": "IN_PROGRESS"},
        "gate boundary",
    )
    _require_exact_json(
        contract["artifact_contract"]["result_authority"],
        {
            "durable_artifact_required": True,
            "independent_review_required": True,
            "path": None,
            "status": "required-missing",
        },
        "result authority boundary",
    )
    boundary = contract["current_head_boundary"]
    _require_exact_json(
        boundary["current_host_driver_matches_hff_effective_source"], False,
        "current/HFF digest equality boundary",
    )
    _require_exact_json(
        boundary["current_head_legacy_provenance_claimed"], False,
        "current-head legacy provenance boundary",
    )
    _require_exact_json(
        boundary["current_head_runtime_reachability_claimed"], False,
        "current-head reachability boundary",
    )

    input_bytes = {}  # type: Dict[str, bytes]
    input_summary = {}  # type: Dict[str, Dict[str, Any]]
    frozen_inputs = contract["frozen_inputs"]
    if type(frozen_inputs) is not dict:
        raise WitnessError("frozen input authority must be an object")
    for input_id in sorted(frozen_inputs):
        binding = frozen_inputs[input_id]
        _require_keys(binding, ("path", "sha256"), "frozen input " + input_id)
        data = _read_rooted_file(
            repo,
            binding["path"],
            "frozen input " + input_id,
            snapshots=authority_snapshots,
        )
        if data is None:
            raise WitnessError("frozen input is unavailable: " + input_id)
        _require_exact_json(_sha256(data), binding["sha256"], "frozen input digest " + input_id)
        input_bytes[input_id] = data
        input_summary[input_id] = {
            "path": binding["path"], "sha256": _sha256(data), "size": len(data)
        }

    current_binding = boundary["current_host_driver"]
    current_bytes = _read_rooted_file(
        repo,
        current_binding["path"],
        "current host_driver boundary",
        current_binding["size"],
        snapshots=authority_snapshots,
    )
    if current_bytes is None:
        raise WitnessError("current host_driver boundary is unavailable")
    _require_exact_json(len(current_bytes), current_binding["size"], "current host_driver size")
    _require_exact_json(
        _sha256(current_bytes), current_binding["sha256"], "current host_driver digest"
    )
    if _exact_json_equal(
        current_binding["sha256"], boundary["hff_effective_source_sha256"]
    ):
        raise WitnessError("current host_driver unexpectedly equals the HFF effective source")

    producers = contract["producers"]
    for producer_id in ("legacy", "native"):
        binding = producers[producer_id]
        producer_bytes = _read_rooted_file(
            repo,
            binding["path"],
            producer_id + " capture producer",
            binding["size"],
            snapshots=authority_snapshots,
        )
        if producer_bytes is None:
            raise WitnessError(producer_id + " capture producer is unavailable")
        _require_exact_json(
            len(producer_bytes), binding["size"], producer_id + " producer size"
        )
        _require_exact_json(
            _sha256(producer_bytes), binding["sha256"], producer_id + " producer digest"
        )

    legacy_authority = contract["legacy_behavior_authority"]
    for input_id, authority_id in (
        ("legacy_behavior_contract", "authority"),
        ("legacy_inventory", "inventory"),
        ("legacy_policy", "policy"),
    ):
        if authority_id == "authority":
            binding = legacy_authority[authority_id]
        else:
            binding = legacy_authority["inputs"][authority_id]
        _require_exact_json(
            len(input_bytes[input_id]), binding["size"], input_id + " authority size"
        )
        _require_exact_json(
            _sha256(input_bytes[input_id]), binding["sha256"],
            input_id + " authority digest",
        )
    _verify_legacy_behavior_authority(contract, input_bytes)
    external_summary = _verify_external_failure_evidence(
        repo, contract, authority_snapshots
    )
    _replay_closed_file_snapshots(authority_snapshots)
    return (
        contract,
        contract_bytes,
        input_summary,
        external_summary,
        authority_snapshots,
    )


def validate_contract(
    repo: Path = ROOT, contract_path: Path = DEFAULT_CONTRACT
) -> Dict[str, Any]:
    contract, contract_bytes, inputs, external, _ = _load_authority(
        repo, contract_path
    )
    return {
        "claims": copy.deepcopy(contract["claims"]),
        "contract_id": contract["contract_id"],
        "contract_sha256": _sha256(contract_bytes),
        "external_failure_evidence": external,
        "frozen_inputs": inputs,
        "result_authority": contract["artifact_contract"]["result_authority"]["status"],
        "vector_count": len(contract["vectors"]),
    }


def _file_identity(metadata: os.stat_result) -> List[int]:
    return [
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_rdev,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        getattr(metadata, "st_blksize", 0),
        getattr(metadata, "st_blocks", 0),
    ]


def _directory_identity(metadata: os.stat_result) -> List[int]:
    return [
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    ]


def _read_fd_exact(descriptor: int, size: int, label: str) -> bytes:
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        remaining = size
        chunks = []  # type: List[bytes]
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65536))
            if not chunk:
                raise WitnessError("{0} ended before its retained size".format(label))
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise WitnessError("{0} grew beyond its retained size".format(label))
        return b"".join(chunks)
    except WitnessError:
        raise
    except OSError as error:
        raise WitnessError("cannot replay {0}: {1}".format(label, error))


def _closed_capture_snapshot(
    directories: Sequence[Dict[str, Any]],
    root: Path,
    members: Sequence[str],
    identities: Dict[str, List[int]],
) -> Dict[str, Any]:
    return {
        "directories": [
            {"identity": list(record["identity"]), "path": record["path"]}
            for record in directories
        ],
        "identities": {
            name: list(identities[name]) for name in sorted(members)
        },
        "members": sorted(members),
        "root": root,
    }


def _replay_closed_capture_snapshot(snapshot: Dict[str, Any]) -> None:
    try:
        _replay_closed_directories(snapshot["directories"], "capture path")
        names = sorted(os.listdir(str(snapshot["root"])))
        _require_exact_json(
            names, snapshot["members"], "post-close capture member-set replay"
        )
        for name in snapshot["members"]:
            metadata = (snapshot["root"] / name).lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise WitnessError(
                    "capture member changed type after all descriptors closed: {0}".format(
                        name
                    )
                )
            _require_exact_json(
                _file_identity(metadata), snapshot["identities"][name],
                "post-close path-rooted leaf replay " + name,
            )
        _replay_closed_directories(snapshot["directories"], "capture path final")
    except WitnessError:
        raise
    except OSError as error:
        raise WitnessError("cannot replay closed capture snapshot: {0}".format(error))


def _replay_closed_capture_snapshots(
    snapshots: Sequence[Dict[str, Any]]
) -> None:
    for snapshot in snapshots:
        _replay_closed_capture_snapshot(snapshot)


def _read_capture_members(
    root: Path,
    members: Sequence[str],
    expected_mode: int,
    maximum_bytes: int,
    snapshots: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, bytes]:
    absolute = Path(os.path.abspath(str(root)))
    if not absolute.is_absolute():
        raise WitnessError("capture path must be absolute after lexical normalization")
    directory_flags = _open_flags(True)
    member_flags = _open_flags(False)
    directory_records = []  # type: List[Dict[str, Any]]
    directory_descriptors = []  # type: List[int]
    descriptors = {}  # type: Dict[str, int]
    named_before = {}  # type: Dict[str, List[int]]
    fd_before = {}  # type: Dict[str, List[int]]
    first_replay = {}  # type: Dict[str, bytes]
    try:
        current = Path(absolute.anchor)
        root_named = os.lstat(str(current))
        if stat.S_ISLNK(root_named.st_mode) or not stat.S_ISDIR(root_named.st_mode):
            raise WitnessError("capture filesystem root is not a directory")
        descriptor = os.open(str(current), directory_flags)
        directory_descriptors.append(descriptor)
        root_fd = os.fstat(descriptor)
        _require_exact_json(
            _file_identity(root_fd), _file_identity(root_named),
            "capture filesystem-root named/descriptor identity",
        )
        directory_records.append(
            {
                "descriptor": descriptor,
                "identity": _file_identity(root_fd),
                "name": current.anchor,
                "path": current,
            }
        )

        for component in absolute.parts[1:]:
            parent_descriptor = directory_records[-1]["descriptor"]
            named = os.stat(
                component, dir_fd=parent_descriptor, follow_symlinks=False
            )
            if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
                raise WitnessError(
                    "capture path must be a non-symlink directory"
                )
            descriptor = os.open(
                component, directory_flags, dir_fd=parent_descriptor
            )
            directory_descriptors.append(descriptor)
            retained = os.fstat(descriptor)
            _require_exact_json(
                _file_identity(retained), _file_identity(named),
                "capture ancestor named/descriptor identity",
            )
            current = current / component
            directory_records.append(
                {
                    "descriptor": descriptor,
                    "identity": _file_identity(retained),
                    "name": component,
                    "path": current,
                }
            )

        directory = directory_records[-1]["descriptor"]
        initial_names = sorted(os.listdir(directory))
        _require_exact_json(initial_names, sorted(members), "initial capture member set")

        for name in members:
            if type(name) is not str or not name or "/" in name or "\\" in name:
                raise WitnessError("capture authority contains an unsafe member name")
            named_metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISLNK(named_metadata.st_mode) or not stat.S_ISREG(named_metadata.st_mode):
                raise WitnessError("capture member is not a named regular leaf: {0}".format(name))
            descriptor = os.open(name, member_flags, dir_fd=directory)
            descriptors[name] = descriptor
            fd_metadata = os.fstat(descriptor)
            named_before[name] = _file_identity(named_metadata)
            fd_before[name] = _file_identity(fd_metadata)
            _require_exact_json(
                fd_before[name], named_before[name], "named/descriptor identity " + name
            )
            if (
                fd_metadata.st_nlink != 1
                or stat.S_IMODE(fd_metadata.st_mode) != expected_mode
            ):
                raise WitnessError(
                    "capture member must be singly linked and exact mode {0:04o}: {1}".format(
                        expected_mode, name
                    )
                )
            if fd_metadata.st_size <= 0 or fd_metadata.st_size > maximum_bytes:
                raise WitnessError("capture member size is invalid: {0}".format(name))

        second_replay = {}  # type: Dict[str, bytes]
        for name in members:
            first_replay[name] = _read_fd_exact(
                descriptors[name], fd_before[name][7], "capture member " + name
            )
        for name in members:
            second_replay[name] = _read_fd_exact(
                descriptors[name], fd_before[name][7], "capture member " + name
            )
            _require_exact_json(
                second_replay[name], first_replay[name], "retained byte replay " + name
            )

        for name in members:
            fd_after = _file_identity(os.fstat(descriptors[name]))
            named_after = _file_identity(
                os.stat(name, dir_fd=directory, follow_symlinks=False)
            )
            _require_exact_json(fd_after, fd_before[name], "retained descriptor identity " + name)
            _require_exact_json(named_after, named_before[name], "named leaf identity " + name)
            _require_exact_json(named_after, fd_after, "final named/descriptor identity " + name)

        _require_exact_json(
            sorted(os.listdir(directory)), sorted(members),
            "retained capture member-set replay",
        )
        _replay_retained_directories(directory_records, "capture path")

        close_error = None  # type: Optional[OSError]
        for name in members:
            member_descriptor = descriptors.pop(name)
            try:
                os.close(member_descriptor)
            except OSError as error:
                if close_error is None:
                    close_error = error
        if close_error is not None:
            raise WitnessError(
                "cannot close retained capture member: {0}".format(close_error)
            )

        for name in members:
            named_after_close = os.stat(
                name, dir_fd=directory, follow_symlinks=False
            )
            if stat.S_ISLNK(named_after_close.st_mode) or not stat.S_ISREG(
                named_after_close.st_mode
            ):
                raise WitnessError(
                    "capture member changed type after descriptor close: {0}".format(name)
                )
            _require_exact_json(
                _file_identity(named_after_close), named_before[name],
                "post-member-close named leaf replay " + name,
            )
        _require_exact_json(
            sorted(os.listdir(directory)), sorted(members),
            "post-member-close capture member-set replay",
        )
        _replay_retained_directories(directory_records, "capture path after member close")

        _close_open_descriptors(directory_descriptors, "capture directory chain")
        snapshot = _closed_capture_snapshot(
            directory_records, absolute, members, named_before
        )
        _replay_closed_capture_snapshot(snapshot)
        if snapshots is not None:
            snapshots.append(snapshot)
        return first_replay
    except WitnessError:
        raise
    except OSError as error:
        raise WitnessError("cannot retain capture snapshot: {0}".format(error))
    finally:
        for descriptor in list(descriptors.values()):
            try:
                os.close(descriptor)
            except OSError:
                pass
        while directory_descriptors:
            descriptor = directory_descriptors.pop()
            try:
                os.close(descriptor)
            except OSError:
                pass


def _load_json_lines(data: bytes, label: str) -> List[Dict[str, Any]]:
    if not data.endswith(b"\n") or data.startswith(b"\xef\xbb\xbf"):
        raise WitnessError("{0} must be UTF-8 JSON lines with a final LF".format(label))
    lines = data.splitlines(True)
    if not lines or any(not line.endswith(b"\n") or line == b"\n" for line in lines):
        raise WitnessError("{0} contains a blank or unterminated record".format(label))
    records = []  # type: List[Dict[str, Any]]
    for index, line in enumerate(lines):
        record = _load_json_bytes(line, "{0} record {1}".format(label, index))
        if line != _canonical_json(record):
            raise WitnessError("{0} record {1} is not canonical".format(label, index))
        records.append(record)
    return records


def _raw_expectations(authority: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "argument": vector["argument"],
            "request": vector["request"],
            "sequence": vector["sequence"],
            "vector_id": vector["vector_id"],
        }
        for vector in authority["vectors"]
    ]


def _validate_raw(data: bytes, authority: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = _load_json_lines(data, "raw stream")
    schema = authority["schemas"]["raw"]
    _require_exact_json(len(records), schema["record_count"], "raw record count")
    _require_exact_json(records, _raw_expectations(authority), "raw vector stream")
    for record in records:
        _require_keys(record, schema["exact_keys"], "raw record")
        for key in ("argument", "request", "sequence"):
            _require_int(record[key], "raw " + key)
        if type(record["vector_id"]) is not str:
            raise WitnessError("raw vector_id must be exact text")
    return records


def _validate_results(
    data: bytes, surface: str, authority: Dict[str, Any]
) -> List[Dict[str, Any]]:
    records = _load_json_lines(data, "result stream")
    schema = authority["schemas"]["result"]
    vectors = authority["vectors"]
    encoding = authority["artifact_contract"]["surface_result_encoding"]
    if surface not in encoding:
        raise WitnessError("unknown capture surface")
    _require_exact_json(len(records), schema["record_count"], "result record count")
    expected = []  # type: List[Dict[str, Any]]
    for vector in vectors:
        expected.append(
            {
                "errno": encoding[surface]["errno"],
                "interface_return": encoding[surface]["interface_return"],
                "normalized_return": vector["expected_normalized_return"],
                "sequence": vector["sequence"],
                "surface": surface,
                "vector_id": vector["vector_id"],
            }
        )
    _require_exact_json(records, expected, "result stream")
    for record in records:
        _require_keys(record, schema["exact_keys"], "result record")
        for key in ("errno", "interface_return", "normalized_return", "sequence"):
            _require_int(record[key], "result " + key)
    return records


def _validate_ledger(
    data: bytes, surface: str, authority: Dict[str, Any]
) -> List[Dict[str, Any]]:
    records = _load_json_lines(data, "state ledger")
    schema = authority["schemas"]["state_ledger"]
    vectors = authority["vectors"]
    state_policy = authority["artifact_contract"]["surface_state_policy"]
    if surface not in state_policy:
        raise WitnessError("unknown state-ledger surface")
    _require_exact_json(len(records), schema["record_count"], "state-ledger count")
    expected_order = [
        (vectors[0]["sequence"], vectors[0]["vector_id"], "before"),
        (vectors[0]["sequence"], vectors[0]["vector_id"], "after"),
        (vectors[1]["sequence"], vectors[1]["vector_id"], "before"),
        (vectors[1]["sequence"], vectors[1]["vector_id"], "after"),
    ]
    bitmaps = []  # type: List[int]
    for record, order in zip(records, expected_order):
        _require_keys(record, schema["exact_keys"], "state-ledger record")
        _require_exact_json(record["minor63_empty"], True, "minor63-empty ledger claim")
        bitmap_text = record["occupied_minor_bitmap"]
        if type(bitmap_text) is not str or HEX16.fullmatch(bitmap_text) is None:
            raise WitnessError("state-ledger bitmap is not canonical lowercase hex")
        bitmap = int(bitmap_text, 16)
        bitmaps.append(bitmap)
        if bitmap & (1 << 63):
            raise WitnessError("minor 63 is occupied in the state ledger")
        _require_int(record["occupied_minor_count"], "occupied-minor count")
        _require_exact_json(
            record["occupied_minor_count"], bin(bitmap).count("1"),
            "occupied-minor count",
        )
        _require_int(record["sequence"], "state-ledger sequence")
        _require_exact_json(
            [record["sequence"], record["vector_id"], record["phase"]],
            list(order), "state-ledger order",
        )
        _require_exact_json(record["surface"], surface, "state-ledger surface")
    if len(set(bitmaps)) != 1:
        raise WitnessError("negative vector changed the occupied-minor state")
    if state_policy[surface] == "fresh-empty-registry" and bitmaps[0] != 0:
        raise WitnessError("standalone Rust fixture did not start from its fresh registry")
    return records


def _review_artifact_with_authority(
    authority: Dict[str, Any],
    path: Path,
    surface: str,
    capture_snapshots: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    artifact = authority["artifact_contract"]
    allowed_surfaces = [artifact["legacy_surface"], artifact["native_surface"]]
    if surface not in allowed_surfaces:
        raise WitnessError("artifact surface is not recognized")
    members = tuple(artifact["capture_members"])
    mode_text = artifact["directory_member_mode"]
    if type(mode_text) is not str or not re.fullmatch(r"0[0-7]{3}", mode_text):
        raise WitnessError("capture member mode authority is invalid")
    maximum = _require_int(artifact["maximum_member_bytes"], "maximum member bytes")
    files = _read_capture_members(
        path,
        members,
        int(mode_text, 8),
        maximum,
        snapshots=capture_snapshots,
    )
    raw = _validate_raw(files["raw.jsonl"], authority)
    results = _validate_results(files["result.jsonl"], surface, authority)
    ledger = _validate_ledger(files["state-ledger.jsonl"], surface, authority)
    rows = [
        {"name": name, "sha256": _sha256(files[name]), "size": len(files[name])}
        for name in members
    ]
    closure = _sha256(_canonical_json(rows))
    if HEX64.fullmatch(closure) is None:
        raise WitnessError("internal capture closure digest is invalid")
    return {
        "artifact_content_closure_sha256": closure,
        "capture_schema_validated": True,
        "claims": copy.deepcopy(authority["claims"]),
        "contract_id": authority["contract_id"],
        "files": rows,
        "raw_sha256": _sha256(files["raw.jsonl"]),
        "result_authority": artifact["result_authority"]["status"],
        "result_sha256": _sha256(files["result.jsonl"]),
        "state_ledger_sha256": _sha256(files["state-ledger.jsonl"]),
        "surface": surface,
        "vector_count": len(raw),
        "validated_result_count": len(results),
        "validated_state_record_count": len(ledger),
    }


def review_artifact(
    repo: Path, path: Path, surface: str, contract_path: Path = DEFAULT_CONTRACT
) -> Dict[str, Any]:
    authority, _, _, _, authority_snapshots = _load_authority(repo, contract_path)
    capture_snapshots = []  # type: List[Dict[str, Any]]
    result = _review_artifact_with_authority(
        authority, Path(path), surface, capture_snapshots
    )
    _replay_closed_file_snapshots(authority_snapshots)
    _replay_closed_capture_snapshots(capture_snapshots)
    return result


def review_artifacts(
    repo: Path, legacy_path: Path, native_path: Path,
    contract_path: Path = DEFAULT_CONTRACT,
) -> Dict[str, Any]:
    authority, _, _, _, authority_snapshots = _load_authority(repo, contract_path)
    capture_snapshots = []  # type: List[Dict[str, Any]]
    legacy_surface = authority["artifact_contract"]["legacy_surface"]
    native_surface = authority["artifact_contract"]["native_surface"]
    legacy = _review_artifact_with_authority(
        authority, Path(legacy_path), legacy_surface, capture_snapshots
    )
    native = _review_artifact_with_authority(
        authority, Path(native_path), native_surface, capture_snapshots
    )
    _require_exact_json(
        legacy["raw_sha256"], native["raw_sha256"],
        "legacy/native raw stream digest",
    )
    _replay_closed_file_snapshots(authority_snapshots)
    _replay_closed_capture_snapshots(capture_snapshots)
    return {
        "artifact_pair_validated": True,
        "claims": copy.deepcopy(authority["claims"]),
        "contract_id": authority["contract_id"],
        "legacy": legacy,
        "native": native,
        "result_authority": authority["artifact_contract"]["result_authority"]["status"],
        "status": "CAPTURED_UNREVIEWED_NONCREDITING",
        "vector_count": len(authority["vectors"]),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    contract = subparsers.add_parser("check-contract")
    contract.add_argument("--repo", type=Path, default=ROOT)
    review = subparsers.add_parser("review-artifacts")
    review.add_argument("--repo", type=Path, default=ROOT)
    review.add_argument("--legacy", type=Path, required=True)
    review.add_argument("--native", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "check-contract":
            result = validate_contract(arguments.repo)
            result["status"] = "CONTRACT_VALIDATED_NONCREDITING"
        elif arguments.command == "review-artifacts":
            result = review_artifacts(
                arguments.repo, arguments.legacy, arguments.native
            )
        else:
            parser.error("a command is required")
            return 2
    except WitnessError as error:
        print("fp0006 negative-dispatch witness error: {0}".format(error), file=sys.stderr)
        return 1
    print(_canonical_json(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
