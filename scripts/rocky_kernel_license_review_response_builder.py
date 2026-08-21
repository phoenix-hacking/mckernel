#!/usr/bin/env python3
"""Build RK-001 reviewer-response material without taking key custody.

The frozen production reviewer registry is deliberately empty, so command-line
build modes fail closed until an independently governed appointment is added.
Integrations and tests may inject a validated response-authority loader; that
loader may change only the reviewer registry.  Templates contain immutable
packet evidence and null decision fields, never machine findings presented as
reviewer conclusions.  Signing is external: this module accepts no private key
and invokes no signing command.
"""

from __future__ import print_function

import argparse
import copy
import ctypes
import errno
import hashlib
import json
import os
import shutil
import stat
import sys
import types
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path(
    "host-kernel/rocky/evidence/"
    "rk001-license-review-response-builder-ef58-v1.json"
)
AUTHORITY_SHA256 = "99d122b6ff4b35e7f83988b41958977c7f4edae705245200e885c6aa6d0d5bbf"
SCHEMA_VERSION = 1
BUILDER_ID = "rk-001-license-review-response-builder-ef58860e-v1"

MAX_AUTHORITY_BYTES = 1024 * 1024
MAX_BOUND_BYTES = 2 * 1024 * 1024
MAX_TREE_MEMBERS = 5000
MAX_TEMPLATE_BYTES = 384 * 1024 * 1024
MAX_JSON_NESTING = 64
MAX_JSON_NUMBER_TOKEN = 128

TEMPLATE_TOP_LEVEL = {
    "archive-expansions.jsonl",
    "archive-members.jsonl",
    "content-findings.jsonl",
    "support-index.jsonl",
    "template-root.json",
    "unit-decisions.jsonl",
}
PREPARED_TOP_LEVEL = {
    "archive-expansions.jsonl",
    "archive-members.jsonl",
    "content-findings.jsonl",
    "response-root.json",
    "support-index.jsonl",
    "unit-decisions.jsonl",
}

EXPECTED_CLAIMS = {
    "active_reviewer_appointment_present": False,
    "campaign_complete": False,
    "credit_eligible": False,
    "durable_archive": False,
    "independent_legal_review_complete": False,
    "private_key_custody": False,
    "response_package_complete": False,
    "tracker_credit": False,
}
EXPECTED_GATE = {
    "credit_eligible": False,
    "gate_id": "RK-001",
    "points_awarded": 0,
    "status": "TODO",
    "tracker_credit": False,
}
EXPECTED_INPUTS = {
    "campaign_authority": {
        "path": "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json",
        "sha256": "b5581cb9ad5707af65968a6e01ea69a7c46ebbe2542412c1a4cec0611da77852",
        "size": 168050,
    },
    "campaign_checker": {
        "path": "scripts/rocky_kernel_license_review_campaign.py",
        "sha256": "f5117c8af8fbf65f159cb06a69379b88f342bacccfb2aad2c5a44fe9559e3a63",
        "size": 81188,
    },
    "response_authority": {
        "path": "host-kernel/rocky/evidence/rk001-license-review-response-contract-ef58-v1.json",
        "sha256": "c71bbb5432d61106f7c86ec0f05a76e804586c57d2ad189b94e4b010bb4deaec",
        "size": 8381,
    },
    "response_checker": {
        "path": "scripts/rocky_kernel_license_review_response.py",
        "sha256": "ae27f84572bf74ef1d2ec22efd99e5aac6d117d4ef5b1fb8d7f38da823200b5c",
        "size": 93401,
    },
}
# Keep the authority's ef58860e descriptors immutable.  The current builder
# may consume a later, separately pinned implementation only to verify that
# same historical authority; this mapping cannot alter reviewer policy or
# produce credit.
CURRENT_IMPLEMENTATION_OVERRIDES = {
    EXPECTED_INPUTS["campaign_checker"]["path"]: {
        "path": EXPECTED_INPUTS["campaign_checker"]["path"],
        "sha256": "02305bcecf42e3b3919535c2104977a1a6e75fece7e5333a916a8ec4c2091f30",
        "size": 82394,
    },
    EXPECTED_INPUTS["response_checker"]["path"]: {
        "path": EXPECTED_INPUTS["response_checker"]["path"],
        "sha256": "c86eb2dbd8e8b1afcc7556d26c1d37eda886ed6660ae940e42d3b1c5e16279de",
        "size": 95089,
    },
}
EXPECTED_FILESYSTEM_POLICY = {
    "atomic_directory_publication": True,
    "directory_mode": "0555",
    "hardlinks_allowed": False,
    "member_mode": "0444",
    "namespace_replay": True,
    "replace_existing_output": False,
    "symlinks_allowed": False,
}
EXPECTED_KEY_POLICY = {
    "accept_private_key_arguments": False,
    "external_sshsig_only": True,
    "private_key_reads": False,
    "signature_namespace": "mckernel-rk001-license-review-response-v1",
}
EXPECTED_MODES = {
    "check": "verify frozen builder authority and bound campaign/response dependencies",
    "emit-template": "emit evidence-bound null-decision templates only after an active appointment",
    "finalize": "accept an externally produced SSHSIG, verify the complete response, and publish it read-only",
    "prepare-signing": "validate reviewer-authored decisions and emit canonical bytes for external signing",
}
EXPECTED_REGISTRY_POLICY = {
    "active_appointment_required": True,
    "injectable_interface": "validated-response-authority-loader-callable",
    "production_registration_status": "required-missing",
    "production_registry": "frozen-response-contract-registered-reviewers",
    "registry_injection_can_change_only": "reviewer_authority_policy",
    "self_asserted_identity_forbidden": True,
}
EXPECTED_TEMPLATE_POLICY = {
    "archive_expansion_status_default": None,
    "authorship_status_default": None,
    "content_finding_conclusion_default": None,
    "license_status_default": None,
    "machine_classification_auto_accepted": False,
    "machine_findings_copied_as_reviewer_conclusions": False,
    "provenance_status_default": None,
    "redistribution_status_default": None,
    "resolution_status_default": None,
    "reviewer_attestations_default": None,
}
EXPECTED_BLOCKERS = [
    "The frozen production response contract has no registered independent reviewer appointment.",
    "No reviewer-authored packet decisions or externally produced SSHSIG are present.",
    "Two archive containers still require successor v2 child inventories.",
    "No aggregate 219-packet response index exists.",
    "No durable immutable response archive authority exists.",
    "This builder cannot award RK-001 or tracker credit.",
]


class ResponseBuilderError(RuntimeError):
    """Raised when builder authority, input, or output fails closed."""


def reject_duplicate_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ResponseBuilderError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def parse_bounded_json_int(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ResponseBuilderError("JSON integer token exceeds its cap")
    try:
        return int(token, 10)
    except ValueError as error:
        raise ResponseBuilderError("JSON integer token is invalid: {0}".format(error))


def reject_json_float(token):
    if type(token) is not str or len(token) > MAX_JSON_NUMBER_TOKEN:
        raise ResponseBuilderError("JSON float token exceeds its cap")
    raise ResponseBuilderError("JSON floating-point values are forbidden")


def reject_json_constant(token):
    raise ResponseBuilderError("nonfinite JSON value is forbidden: {0}".format(token))


def require_bounded_json_nesting(value):
    stack = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_NESTING:
            raise ResponseBuilderError("JSON nesting exceeds its cap")
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend((item, depth + 1) for item in current)


def canonical_json(value, newline=False):
    require_bounded_json_nesting(value)
    try:
        data = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (RecursionError, TypeError, ValueError) as error:
        raise ResponseBuilderError("value is not canonical JSON: {0}".format(error))
    return data + (b"\n" if newline else b"")


def read_json_bytes(data, label, canonical=False):
    try:
        value = json.loads(
            data.decode("ascii"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_json_constant,
            parse_float=reject_json_float,
            parse_int=parse_bounded_json_int,
        )
    except ResponseBuilderError:
        raise
    except (RecursionError, UnicodeError, ValueError) as error:
        raise ResponseBuilderError("{0} is not valid JSON: {1}".format(label, error))
    require_bounded_json_nesting(value)
    if type(value) is not dict:
        raise ResponseBuilderError("{0} must be a JSON object".format(label))
    if canonical and data != canonical_json(value, newline=True):
        raise ResponseBuilderError("{0} is not canonical JSON".format(label))
    return value


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ResponseBuilderError("{0} fields changed".format(label))
    return value


def require_exact(actual, expected, label):
    if type(actual) is not type(expected):
        raise ResponseBuilderError("{0} type changed".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ResponseBuilderError("{0} fields changed".format(label))
        for key in expected:
            require_exact(actual[key], expected[key], label + "." + str(key))
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise ResponseBuilderError("{0} length changed".format(label))
        for index, pair in enumerate(zip(actual, expected)):
            require_exact(pair[0], pair[1], label + "[{0}]".format(index))
        return
    if actual != expected:
        raise ResponseBuilderError(
            "{0} differs: {1!r} != {2!r}".format(label, actual, expected)
        )


def safe_relative(value, label):
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise ResponseBuilderError("{0} is unsafe".format(label))
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ResponseBuilderError("{0} is not normalized".format(label))
    return value


def _stat_identity(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_uid,
        info.st_gid,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _read_regular_file_once(path, label, cap, hardlink_forbidden=True):
    raw = str(path)
    parts = raw.split(os.sep)
    comparable = parts[1:] if os.path.isabs(raw) else parts
    if (
        not raw
        or "\x00" in raw
        or "\\" in raw
        or any(part in ("", ".", "..") for part in comparable)
    ):
        raise ResponseBuilderError("{0} path is unsafe".format(label))
    requested = Path(os.path.abspath(raw))
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    chain = []
    file_descriptor = None
    try:
        current = os.open(requested.anchor, directory_flags)
        root_info = os.fstat(current)
        if not stat.S_ISDIR(root_info.st_mode):
            raise ResponseBuilderError("{0} root is not a directory".format(label))
        chain.append(
            {
                "descriptor": current,
                "identity": _stat_identity(root_info),
                "name": None,
                "parent_fd": None,
            }
        )
        for component in requested.parts[1:-1]:
            if component in ("", ".", "..") or os.sep in component:
                raise ResponseBuilderError("{0} component is unsafe".format(label))
            following = os.open(component, directory_flags, dir_fd=current)
            opened = os.fstat(following)
            named = os.stat(component, dir_fd=current, follow_symlinks=False)
            if not stat.S_ISDIR(opened.st_mode) or _stat_identity(opened) != _stat_identity(named):
                os.close(following)
                raise ResponseBuilderError("{0} directory identity changed".format(label))
            chain.append(
                {
                    "descriptor": following,
                    "identity": _stat_identity(opened),
                    "name": component,
                    "parent_fd": current,
                }
            )
            current = following
        filename = requested.parts[-1]
        if filename in ("", ".", "..") or os.sep in filename:
            raise ResponseBuilderError("{0} filename is unsafe".format(label))
        file_descriptor = os.open(filename, file_flags, dir_fd=current)
        opened = os.fstat(file_descriptor)
        named = os.stat(filename, dir_fd=current, follow_symlinks=False)
        identity = _stat_identity(opened)
        if (
            not stat.S_ISREG(opened.st_mode)
            or identity != _stat_identity(named)
            or opened.st_size > cap
            or (hardlink_forbidden and opened.st_nlink != 1)
        ):
            raise ResponseBuilderError("{0} is not a bounded unique regular file".format(label))

        def replay():
            for record in chain:
                chain_opened = os.fstat(record["descriptor"])
                chain_named = (
                    chain_opened
                    if record["parent_fd"] is None
                    else os.stat(
                        record["name"],
                        dir_fd=record["parent_fd"],
                        follow_symlinks=False,
                    )
                )
                if (
                    _stat_identity(chain_opened) != record["identity"]
                    or _stat_identity(chain_named) != record["identity"]
                ):
                    raise ResponseBuilderError(
                        "{0} ancestor namespace changed".format(label)
                    )
            current_opened = os.fstat(file_descriptor)
            current_named = os.stat(filename, dir_fd=current, follow_symlinks=False)
            if (
                _stat_identity(current_opened) != identity
                or _stat_identity(current_named) != identity
            ):
                raise ResponseBuilderError("{0} namespace changed".format(label))

        def read_pass():
            replay()
            os.lseek(file_descriptor, 0, os.SEEK_SET)
            remaining = opened.st_size
            chunks = []
            while remaining:
                chunk = os.read(file_descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    raise ResponseBuilderError("{0} ended early".format(label))
                chunks.append(chunk)
                remaining -= len(chunk)
                replay()
            if os.read(file_descriptor, 1):
                raise ResponseBuilderError("{0} grew while read".format(label))
            replay()
            return b"".join(chunks)

        first = read_pass()
        second = read_pass()
        if first != second:
            raise ResponseBuilderError("{0} replay differs".format(label))
        replay()
        return second
    except ResponseBuilderError:
        raise
    except OSError as error:
        raise ResponseBuilderError("cannot read {0}: {1}".format(label, error))
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        for record in reversed(chain):
            try:
                os.close(record["descriptor"])
            except OSError:
                pass


def validate_authority(authority):
    exact_keys(
        authority,
        {
            "builder_id",
            "claims",
            "filesystem_policy",
            "gate",
            "inputs",
            "key_policy",
            "modes",
            "registry_policy",
            "remaining_blockers",
            "schema_version",
            "template_policy",
        },
        "response-builder authority",
    )
    require_exact(authority["schema_version"], SCHEMA_VERSION, "schema version")
    require_exact(authority["builder_id"], BUILDER_ID, "builder ID")
    require_exact(authority["claims"], EXPECTED_CLAIMS, "claims")
    require_exact(authority["gate"], EXPECTED_GATE, "gate")
    require_exact(authority["inputs"], EXPECTED_INPUTS, "bound inputs")
    require_exact(
        authority["filesystem_policy"],
        EXPECTED_FILESYSTEM_POLICY,
        "filesystem policy",
    )
    require_exact(authority["key_policy"], EXPECTED_KEY_POLICY, "key policy")
    require_exact(authority["modes"], EXPECTED_MODES, "modes")
    require_exact(
        authority["registry_policy"], EXPECTED_REGISTRY_POLICY, "registry policy"
    )
    require_exact(
        authority["template_policy"], EXPECTED_TEMPLATE_POLICY, "template policy"
    )
    require_exact(authority["remaining_blockers"], EXPECTED_BLOCKERS, "blockers")
    return authority


def load_authority(repo=REPO_ROOT, explicit=None):
    path = Path(explicit) if explicit is not None else Path(repo) / AUTHORITY_PATH
    data = _read_regular_file_once(path, "response-builder authority", MAX_AUTHORITY_BYTES)
    if hashlib.sha256(data).hexdigest() != AUTHORITY_SHA256:
        raise ResponseBuilderError("response-builder authority digest differs")
    return validate_authority(
        read_json_bytes(data, "response-builder authority", canonical=True)
    )


def _load_bound_module(repo, record, name, label):
    exact_keys(record, {"path", "sha256", "size"}, label + " descriptor")
    active_record = CURRENT_IMPLEMENTATION_OVERRIDES.get(record["path"], record)
    require_exact(active_record["path"], record["path"], label + " compatibility path")
    path = Path(repo) / safe_relative(active_record["path"], label + " path")
    data = _read_regular_file_once(path, label, MAX_BOUND_BYTES)
    if (
        len(data) != active_record["size"]
        or hashlib.sha256(data).hexdigest() != active_record["sha256"]
    ):
        raise ResponseBuilderError("{0} bytes differ".format(label))
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    try:
        code = compile(data, str(path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
    except (Exception, MemoryError) as error:
        raise ResponseBuilderError("cannot execute {0}: {1}".format(label, error))
    return module


def load_dependencies(repo, authority):
    repo = Path(repo).resolve()
    campaign_module = _load_bound_module(
        repo,
        authority["inputs"]["campaign_checker"],
        "_rk001_builder_campaign_v1",
        "bound campaign checker",
    )
    response_module = _load_bound_module(
        repo,
        authority["inputs"]["response_checker"],
        "_rk001_builder_response_v1",
        "bound response checker",
    )
    for key, module, digest_name in (
        ("campaign_authority", campaign_module, "AUTHORITY_SHA256"),
        ("response_authority", response_module, "AUTHORITY_SHA256"),
    ):
        record = authority["inputs"][key]
        path = repo / safe_relative(record["path"], key + " path")
        data = _read_regular_file_once(path, "bound " + key, MAX_AUTHORITY_BYTES)
        if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ResponseBuilderError("bound {0} bytes differ".format(key))
        require_exact(getattr(module, digest_name), record["sha256"], key + " module digest")
    try:
        campaign_authority = campaign_module.load_authority(
            repo, repo / authority["inputs"]["campaign_authority"]["path"]
        )
        response_authority = response_module.load_authority(
            repo, repo / authority["inputs"]["response_authority"]["path"]
        )
        response_module.load_campaign_checker(repo, response_authority)
    except Exception as error:
        raise ResponseBuilderError("bound dependency validation failed: {0}".format(error))
    require_exact(
        campaign_authority["campaign_id"],
        response_module.CAMPAIGN_ID,
        "campaign/response ID",
    )
    return {
        "campaign": campaign_module,
        "campaign_authority": campaign_authority,
        "response": response_module,
        "response_authority": response_authority,
    }


def load_registry(response_module, production_authority, registry_loader=None):
    """Return a validated registry, allowing injection of reviewer policy only."""

    baseline = copy.deepcopy(production_authority)
    try:
        response_module.validate_authority(copy.deepcopy(baseline))
    except Exception as error:
        raise ResponseBuilderError("production reviewer authority is invalid: {0}".format(error))
    if registry_loader is None:
        registry = copy.deepcopy(baseline)
    else:
        if not callable(registry_loader):
            raise ResponseBuilderError("reviewer registry loader is not callable")
        try:
            registry = registry_loader(copy.deepcopy(baseline))
        except Exception as error:
            raise ResponseBuilderError("reviewer registry loader failed: {0}".format(error))
    try:
        response_module.validate_authority(copy.deepcopy(registry))
    except Exception as error:
        raise ResponseBuilderError("reviewer registry authority is invalid: {0}".format(error))
    comparison = copy.deepcopy(registry)
    comparison["reviewer_authority_policy"] = copy.deepcopy(
        baseline["reviewer_authority_policy"]
    )
    try:
        response_module.require_exact(
            comparison, baseline, "injected registry non-reviewer fields"
        )
    except Exception as error:
        raise ResponseBuilderError("registry injection changed frozen policy: {0}".format(error))
    return registry


def active_appointment(
    response_module,
    registry,
    reviewer_authority_id,
    reviewer_identity,
    packet_id,
    review_completed_at,
):
    try:
        response_module.validate_authority(copy.deepcopy(registry))
    except Exception as error:
        raise ResponseBuilderError("reviewer appointment registry is invalid: {0}".format(error))
    if (
        type(packet_id) is not str
        or not response_module.PACKET_ID_PATTERN.fullmatch(packet_id)
        or not ("0001" <= packet_id <= "0219")
    ):
        raise ResponseBuilderError("reviewer appointment packet ID is malformed")
    policy = registry["reviewer_authority_policy"]
    if policy["registration_status"] != "registered":
        raise ResponseBuilderError(
            "no active production reviewer appointment; registry status={0}".format(
                policy["registration_status"]
            )
        )
    matches = [
        record
        for record in policy["registered_reviewers"]
        if record["authority_id"] == reviewer_authority_id
        and record["reviewer_identity"] == reviewer_identity
    ]
    if len(matches) != 1:
        raise ResponseBuilderError("reviewer appointment is not uniquely registered")
    reviewer = matches[0]
    try:
        response_module.validate_reviewer(copy.deepcopy(reviewer))
        response_module.require_utc_timestamp(review_completed_at, "review completed time")
    except Exception as error:
        raise ResponseBuilderError("reviewer appointment input is invalid: {0}".format(error))
    if not (reviewer["packet_min"] <= packet_id <= reviewer["packet_max"]):
        raise ResponseBuilderError("reviewer appointment does not cover this packet")
    if not (reviewer["valid_from"] <= review_completed_at <= reviewer["valid_through"]):
        raise ResponseBuilderError("review time is outside the appointment interval")
    return copy.deepcopy(reviewer)


def load_verified_packet(repo, dependencies, artifact, packet_id, packet_directory):
    campaign_module = dependencies["campaign"]
    response_module = dependencies["response"]
    try:
        derived = campaign_module.derive_campaign(
            Path(repo).resolve(), Path(artifact), dependencies["campaign_authority"]
        )
        campaign_module.verify_package(
            dependencies["campaign_authority"],
            derived,
            packet_id,
            Path(packet_directory),
        )
        metadata = campaign_module.packet_metadata_files(
            dependencies["campaign_authority"], derived, packet_id
        )
        groups = response_module.parse_jsonl(
            metadata["content-groups.jsonl"],
            "campaign content groups",
            response_module.MAX_FINDING_RECORDS,
        )
        units = response_module.parse_jsonl(
            metadata["review-units.jsonl"],
            "campaign review units",
            response_module.MAX_UNIT_RECORDS,
        )
    except Exception as error:
        raise ResponseBuilderError("campaign packet verification failed: {0}".format(error))
    return groups, units


def _validate_packet_material(response_module, groups, units, packet_id):
    if type(packet_id) is not str or not response_module.PACKET_ID_PATTERN.fullmatch(packet_id):
        raise ResponseBuilderError("packet ID is malformed")
    if not ("0001" <= packet_id <= "0219"):
        raise ResponseBuilderError("packet ID is outside the campaign")
    if type(groups) is not list or type(units) is not list:
        raise ResponseBuilderError("packet groups and units must be lists")
    if not groups or not units:
        raise ResponseBuilderError("packet material is empty")
    if len(groups) > response_module.MAX_FINDING_RECORDS:
        raise ResponseBuilderError("packet content-group count exceeds its cap")
    if len(units) > response_module.MAX_UNIT_RECORDS:
        raise ResponseBuilderError("packet unit count exceeds its cap")
    group_ids = []
    for group in groups:
        if type(group) is not dict:
            raise ResponseBuilderError("packet content group is not an object")
        group_id = group.get("group_id")
        identity = group.get("identity")
        if (
            type(group_id) is not str
            or type(identity) is not dict
            or type(identity.get("sha256")) is not str
            or type(identity.get("size")) is not int
        ):
            raise ResponseBuilderError("packet content group identity is malformed")
        response_module.require_sha256(identity["sha256"], "packet content digest")
        response_module.require_nonnegative_int(identity["size"], "packet content size")
        group_ids.append(group_id)
    if len(group_ids) != len(set(group_ids)):
        raise ResponseBuilderError("packet content groups are duplicated")
    unit_ids = []
    known_groups = set(group_ids)
    for unit in units:
        if type(unit) is not dict or type(unit.get("evidence")) is not dict:
            raise ResponseBuilderError("packet review unit is malformed")
        for key in ("unit_id", "context_group_id", "exact_content_group_id"):
            if key not in unit:
                raise ResponseBuilderError("packet review unit lacks {0}".format(key))
        evidence = unit["evidence"]
        for key in ("path", "namespace", "origin", "source_identity"):
            if key not in evidence:
                raise ResponseBuilderError("packet evidence lacks {0}".format(key))
        if unit["exact_content_group_id"] is not None and unit["exact_content_group_id"] not in known_groups:
            raise ResponseBuilderError("packet unit references an unknown content group")
        unit_ids.append(unit["unit_id"])
    if len(unit_ids) != len(set(unit_ids)):
        raise ResponseBuilderError("packet review units are duplicated")


def _template_root(
    authority,
    response_authority,
    packet_id,
    reviewer,
    review_completed_at,
    campaign_authority_sha256,
    groups,
    units,
):
    return {
        "builder_authority_sha256": AUTHORITY_SHA256,
        "builder_id": authority["builder_id"],
        "campaign_authority_sha256": campaign_authority_sha256,
        "campaign_id": response_authority["campaign_closure"]["campaign_id"],
        "claims": copy.deepcopy(EXPECTED_CLAIMS),
        "content_group_count": len(groups),
        "packet_id": packet_id,
        "response_contract_id": response_authority["response_contract_id"],
        "review_completed_at": review_completed_at,
        "reviewer_attestations": {
            "all_units_individually_reviewed": None,
            "archive_expansion_complete": None,
            "independent_from_capture": None,
        },
        "reviewer_authority_id": reviewer["authority_id"],
        "reviewer_identity": reviewer["reviewer_identity"],
        "reviewer_key_fingerprint": reviewer["ssh_fingerprint"],
        "schema_version": 1,
        "unit_count": len(units),
    }


TEMPLATE_ROOT_KEYS = {
    "builder_authority_sha256",
    "builder_id",
    "campaign_authority_sha256",
    "campaign_id",
    "claims",
    "content_group_count",
    "packet_id",
    "response_contract_id",
    "review_completed_at",
    "reviewer_attestations",
    "reviewer_authority_id",
    "reviewer_identity",
    "reviewer_key_fingerprint",
    "schema_version",
    "unit_count",
}


def emit_template_data(
    authority,
    response_module,
    response_authority,
    groups,
    units,
    packet_id,
    reviewer,
    review_completed_at,
    campaign_authority_sha256,
):
    """Return null-decision template files for a verified packet."""

    _validate_packet_material(response_module, groups, units, packet_id)
    appointed = active_appointment(
        response_module,
        response_authority,
        reviewer.get("authority_id") if type(reviewer) is dict else None,
        reviewer.get("reviewer_identity") if type(reviewer) is dict else None,
        packet_id,
        review_completed_at,
    )
    try:
        response_module.require_exact(appointed, reviewer, "template reviewer appointment")
    except Exception as error:
        raise ResponseBuilderError("template reviewer appointment differs: {0}".format(error))
    response_module.require_sha256(
        campaign_authority_sha256, "template campaign authority digest"
    )
    findings = []
    for group in groups:
        findings.append(
            {
                "conclusion": None,
                "content_finding_id": None,
                "content_group_id": group["group_id"],
                "content_sha256": group["identity"]["sha256"],
                "content_size": group["identity"]["size"],
                "reviewer_identity": reviewer["reviewer_identity"],
                "spdx_expression_or_unresolved": None,
                "support_reference_ids": [],
            }
        )
    decisions = []
    for unit in units:
        evidence = unit["evidence"]
        decisions.append(
            {
                "authorship_status": None,
                "content_finding_id": None,
                "context_group_id": unit["context_group_id"],
                "license_status": None,
                "namespace": evidence["namespace"],
                "origin": evidence["origin"],
                "path": evidence["path"],
                "provenance_status": None,
                "redistribution_status": None,
                "resolved_or_unresolved": None,
                "reviewer_identity": reviewer["reviewer_identity"],
                "signed_response_root": None,
                "source_identity": evidence["source_identity"],
                "support_reference_ids": [],
                "unit_evidence_sha256": hashlib.sha256(
                    response_module.canonical_json(unit)
                ).hexdigest(),
                "unit_id": unit["unit_id"],
            }
        )
    archive_rows = []
    if packet_id == "0218":
        for binding in response_authority["campaign_closure"]["archive_bindings"]:
            container = binding["container"]
            archive_rows.append(
                {
                    "archive_binding_sha256": hashlib.sha256(
                        response_module.canonical_json(binding)
                    ).hexdigest(),
                    "archive_group_id": container["group_id"],
                    "container_path": container["path"],
                    "container_sha256": container["sha256"],
                    "container_size": container["size"],
                    "expansion_role": binding["role"],
                    "expansion_status": None,
                    "member_count": None,
                    "member_stream_sha256": None,
                    "member_stream_size": None,
                    "reviewer_identity": reviewer["reviewer_identity"],
                    "support_reference_ids": [],
                }
            )
    root = _template_root(
        authority,
        response_authority,
        packet_id,
        reviewer,
        review_completed_at,
        campaign_authority_sha256,
        groups,
        units,
    )
    return {
        "archive-expansions.jsonl": response_module.canonical_stream(archive_rows),
        "archive-members.jsonl": b"",
        "content-findings.jsonl": response_module.canonical_stream(findings),
        "support-index.jsonl": b"",
        "template-root.json": response_module.canonical_json(root, newline=True),
        "unit-decisions.jsonl": response_module.canonical_stream(decisions),
    }


def _validate_template_root(
    authority,
    response_module,
    response_authority,
    root,
    groups,
    units,
    packet_id,
    reviewer,
    review_completed_at,
    campaign_authority_sha256,
):
    exact_keys(root, TEMPLATE_ROOT_KEYS, "template root")
    expected = _template_root(
        authority,
        response_authority,
        packet_id,
        reviewer,
        review_completed_at,
        campaign_authority_sha256,
        groups,
        units,
    )
    attestations = exact_keys(
        root["reviewer_attestations"],
        {
            "all_units_individually_reviewed",
            "archive_expansion_complete",
            "independent_from_capture",
        },
        "template reviewer attestations",
    )
    comparison = copy.deepcopy(root)
    comparison["reviewer_attestations"] = expected["reviewer_attestations"]
    require_exact(comparison, expected, "template root binding")
    for key in attestations:
        if type(attestations[key]) is not bool:
            raise ResponseBuilderError(
                "reviewer must explicitly set template attestation {0}".format(key)
            )
    require_exact(
        attestations["all_units_individually_reviewed"],
        True,
        "all-units-reviewed attestation",
    )
    require_exact(
        attestations["independent_from_capture"],
        True,
        "independent-from-capture attestation",
    )
    response_module.require_exact(root["claims"], EXPECTED_CLAIMS, "template claims")
    return attestations


def _parse_draft(response_module, files):
    non_support = {name for name in files if not name.startswith("support/")}
    if non_support != TEMPLATE_TOP_LEVEL:
        raise ResponseBuilderError("draft response file closure differs")
    try:
        root = response_module.read_json_bytes(
            files["template-root.json"], "template root", canonical=True
        )
        records = {
            "archive_expansions": response_module.parse_jsonl(
                files["archive-expansions.jsonl"],
                "draft archive expansions",
                response_module.MAX_ARCHIVE_RECORDS,
            ),
            "archive_members": response_module.parse_jsonl(
                files["archive-members.jsonl"],
                "draft archive members",
                response_module.MAX_ARCHIVE_MEMBER_RECORDS,
            ),
            "content_findings": response_module.parse_jsonl(
                files["content-findings.jsonl"],
                "draft content findings",
                response_module.MAX_FINDING_RECORDS,
            ),
            "support_index": response_module.parse_jsonl(
                files["support-index.jsonl"],
                "draft support index",
                response_module.MAX_SUPPORT_RECORDS,
            ),
            "unit_decisions": response_module.parse_jsonl(
                files["unit-decisions.jsonl"],
                "draft unit decisions",
                response_module.MAX_UNIT_RECORDS,
            ),
        }
    except Exception as error:
        raise ResponseBuilderError("draft response parsing failed: {0}".format(error))
    return root, records


def _normalize_findings(response_module, records, groups, reviewer_identity):
    if len(records) != len(groups):
        raise ResponseBuilderError("draft content-finding count differs from the packet")
    by_group = {}
    for record in records:
        try:
            response_module.exact_keys(
                record, response_module.CONTENT_FINDING_KEYS, "draft content finding"
            )
        except Exception as error:
            raise ResponseBuilderError("draft content finding fields differ: {0}".format(error))
        group_id = record.get("content_group_id")
        if group_id in by_group:
            raise ResponseBuilderError("draft content group has duplicate findings")
        by_group[group_id] = record
    normalized = []
    for group in groups:
        group_id = group["group_id"]
        if group_id not in by_group:
            raise ResponseBuilderError("draft content finding closure differs")
        record = copy.deepcopy(by_group[group_id])
        for key, expected in (
            ("content_sha256", group["identity"]["sha256"]),
            ("content_size", group["identity"]["size"]),
            ("reviewer_identity", reviewer_identity),
        ):
            require_exact(record[key], expected, "draft content finding " + key)
        if record["conclusion"] not in ("resolved", "unresolved"):
            raise ResponseBuilderError("reviewer must author every content conclusion")
        if record["conclusion"] == "resolved":
            try:
                expression = response_module.require_string(
                    record["spdx_expression_or_unresolved"],
                    "reviewer SPDX expression",
                    16384,
                )
            except Exception as error:
                raise ResponseBuilderError("reviewer SPDX expression is invalid: {0}".format(error))
            if expression == "unresolved":
                raise ResponseBuilderError("resolved finding has an unresolved expression")
        else:
            require_exact(
                record["spdx_expression_or_unresolved"],
                "unresolved",
                "unresolved finding expression",
            )
        if type(record["support_reference_ids"]) is not list:
            raise ResponseBuilderError("content finding support references are not a list")
        supplied_id = record["content_finding_id"]
        payload = dict(record)
        del payload["content_finding_id"]
        derived_id = response_module.stable_id("content-finding", payload)
        if supplied_id not in (None, derived_id):
            raise ResponseBuilderError("draft content finding ID is not null or derived")
        record["content_finding_id"] = derived_id
        normalized.append(record)
    normalized.sort(key=lambda item: item["content_finding_id"])
    return normalized


def _normalize_decisions(
    response_module, records, units, findings_by_group, reviewer_identity
):
    if len(records) != len(units):
        raise ResponseBuilderError("draft unit-decision count differs from the packet")
    by_unit = {}
    for record in records:
        try:
            response_module.exact_keys(
                record, response_module.UNIT_DECISION_KEYS, "draft unit decision"
            )
        except Exception as error:
            raise ResponseBuilderError("draft unit decision fields differ: {0}".format(error))
        unit_id = record.get("unit_id")
        if unit_id in by_unit:
            raise ResponseBuilderError("draft unit decision is duplicated")
        by_unit[unit_id] = record
    normalized = []
    for unit in units:
        unit_id = unit["unit_id"]
        if unit_id not in by_unit:
            raise ResponseBuilderError("draft unit-decision closure differs")
        record = copy.deepcopy(by_unit[unit_id])
        evidence = unit["evidence"]
        for key, expected in (
            ("context_group_id", unit["context_group_id"]),
            ("namespace", evidence["namespace"]),
            ("origin", evidence["origin"]),
            ("path", evidence["path"]),
            ("reviewer_identity", reviewer_identity),
            ("source_identity", evidence["source_identity"]),
            (
                "unit_evidence_sha256",
                hashlib.sha256(response_module.canonical_json(unit)).hexdigest(),
            ),
        ):
            require_exact(record[key], expected, "draft unit decision " + key)
        if record["signed_response_root"] is not None:
            raise ResponseBuilderError("draft unit decision must not supply a signed root")
        group_id = unit["exact_content_group_id"]
        expected_finding = None if group_id is None else findings_by_group[group_id]
        expected_finding_id = (
            None if expected_finding is None else expected_finding["content_finding_id"]
        )
        if record["content_finding_id"] not in (None, expected_finding_id):
            raise ResponseBuilderError("draft unit content-finding link differs")
        record["content_finding_id"] = expected_finding_id
        statuses = {
            "authorship_status": ("affirmed", "unresolved"),
            "license_status": ("affirmed", "unresolved"),
            "provenance_status": ("affirmed", "unresolved"),
            "redistribution_status": ("approved", "not-approved", "unresolved"),
            "resolved_or_unresolved": ("resolved", "unresolved"),
        }
        for key, allowed in statuses.items():
            if record[key] not in allowed:
                raise ResponseBuilderError(
                    "reviewer must author unit field {0}".format(key)
                )
        affirmative = (
            record["authorship_status"] == "affirmed"
            and record["license_status"] == "affirmed"
            and record["provenance_status"] == "affirmed"
            and record["redistribution_status"] == "approved"
            and record["resolved_or_unresolved"] == "resolved"
            and (expected_finding is None or expected_finding["conclusion"] == "resolved")
        )
        if record["resolved_or_unresolved"] == "resolved" and not affirmative:
            raise ResponseBuilderError("resolved unit contradicts reviewer-authored statuses")
        if type(record["support_reference_ids"]) is not list:
            raise ResponseBuilderError("unit support references are not a list")
        normalized.append(record)
    return normalized


def prepare_signing_data(
    authority,
    response_module,
    registry,
    groups,
    units,
    packet_id,
    reviewer,
    review_completed_at,
    campaign_authority_sha256,
    draft_files,
):
    """Validate authored draft data and return an unsigned canonical package."""

    _validate_packet_material(response_module, groups, units, packet_id)
    appointed = active_appointment(
        response_module,
        registry,
        reviewer.get("authority_id") if type(reviewer) is dict else None,
        reviewer.get("reviewer_identity") if type(reviewer) is dict else None,
        packet_id,
        review_completed_at,
    )
    try:
        response_module.require_exact(appointed, reviewer, "draft reviewer appointment")
    except Exception as error:
        raise ResponseBuilderError("draft reviewer appointment differs: {0}".format(error))
    root_template, records = _parse_draft(response_module, draft_files)
    attestations = _validate_template_root(
        authority,
        response_module,
        registry,
        root_template,
        groups,
        units,
        packet_id,
        reviewer,
        review_completed_at,
        campaign_authority_sha256,
    )
    try:
        support = response_module.validate_support(
            records["support_index"], draft_files
        )
    except Exception as error:
        raise ResponseBuilderError("draft support validation failed: {0}".format(error))
    findings = _normalize_findings(
        response_module,
        records["content_findings"],
        groups,
        reviewer["reviewer_identity"],
    )
    findings_by_group = {record["content_group_id"]: record for record in findings}
    decisions = _normalize_decisions(
        response_module,
        records["unit_decisions"],
        units,
        findings_by_group,
        reviewer["reviewer_identity"],
    )
    archive_expansions = copy.deepcopy(records["archive_expansions"])
    archive_members = copy.deepcopy(records["archive_members"])
    support_index = copy.deepcopy(records["support_index"])
    files = {
        "archive-expansions.jsonl": response_module.canonical_stream(archive_expansions),
        "archive-members.jsonl": response_module.canonical_stream(archive_members),
        "content-findings.jsonl": response_module.canonical_stream(findings),
        "support-index.jsonl": response_module.canonical_stream(support_index),
    }
    for name, data in draft_files.items():
        if name.startswith("support/"):
            files[name] = data
    payload_stream = response_module.unit_payload_stream(decisions)
    unit_bytes_with_placeholder = response_module.canonical_stream(decisions)
    streams = {
        "archive_expansions": response_module.stream_descriptor(
            "archive-expansions.jsonl", files["archive-expansions.jsonl"], archive_expansions
        ),
        "archive_members": response_module.stream_descriptor(
            "archive-members.jsonl", files["archive-members.jsonl"], archive_members
        ),
        "content_findings": response_module.stream_descriptor(
            "content-findings.jsonl", files["content-findings.jsonl"], findings
        ),
        "support_index": response_module.stream_descriptor(
            "support-index.jsonl", files["support-index.jsonl"], support_index
        ),
        "unit_decisions": response_module.stream_descriptor(
            "unit-decisions.jsonl", unit_bytes_with_placeholder, decisions
        ),
    }
    streams["unit_decisions"].update(
        {
            "payload_sha256": hashlib.sha256(payload_stream).hexdigest(),
            "payload_size": len(payload_stream),
        }
    )
    root = {
        "attestations": {
            "all_units_individually_reviewed": attestations[
                "all_units_individually_reviewed"
            ],
            "archive_expansion_complete": attestations["archive_expansion_complete"],
            "content_findings_auto_resolve_paths": False,
            "credit_eligible": False,
            "durable_archive": False,
            "independent_from_capture": attestations["independent_from_capture"],
            "machine_classification_auto_accepted": False,
            "tracker_credit": False,
        },
        "campaign_authority_sha256": campaign_authority_sha256,
        "campaign_id": response_module.CAMPAIGN_ID,
        "packet_id": packet_id,
        "response_contract_id": response_module.CONTRACT_ID,
        "review_completed_at": review_completed_at,
        "reviewer_authority_id": reviewer["authority_id"],
        "reviewer_identity": reviewer["reviewer_identity"],
        "reviewer_key_fingerprint": reviewer["ssh_fingerprint"],
        "schema_version": 1,
        "signed_response_root": "rk001-response-root:" + "0" * 64,
        "streams": streams,
    }
    root["signed_response_root"] = response_module.signed_response_root(root)
    for record in decisions:
        record["signed_response_root"] = root["signed_response_root"]
    files["unit-decisions.jsonl"] = response_module.canonical_stream(decisions)
    root["streams"]["unit_decisions"].update(
        response_module.stream_descriptor(
            "unit-decisions.jsonl", files["unit-decisions.jsonl"], decisions
        )
    )
    try:
        response_module.validate_root(root, registry)
        response_module.find_reviewer(registry, root)
        response_module.validate_findings(
            findings, groups, reviewer["reviewer_identity"], support
        )
        response_module.validate_unit_decisions(
            decisions, units, findings_by_group, root, support
        )
        archive_complete = response_module.validate_archive_expansions(
            archive_expansions,
            archive_members,
            registry,
            reviewer["reviewer_identity"],
            support,
            packet_id,
        )
        response_module.require_exact(
            attestations["archive_expansion_complete"],
            archive_complete,
            "reviewer archive-complete attestation",
        )
    except Exception as error:
        raise ResponseBuilderError("prepared response validation failed: {0}".format(error))
    files["response-root.json"] = response_module.canonical_json(root, newline=True)
    return files


def finalize_data(
    response_module,
    registry,
    groups,
    units,
    expected_packet_id,
    campaign_authority_sha256,
    prepared_files,
    signature_bytes,
):
    """Attach an external signature, verify it, and return complete files/result."""

    _validate_packet_material(response_module, groups, units, expected_packet_id)
    non_support = {name for name in prepared_files if not name.startswith("support/")}
    if non_support != PREPARED_TOP_LEVEL:
        raise ResponseBuilderError("prepared response file closure differs")
    if type(signature_bytes) is not bytes or not signature_bytes:
        raise ResponseBuilderError("external SSHSIG is empty")
    if len(signature_bytes) > response_module.MAX_SIGNATURE_BYTES:
        raise ResponseBuilderError("external SSHSIG exceeds its cap")
    files = dict(prepared_files)
    files["response-root.sig"] = signature_bytes
    files["SHA256SUMS"] = response_module._checksum_manifest(files)
    try:
        result = response_module.verify_response_data(
            registry,
            groups,
            units,
            files,
            campaign_authority_sha256,
        )
    except Exception as error:
        raise ResponseBuilderError("externally signed response failed verification: {0}".format(error))
    for key, expected in (
        ("campaign_complete", False),
        ("credit_eligible", False),
        ("durable_archive", False),
        ("points_awarded", 0),
        ("tracker_credit", False),
    ):
        require_exact(result[key], expected, "final response " + key)
    require_exact(
        result["packet_id"], expected_packet_id, "final response packet ID"
    )
    return files, result


def read_exact_tree(response_module, directory, top_level, label):
    """Read an exact read-only directory tree with descriptor-rooted replay."""

    root = response_module._open_dir(Path(directory), label + " root")
    support = None
    members = {}
    try:
        names = response_module._list_dir(root, len(top_level) + 1)
        root["expected_names"] = names
        actual = set(names)
        support_present = "support" in actual
        actual.discard("support")
        if actual != set(top_level):
            raise ResponseBuilderError("{0} top-level closure differs".format(label))
        for name in sorted(top_level):
            members[name] = response_module._open_member(
                root, name, label + " member " + name
            )
        if support_present:
            support = response_module._open_child_dir(
                root, "support", label + " support directory"
            )
            support_names = response_module._list_dir(
                support, response_module.MAX_SUPPORT_RECORDS
            )
            support["expected_names"] = support_names
            for name in support_names:
                if not response_module.HEX_SHA256.fullmatch(name):
                    raise ResponseBuilderError("support filename is malformed")
                relative = "support/" + name
                members[relative] = response_module._open_member(
                    support, name, label + " member " + relative
                )
        if len(members) > MAX_TREE_MEMBERS:
            raise ResponseBuilderError("{0} member count exceeds its cap".format(label))
        total = sum(member["size"] for member in members.values())
        if total > MAX_TEMPLATE_BYTES:
            raise ResponseBuilderError("{0} aggregate size exceeds its cap".format(label))
        files = {}
        retained = 0
        for name in sorted(members):
            member = members[name]
            if name.startswith("support/"):
                cap = response_module.MAX_SUPPORT_MEMBER_BYTES
            elif name in ("template-root.json", "response-root.json"):
                cap = response_module.MAX_ROOT_BYTES
            else:
                cap = response_module.MAX_STREAM_BYTES
            data = response_module._read_member(member, cap)
            retained += len(data)
            if retained > MAX_TEMPLATE_BYTES:
                raise ResponseBuilderError("{0} retained bytes exceed cap".format(label))
            files[name] = data
        if retained != total:
            raise ResponseBuilderError("{0} retained-byte closure differs".format(label))
        response_module._replay_dir(root)
        if support is not None:
            response_module._replay_dir(support)
        return files
    except ResponseBuilderError:
        raise
    except Exception as error:
        raise ResponseBuilderError("cannot read {0}: {1}".format(label, error))
    finally:
        for member in members.values():
            try:
                os.close(member["fd"])
            except OSError:
                pass
        response_module._close_dir(support)
        response_module._close_dir(root)


def _safe_output_name(value, label):
    raw = str(value)
    parts = raw.split(os.sep)
    comparable = parts[1:] if os.path.isabs(raw) else parts
    if (
        not raw
        or "\x00" in raw
        or "\\" in raw
        or any(part in ("", ".", "..") for part in comparable)
    ):
        raise ResponseBuilderError("{0} path is unsafe".format(label))
    path = Path(os.path.abspath(raw))
    if path.anchor != os.sep or len(path.parts) < 3:
        raise ResponseBuilderError("{0} path is too broad".format(label))
    return path


def _replay_output_parent(response_module, context, allow_child_mutation):
    """Replay a held output parent, allowing only its child-list metadata to move."""

    chain = context["chain"]
    for index, record in enumerate(chain):
        try:
            opened = os.fstat(record["descriptor"])
            named = (
                opened
                if record["parent_fd"] is None
                else os.stat(
                    record["name"],
                    dir_fd=record["parent_fd"],
                    follow_symlinks=False,
                )
            )
        except OSError as error:
            raise ResponseBuilderError(
                "output parent namespace changed: {0}".format(error)
            )
        opened_identity = response_module._directory_identity(opened)
        named_identity = response_module._directory_identity(named)
        if opened_identity != named_identity:
            raise ResponseBuilderError("output parent namespace identity changed")
        if index != len(chain) - 1 or not allow_child_mutation:
            if opened_identity != record["identity"]:
                raise ResponseBuilderError("output parent ancestor changed")
        else:
            original = record["identity"]
            stable_opened = (
                opened.st_dev,
                opened.st_ino,
                opened.st_mode,
                opened.st_uid,
                opened.st_gid,
            )
            stable_original = (
                original[0],
                original[1],
                original[2],
                original[4],
                original[5],
            )
            if stable_opened != stable_original:
                raise ResponseBuilderError("output parent stable identity changed")


def _rename_directory_noreplace(parent_fd, source_name, target_name):
    """Use Linux renameat2(RENAME_NOREPLACE); fail closed if unavailable."""

    try:
        library = ctypes.CDLL(None, use_errno=True)
        renameat2 = library.renameat2
    except (AttributeError, OSError) as error:
        raise ResponseBuilderError(
            "atomic no-replace directory publication is unavailable: {0}".format(error)
        )
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_fd,
        source_name.encode("ascii"),
        parent_fd,
        target_name.encode("ascii"),
        1,
    )
    if result != 0:
        number = ctypes.get_errno()
        if number == errno.EEXIST:
            raise ResponseBuilderError("output target appeared during publication")
        raise ResponseBuilderError(
            "atomic no-replace directory publication failed: {0}".format(
                os.strerror(number)
            )
        )


def _read_output_member(record, expected, label):
    opened = os.fstat(record["fd"])
    named = os.stat(
        record["name"], dir_fd=record["directory_fd"], follow_symlinks=False
    )
    identity = _stat_identity(opened)
    if (
        identity != record["identity"]
        or _stat_identity(named) != record["identity"]
        or not stat.S_ISREG(opened.st_mode)
        or stat.S_IMODE(opened.st_mode) != 0o444
        or opened.st_nlink != 1
        or opened.st_size != len(expected)
    ):
        raise ResponseBuilderError("{0} identity changed".format(label))
    os.lseek(record["fd"], 0, os.SEEK_SET)
    chunks = []
    remaining = len(expected)
    while remaining:
        chunk = os.read(record["fd"], min(1024 * 1024, remaining))
        if not chunk:
            raise ResponseBuilderError("{0} ended early".format(label))
        chunks.append(chunk)
        remaining -= len(chunk)
        current = os.fstat(record["fd"])
        if _stat_identity(current) != record["identity"]:
            raise ResponseBuilderError("{0} changed while replayed".format(label))
    if os.read(record["fd"], 1):
        raise ResponseBuilderError("{0} grew while replayed".format(label))
    retained = b"".join(chunks)
    if retained != expected:
        raise ResponseBuilderError("{0} bytes changed".format(label))
    final_opened = os.fstat(record["fd"])
    final_named = os.stat(
        record["name"], dir_fd=record["directory_fd"], follow_symlinks=False
    )
    if (
        _stat_identity(final_opened) != record["identity"]
        or _stat_identity(final_named) != record["identity"]
    ):
        raise ResponseBuilderError("{0} changed after replay".format(label))


def _verify_output_stage(
    response_module,
    parent_fd,
    namespace_name,
    root_fd,
    root_stable_identity,
    support_fd,
    support_identity,
    members,
    files,
):
    try:
        root_opened = os.fstat(root_fd)
        root_named = os.stat(
            namespace_name, dir_fd=parent_fd, follow_symlinks=False
        )
    except OSError as error:
        raise ResponseBuilderError("output stage namespace changed: {0}".format(error))
    root_stable_opened = (
        root_opened.st_dev,
        root_opened.st_ino,
        root_opened.st_mode,
        root_opened.st_uid,
        root_opened.st_gid,
    )
    root_stable_named = (
        root_named.st_dev,
        root_named.st_ino,
        root_named.st_mode,
        root_named.st_uid,
        root_named.st_gid,
    )
    if (
        root_stable_opened != root_stable_identity
        or root_stable_named != root_stable_identity
        or not stat.S_ISDIR(root_opened.st_mode)
        or stat.S_IMODE(root_opened.st_mode) != 0o555
    ):
        raise ResponseBuilderError("output stage root identity changed")
    expected_root_names = sorted(
        {name for name in files if not name.startswith("support/")}
        | ({"support"} if support_fd is not None else set())
    )
    if sorted(os.listdir(root_fd)) != expected_root_names:
        raise ResponseBuilderError("output stage top-level closure changed")
    if support_fd is not None:
        support_opened = os.fstat(support_fd)
        support_named = os.stat("support", dir_fd=root_fd, follow_symlinks=False)
        if (
            response_module._directory_identity(support_opened) != support_identity
            or response_module._directory_identity(support_named) != support_identity
            or stat.S_IMODE(support_opened.st_mode) != 0o555
        ):
            raise ResponseBuilderError("output support directory identity changed")
        expected_support_names = sorted(
            name.split("/", 1)[1]
            for name in files
            if name.startswith("support/")
        )
        if sorted(os.listdir(support_fd)) != expected_support_names:
            raise ResponseBuilderError("output support closure changed")
    for name in sorted(members):
        _read_output_member(
            members[name], files[name], "output stage member " + name
        )
    root_opened_after = os.fstat(root_fd)
    root_named_after = os.stat(
        namespace_name, dir_fd=parent_fd, follow_symlinks=False
    )
    for info in (root_opened_after, root_named_after):
        stable = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)
        if stable != root_stable_identity:
            raise ResponseBuilderError("output stage root moved during replay")


def atomic_publish_tree(response_module, output_directory, files):
    """Publish a new 0444/0555 tree atomically without following links."""

    output = _safe_output_name(output_directory, "output directory")
    parent_path = output.parent
    basename = output.name
    if basename in ("", ".", "..") or os.sep in basename:
        raise ResponseBuilderError("output directory name is unsafe")
    expected_top = {name for name in files if not name.startswith("support/")}
    if not expected_top or len(files) > MAX_TREE_MEMBERS:
        raise ResponseBuilderError("output member closure is empty or excessive")
    total = 0
    for name, data in files.items():
        safe_relative(name, "output member")
        if type(data) is not bytes:
            raise ResponseBuilderError("output member data is not bytes")
        if name.startswith("support/"):
            parts = name.split("/")
            if len(parts) != 2 or not response_module.HEX_SHA256.fullmatch(parts[1]):
                raise ResponseBuilderError("output support member name is malformed")
        elif "/" in name:
            raise ResponseBuilderError("output top-level member is nested")
        total += len(data)
        if total > MAX_TEMPLATE_BYTES:
            raise ResponseBuilderError("output aggregate size exceeds its cap")

    parent = response_module._open_dir(parent_path, "output parent")
    temp_name = None
    temp_path = None
    published = False
    temp_fd = None
    support_fd = None
    member_records = {}
    try:
        parent_info = os.fstat(parent["fd"])
        if (
            parent_info.st_uid != os.geteuid()
            or parent_info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise ResponseBuilderError("output parent is not private to the current user")
        try:
            os.stat(basename, dir_fd=parent["fd"], follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ResponseBuilderError("cannot inspect output target: {0}".format(error))
        else:
            raise ResponseBuilderError("output target already exists")

        _replay_output_parent(response_module, parent, False)
        for unused in range(128):
            candidate = ".rk001-builder-" + os.urandom(16).hex()
            try:
                os.mkdir(candidate, 0o700, dir_fd=parent["fd"])
            except FileExistsError:
                continue
            temp_name = candidate
            break
        if temp_name is None:
            raise ResponseBuilderError("cannot allocate an output staging directory")
        temp_path = parent_path / temp_name
        temp_fd = os.open(
            temp_name,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            dir_fd=parent["fd"],
        )
        if any(name.startswith("support/") for name in files):
            os.mkdir("support", 0o700, dir_fd=temp_fd)
            support_fd = os.open(
                "support",
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=temp_fd,
            )
        for name in sorted(files):
            if name.startswith("support/"):
                directory_fd = support_fd
                filename = name.split("/", 1)[1]
            else:
                directory_fd = temp_fd
                filename = name
            flags = (
                os.O_RDWR
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0)
            )
            descriptor = os.open(filename, flags, 0o400, dir_fd=directory_fd)
            member_records[name] = {
                "directory_fd": directory_fd,
                "fd": descriptor,
                "identity": None,
                "name": filename,
            }
            data = files[name]
            offset = 0
            while offset < len(data):
                written = os.write(descriptor, data[offset : offset + 1024 * 1024])
                if written <= 0:
                    raise ResponseBuilderError("output member write made no progress")
                offset += written
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o444)
            os.fsync(descriptor)
            info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o444
                or info.st_nlink != 1
                or info.st_size != len(data)
            ):
                raise ResponseBuilderError("published member identity differs")
            member_records[name]["identity"] = _stat_identity(info)
        support_identity = None
        if support_fd is not None:
            os.fchmod(support_fd, 0o555)
            os.fsync(support_fd)
            support_identity = response_module._directory_identity(
                os.fstat(support_fd)
            )
        os.fchmod(temp_fd, 0o555)
        os.fsync(temp_fd)
        root_info = os.fstat(temp_fd)
        root_stable_identity = (
            root_info.st_dev,
            root_info.st_ino,
            root_info.st_mode,
            root_info.st_uid,
            root_info.st_gid,
        )
        _verify_output_stage(
            response_module,
            parent["fd"],
            temp_name,
            temp_fd,
            root_stable_identity,
            support_fd,
            support_identity,
            member_records,
            files,
        )
        _replay_output_parent(response_module, parent, True)
        _rename_directory_noreplace(parent["fd"], temp_name, basename)
        try:
            _verify_output_stage(
                response_module,
                parent["fd"],
                basename,
                temp_fd,
                root_stable_identity,
                support_fd,
                support_identity,
                member_records,
                files,
            )
            os.fsync(parent["fd"])
            _replay_output_parent(response_module, parent, True)
        except Exception as verification_error:
            try:
                _rename_directory_noreplace(parent["fd"], basename, temp_name)
                os.fsync(parent["fd"])
            except Exception as rollback_error:
                raise ResponseBuilderError(
                    "published output verification failed ({0}); rollback failed ({1})".format(
                        verification_error, rollback_error
                    )
                )
            raise ResponseBuilderError(
                "published output verification failed and was retracted: {0}".format(
                    verification_error
                )
            )
        published = True
        temp_name = None
    except ResponseBuilderError:
        raise
    except OSError as error:
        raise ResponseBuilderError("cannot publish output tree: {0}".format(error))
    finally:
        for record in member_records.values():
            try:
                os.close(record["fd"])
            except OSError:
                pass
        if support_fd is not None:
            try:
                os.close(support_fd)
            except OSError:
                pass
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_name is not None and temp_path is not None:
            try:
                os.chmod(str(temp_path), 0o700, follow_symlinks=False)
                support_path = temp_path / "support"
                if support_path.exists() and not support_path.is_symlink():
                    os.chmod(str(support_path), 0o700, follow_symlinks=False)
                shutil.rmtree(str(temp_path))
            except OSError:
                pass
        response_module._close_dir(parent)
    if not published:
        raise ResponseBuilderError("output tree was not published")
    return output


def parser(argv=None):
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", default=REPO_ROOT, type=Path)
    value.add_argument("--authority", type=Path)
    modes = value.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--emit-template", action="store_true")
    modes.add_argument("--prepare-signing", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    value.add_argument("--artifact", type=Path)
    value.add_argument("--packet-id")
    value.add_argument("--packet-dir", type=Path)
    value.add_argument("--reviewer-authority-id")
    value.add_argument("--reviewer-identity")
    value.add_argument("--review-completed-at")
    value.add_argument("--draft-dir", type=Path)
    value.add_argument("--prepared-dir", type=Path)
    value.add_argument("--signature", type=Path)
    value.add_argument("--output-dir", type=Path)
    return value.parse_args(argv)


def _require_arguments(args, names):
    for name in names:
        if getattr(args, name) is None:
            raise ResponseBuilderError(
                "--{0} is required".format(name.replace("_", "-"))
            )


def main(argv=None):
    args = parser(argv)
    try:
        repo = args.repo.resolve()
        authority = load_authority(repo, args.authority)
        dependencies = load_dependencies(repo, authority)
        response_module = dependencies["response"]
        production_authority = dependencies["response_authority"]
        policy = production_authority["reviewer_authority_policy"]
        if args.check:
            require_exact(
                policy["registration_status"],
                "required-missing",
                "production reviewer registry status",
            )
            require_exact(
                policy["registered_reviewers"], [], "production reviewer registry"
            )
            print(
                "RK-001 response builder verified: reviewers=0 appointment=false "
                "key_custody=false signed=false durable=false aggregate=false "
                "gate=TODO points=0 credit=false"
            )
            return 0

        _require_arguments(
            args,
            (
                "artifact",
                "packet_id",
                "packet_dir",
                "reviewer_authority_id",
                "reviewer_identity",
                "review_completed_at",
                "output_dir",
            ),
        )
        registry = load_registry(
            response_module, production_authority, registry_loader=None
        )
        reviewer = active_appointment(
            response_module,
            registry,
            args.reviewer_authority_id,
            args.reviewer_identity,
            args.packet_id,
            args.review_completed_at,
        )
        groups, units = load_verified_packet(
            repo,
            dependencies,
            args.artifact,
            args.packet_id,
            args.packet_dir,
        )
        campaign_sha256 = authority["inputs"]["campaign_authority"]["sha256"]
        if args.emit_template:
            files = emit_template_data(
                authority,
                response_module,
                registry,
                groups,
                units,
                args.packet_id,
                reviewer,
                args.review_completed_at,
                campaign_sha256,
            )
            atomic_publish_tree(response_module, args.output_dir, files)
            print(
                "RK-001 null-decision response template emitted: packet={0} "
                "units={1} findings={2} signed=false credit=false".format(
                    args.packet_id, len(units), len(groups)
                )
            )
            return 0
        if args.prepare_signing:
            _require_arguments(args, ("draft_dir",))
            draft_files = read_exact_tree(
                response_module, args.draft_dir, TEMPLATE_TOP_LEVEL, "response draft"
            )
            files = prepare_signing_data(
                authority,
                response_module,
                registry,
                groups,
                units,
                args.packet_id,
                reviewer,
                args.review_completed_at,
                campaign_sha256,
                draft_files,
            )
            atomic_publish_tree(response_module, args.output_dir, files)
            print(
                "RK-001 response signing bytes prepared: packet={0} key_custody=false "
                "signed=false credit=false".format(args.packet_id)
            )
            return 0
        _require_arguments(args, ("prepared_dir", "signature"))
        prepared_files = read_exact_tree(
            response_module,
            args.prepared_dir,
            PREPARED_TOP_LEVEL,
            "prepared response",
        )
        signature_bytes = _read_regular_file_once(
            args.signature,
            "external response signature",
            response_module.MAX_SIGNATURE_BYTES,
        )
        files, result = finalize_data(
            response_module,
            registry,
            groups,
            units,
            args.packet_id,
            campaign_sha256,
            prepared_files,
            signature_bytes,
        )
        atomic_publish_tree(response_module, args.output_dir, files)
        print(
            "RK-001 externally signed response finalized: packet={0} root={1} "
            "signature=true key_custody=false durable=false aggregate=false "
            "gate=TODO points=0 credit=false".format(
                result["packet_id"], result["signed_response_root"]
            )
        )
        return 0
    except ResponseBuilderError as error:
        print("RK-001 response-builder error: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
