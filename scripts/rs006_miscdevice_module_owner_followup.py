#!/usr/bin/env python3
"""Validate the unintegrated RS-006 miscdevice module-owner follow-up.

This checker proves only the exact local candidate bytes, their strict replay
after patches 0019 and 0020 on the minimal repository fixture, and a standalone
compile-shape model.  It cannot integrate the patch, supersede an authority,
prove a Rocky kernel build or runtime result, or award gate/tracker credit.
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile


CONTRACT_PATH = "host-kernel/contracts/rs006-miscdevice-module-owner-followup-v1.json"
EXPECTED_CONTRACT_SHA256 = "5936b3bda67570babeac0f10d58d6eaa838921bc1a0884a07e544016ed0f0ca9"
CANDIDATE_PATH = "host-kernel/rocky/candidates/0020-followup-rust-miscdevice-module-owner-v1.patch"
COMPILE_FIXTURE_PATH = "scripts/tests/fixtures/rs006_miscdevice_module_owner_compile.rs"
REPLAY_FIXTURE_PATH = "scripts/tests/fixtures/rust-core-rocky-6.12"

_MAX_AUTHORITY_BYTES = 1024 * 1024
_PATCH_HEADER = re.compile(br"^diff --git a/([^\n]+) b/([^\n]+)$", re.MULTILINE)


class ContractError(Exception):
    """The candidate contract, inputs, or replay failed closed."""


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _identity(info):
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        stat.S_IMODE(info.st_mode),
        info.st_nlink,
        info.st_uid,
        info.st_gid,
        info.st_size,
        getattr(info, "st_mtime_ns", int(info.st_mtime * 1000000000)),
        getattr(info, "st_ctime_ns", int(info.st_ctime * 1000000000)),
    )


def _json_without_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("duplicate JSON key: {0}".format(key))
        value[key] = item
    return value


def _safe_relative(value, label):
    if type(value) is not str or not value or "\\" in value:
        raise ContractError("{0} is not a normalized relative path".format(label))
    if any(ord(character) < 0x20 or ord(character) == 0x7f for character in value):
        raise ContractError("{0} contains a control character".format(label))
    parts = value.split("/")
    if value.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise ContractError("{0} escapes its root".format(label))
    return value


def _read_regular(repo_root, relative, label, cap=_MAX_AUTHORITY_BYTES):
    """Read through the same post-close-hardened aggregate snapshot path."""
    if type(cap) is not int or isinstance(cap, bool) or cap < 0:
        raise ContractError("{0} byte cap is invalid".format(label))
    snapshot = None
    failure = None
    data = None
    try:
        snapshot = _AggregateSnapshot(repo_root)
        data = snapshot.open_file(relative, label, cap)
        snapshot.checkpoint(label + " validation")
    except (ContractError, OSError, TypeError, ValueError) as error:
        failure = error if isinstance(error, ContractError) else ContractError(
            "{0} snapshot failed closed: {1}".format(label, error))
    if snapshot is not None:
        try:
            snapshot.close()
        except ContractError as error:
            if failure is None:
                failure = error
    if failure is not None:
        raise failure
    if data is None:
        raise ContractError("{0} snapshot produced no bytes".format(label))
    return data


def _read_fd_exact(descriptor, expected_size, label):
    os.lseek(descriptor, 0, os.SEEK_SET)
    data = bytearray()
    while len(data) < expected_size:
        chunk = os.read(descriptor, min(65536, expected_size - len(data)))
        if not chunk:
            raise ContractError("{0} retained bytes ended early".format(label))
        data.extend(chunk)
    if os.read(descriptor, 1):
        raise ContractError("{0} retained bytes exceed the identity size".format(label))
    return bytes(data)


class _AggregateSnapshot(object):
    """One retained descriptor-rooted snapshot for every authoritative input."""

    def __init__(self, repo_root):
        if type(repo_root) is not str or not repo_root:
            raise ContractError("repository root must be nonempty text")
        root = os.path.abspath(repo_root)
        if os.path.realpath(root) != root:
            raise ContractError("repository root must not traverse a symlink")
        self.repo_root = root
        self._directories = []
        self._directory_by_path = {}
        self._files = {}
        self._tree_specs = []
        self._closed = False
        self._directory_flags = (
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) |
            getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0)
        )
        self._leaf_flags = (
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) |
            getattr(os, "O_NOFOLLOW", 0)
        )
        if not getattr(os, "O_NOFOLLOW", 0) or not getattr(os, "O_DIRECTORY", 0):
            raise ContractError("descriptor-rooted O_NOFOLLOW/openat support is required")
        try:
            self._open_repository_chain()
        except (ContractError, OSError) as error:
            while self._directories:
                record = self._directories.pop()
                try:
                    os.close(record["descriptor"])
                except OSError:
                    pass
            if isinstance(error, ContractError):
                raise error
            raise ContractError("cannot retain repository root: {0}".format(error))

    def _open_repository_chain(self):
        named = os.lstat(os.sep)
        if not stat.S_ISDIR(named.st_mode) or stat.S_ISLNK(named.st_mode):
            raise ContractError("filesystem root is not a real directory")
        descriptor = os.open(os.sep, self._directory_flags)
        retained = os.fstat(descriptor)
        if _identity(named) != _identity(retained):
            os.close(descriptor)
            raise ContractError("filesystem-root named/descriptor identity differs")
        record = {
            "absolute": os.sep,
            "descriptor": descriptor,
            "identity": _identity(retained),
            "name": os.sep,
            "parent": None,
        }
        self._directories.append(record)
        self._directory_by_path[os.sep] = record
        current = record
        current_path = os.sep
        components = [part for part in self.repo_root.split(os.sep) if part]
        for component in components:
            current_path = os.path.join(current_path, component)
            current = self._open_child_directory(current, component, current_path)
        self._repository_record = current

    def _open_child_directory(self, parent, name, absolute):
        if absolute in self._directory_by_path:
            return self._directory_by_path[absolute]
        named = os.stat(name, dir_fd=parent["descriptor"], follow_symlinks=False)
        if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
            raise ContractError("snapshot ancestor is not a real directory: {0}".format(absolute))
        descriptor = os.open(
            name, self._directory_flags, dir_fd=parent["descriptor"])
        retained = os.fstat(descriptor)
        if _identity(named) != _identity(retained):
            os.close(descriptor)
            raise ContractError("snapshot ancestor named/descriptor identity differs: {0}".format(absolute))
        record = {
            "absolute": absolute,
            "descriptor": descriptor,
            "identity": _identity(retained),
            "name": name,
            "parent": parent,
        }
        self._directories.append(record)
        self._directory_by_path[absolute] = record
        return record

    def _ensure_directory(self, relative_parts):
        current = self._repository_record
        absolute = self.repo_root
        for component in relative_parts:
            absolute = os.path.join(absolute, component)
            current = self._open_child_directory(current, component, absolute)
        return current

    def open_file(self, relative, label, cap):
        if self._closed:
            raise ContractError("aggregate snapshot is already closed")
        if type(cap) is not int or isinstance(cap, bool) or cap < 0:
            raise ContractError("{0} byte cap is invalid".format(label))
        relative = _safe_relative(relative, label)
        if relative in self._files:
            record = self._files[relative]
            if len(record["bytes"]) > cap:
                raise ContractError("{0} exceeds its byte cap".format(label))
            return record["bytes"]
        parts = relative.split("/")
        parent = self._ensure_directory(parts[:-1])
        name = parts[-1]
        named = os.stat(name, dir_fd=parent["descriptor"], follow_symlinks=False)
        if stat.S_ISLNK(named.st_mode) or not stat.S_ISREG(named.st_mode):
            raise ContractError("{0} must be a regular non-symlink file".format(label))
        if named.st_nlink != 1:
            raise ContractError("{0} must be singly linked".format(label))
        if named.st_size > cap:
            raise ContractError("{0} exceeds its byte cap".format(label))
        descriptor = os.open(name, self._leaf_flags, dir_fd=parent["descriptor"])
        retained = os.fstat(descriptor)
        identity = _identity(retained)
        if _identity(named) != identity:
            os.close(descriptor)
            raise ContractError("{0} named/descriptor identity differs".format(label))
        first = _read_fd_exact(descriptor, retained.st_size, label)
        second = _read_fd_exact(descriptor, retained.st_size, label)
        if first != second or _identity(os.fstat(descriptor)) != identity:
            os.close(descriptor)
            raise ContractError("{0} changed during retained byte replay".format(label))
        named_after = os.stat(name, dir_fd=parent["descriptor"], follow_symlinks=False)
        if _identity(named_after) != identity:
            os.close(descriptor)
            raise ContractError("{0} named identity changed during capture".format(label))
        record = {
            "absolute": os.path.join(self.repo_root, *parts),
            "bytes": first,
            "descriptor": descriptor,
            "identity": identity,
            "label": label,
            "name": name,
            "parent": parent,
            "relative": relative,
        }
        self._files[relative] = record
        return first

    def assert_tree(self, prefix, inventory_paths, label):
        prefix = _safe_relative(prefix, label + " prefix")
        if type(inventory_paths) is not list or not inventory_paths:
            raise ContractError("{0} inventory paths differ".format(label))
        directory_names = {"": set()}
        directory_paths = {""}
        file_paths = set()
        for index, value in enumerate(inventory_paths):
            relative = _safe_relative(value, "{0}[{1}]".format(label, index))
            if relative in file_paths:
                raise ContractError("{0} contains duplicate files".format(label))
            file_paths.add(relative)
            parts = relative.split("/")
            for offset, component in enumerate(parts):
                parent = "/".join(parts[:offset])
                directory_names.setdefault(parent, set()).add(component)
                if offset < len(parts) - 1:
                    child = "/".join(parts[:offset + 1])
                    directory_paths.add(child)
                    directory_names.setdefault(child, set())
        prefix_parts = prefix.split("/")
        for directory_relative in sorted(directory_paths):
            suffix = [] if not directory_relative else directory_relative.split("/")
            record = self._ensure_directory(prefix_parts + suffix)
            actual = sorted(os.listdir(record["descriptor"]))
            expected = sorted(directory_names[directory_relative])
            if actual != expected:
                raise ContractError("{0} member set differs at {1}".format(label, directory_relative))
            for name in expected:
                metadata = os.stat(
                    name, dir_fd=record["descriptor"], follow_symlinks=False)
                child = name if not directory_relative else directory_relative + "/" + name
                if child in directory_paths:
                    valid = stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode)
                else:
                    valid = stat.S_ISREG(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode)
                if not valid:
                    raise ContractError("{0} member type differs: {1}".format(label, child))
        spec = {
            "directory_names": {
                key: tuple(sorted(value)) for key, value in directory_names.items()
            },
            "directory_paths": tuple(sorted(directory_paths)),
            "label": label,
            "prefix": prefix,
        }
        self._tree_specs.append(spec)
        self._replay_tree_retained(spec, label + " initial")

    def _replay_tree_retained(self, spec, label):
        prefix_parts = spec["prefix"].split("/")
        for directory_relative in spec["directory_paths"]:
            suffix = [] if not directory_relative else directory_relative.split("/")
            absolute = os.path.join(self.repo_root, *(prefix_parts + suffix))
            record = self._directory_by_path.get(absolute)
            if record is None or record["descriptor"] is None:
                raise ContractError("{0} retained tree directory is closed".format(label))
            try:
                actual = tuple(sorted(os.listdir(record["descriptor"])))
            except OSError as error:
                raise ContractError("{0} retained tree replay failed: {1}".format(label, error))
            if actual != spec["directory_names"][directory_relative]:
                raise ContractError("{0} retained member set differs".format(label))

    def _replay_retained(self, label):
        for record in self._directories:
            descriptor = record["descriptor"]
            if descriptor is None:
                continue
            if _identity(os.fstat(descriptor)) != record["identity"]:
                raise ContractError("{0} retained directory identity differs".format(label))
            parent = record["parent"]
            if parent is None:
                named = os.lstat(record["absolute"])
            elif parent["descriptor"] is not None:
                named = os.stat(
                    record["name"], dir_fd=parent["descriptor"], follow_symlinks=False)
            else:
                continue
            if _identity(named) != record["identity"]:
                raise ContractError("{0} retained named directory differs".format(label))
        for relative in sorted(self._files):
            record = self._files[relative]
            descriptor = record["descriptor"]
            if descriptor is None:
                continue
            if _identity(os.fstat(descriptor)) != record["identity"]:
                raise ContractError("{0} retained file identity differs: {1}".format(label, relative))
            replay = _read_fd_exact(
                descriptor, record["identity"][7], label + " " + relative)
            if replay != record["bytes"]:
                raise ContractError("{0} retained file bytes differ: {1}".format(label, relative))
            parent = record["parent"]
            if parent["descriptor"] is not None:
                named = os.stat(
                    record["name"], dir_fd=parent["descriptor"], follow_symlinks=False)
                if _identity(named) != record["identity"]:
                    raise ContractError("{0} retained named file differs: {1}".format(label, relative))
        for spec in self._tree_specs:
            self._replay_tree_retained(spec, label + " tree")

    def _fresh_open_chain(self, absolute_parent, label):
        descriptors = []
        try:
            descriptor = os.open(os.sep, self._directory_flags)
            descriptors.append(descriptor)
            root_record = self._directory_by_path[os.sep]
            if _identity(os.fstat(descriptor)) != root_record["identity"]:
                raise ContractError("{0} fresh filesystem root differs".format(label))
            current_path = os.sep
            for component in [part for part in absolute_parent.split(os.sep) if part]:
                current_path = os.path.join(current_path, component)
                named = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
                    raise ContractError("{0} fresh ancestor type differs".format(label))
                child = os.open(component, self._directory_flags, dir_fd=descriptor)
                descriptors.append(child)
                expected = self._directory_by_path.get(current_path)
                if expected is None or _identity(named) != expected["identity"] \
                        or _identity(os.fstat(child)) != expected["identity"]:
                    raise ContractError("{0} fresh ancestor identity differs".format(label))
                descriptor = child
            return descriptors
        except (ContractError, OSError) as error:
            while descriptors:
                try:
                    os.close(descriptors.pop())
                except OSError:
                    pass
            if isinstance(error, ContractError):
                raise error
            raise ContractError("{0} fresh ancestor replay failed: {1}".format(label, error))

    def _fresh_read_file(self, record, label):
        descriptors = self._fresh_open_chain(os.path.dirname(record["absolute"]), label)
        leaf = None
        failure = None
        try:
            parent = descriptors[-1]
            named = os.stat(record["name"], dir_fd=parent, follow_symlinks=False)
            if _identity(named) != record["identity"]:
                raise ContractError("{0} fresh named leaf identity differs".format(label))
            leaf = os.open(record["name"], self._leaf_flags, dir_fd=parent)
            if _identity(os.fstat(leaf)) != record["identity"]:
                raise ContractError("{0} fresh retained leaf identity differs".format(label))
            data = _read_fd_exact(leaf, record["identity"][7], label)
            if data != record["bytes"]:
                raise ContractError("{0} fresh named leaf bytes differ".format(label))
        except ContractError as error:
            failure = error
        except OSError as error:
            failure = ContractError("{0} fresh replay failed: {1}".format(label, error))
        if leaf is not None:
            try:
                os.close(leaf)
            except OSError as error:
                if failure is None:
                    failure = ContractError("{0} fresh leaf close failed: {1}".format(label, error))
        while descriptors:
            try:
                os.close(descriptors.pop())
            except OSError as error:
                if failure is None:
                    failure = ContractError("{0} fresh ancestor close failed: {1}".format(label, error))
        try:
            after = os.lstat(record["absolute"])
            if _identity(after) != record["identity"]:
                raise ContractError("{0} post-close named leaf identity differs".format(label))
        except (OSError, ContractError) as error:
            if failure is None:
                failure = error if isinstance(error, ContractError) else ContractError(
                    "{0} post-close replay failed: {1}".format(label, error))
        if failure is not None:
            raise failure

    def _fresh_tree_replay(self, spec, label):
        for directory_relative in spec["directory_paths"]:
            suffix = [] if not directory_relative else directory_relative.split("/")
            absolute = os.path.join(self.repo_root, spec["prefix"], *suffix)
            descriptors = self._fresh_open_chain(absolute, label)
            failure = None
            try:
                actual = tuple(sorted(os.listdir(descriptors[-1])))
                if actual != spec["directory_names"][directory_relative]:
                    failure = ContractError("{0} fresh tree member set differs".format(label))
            except OSError as error:
                failure = ContractError("{0} fresh tree replay failed: {1}".format(label, error))
            finally:
                while descriptors:
                    try:
                        os.close(descriptors.pop())
                    except OSError as error:
                        if failure is None:
                            failure = ContractError(
                                "{0} fresh tree close failed: {1}".format(label, error))
            if failure is not None:
                raise failure

    def _replay_all_named(self, label):
        for relative in sorted(self._files):
            self._fresh_read_file(self._files[relative], label + " " + relative)
        for spec in self._tree_specs:
            self._fresh_tree_replay(spec, label + " tree")

    def _replay_closed_state_once(self, label):
        """Replay names without opening descriptors that would add close races."""
        for record in self._directories:
            metadata = os.lstat(record["absolute"])
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode) \
                    or _identity(metadata) != record["identity"]:
                raise ContractError(
                    "{0} closed named directory differs: {1}".format(
                        label, record["absolute"]))
        for relative in sorted(self._files):
            record = self._files[relative]
            metadata = os.lstat(record["absolute"])
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode) \
                    or _identity(metadata) != record["identity"]:
                raise ContractError(
                    "{0} closed named file differs: {1}".format(label, relative))
        for spec in self._tree_specs:
            for directory_relative in spec["directory_paths"]:
                suffix = [] if not directory_relative else directory_relative.split("/")
                absolute = os.path.join(self.repo_root, spec["prefix"], *suffix)
                actual = tuple(sorted(os.listdir(absolute)))
                if actual != spec["directory_names"][directory_relative]:
                    raise ContractError(
                        "{0} closed tree member set differs".format(label))

    def _replay_closed_state(self, label):
        try:
            self._replay_closed_state_once(label)
            self._replay_closed_state_once(label + " final")
        except ContractError:
            raise
        except OSError as error:
            raise ContractError("{0} closed named replay failed: {1}".format(label, error))

    def checkpoint(self, label):
        self._replay_retained(label)
        self._replay_all_named(label + " named")
        self._replay_retained(label + " post-fresh-close")
        self._replay_closed_state(label + " post-fresh-close named")

    def bytes_by_path(self):
        return {relative: record["bytes"] for relative, record in self._files.items()}

    def descriptor_for(self, relative):
        return self._files[relative]["descriptor"]

    def close(self):
        if self._closed:
            return
        first_error = None
        try:
            self.checkpoint("aggregate pre-close")
        except (ContractError, OSError) as error:
            first_error = error if isinstance(error, ContractError) else ContractError(
                "aggregate pre-close replay failed: {0}".format(error))
        for relative in sorted(self._files):
            record = self._files[relative]
            descriptor = record["descriptor"]
            if descriptor is None:
                continue
            try:
                os.close(descriptor)
            except OSError as error:
                if first_error is None:
                    first_error = ContractError(
                        "aggregate leaf close failed for {0}: {1}".format(relative, error))
            record["descriptor"] = None
            try:
                self._replay_closed_state("post-leaf-close " + relative)
            except (ContractError, OSError) as error:
                if first_error is None:
                    first_error = error if isinstance(error, ContractError) else ContractError(
                        "aggregate post-leaf replay failed: {0}".format(error))
        for record in reversed(self._directories):
            descriptor = record["descriptor"]
            if descriptor is None:
                continue
            try:
                os.close(descriptor)
            except OSError as error:
                if first_error is None:
                    first_error = ContractError(
                        "aggregate directory close failed for {0}: {1}".format(
                            record["absolute"], error))
            record["descriptor"] = None
            try:
                self._replay_closed_state("post-directory-close " + record["absolute"])
            except (ContractError, OSError) as error:
                if first_error is None:
                    first_error = error if isinstance(error, ContractError) else ContractError(
                        "aggregate post-directory replay failed: {0}".format(error))
        self._closed = True
        try:
            self._replay_closed_state("aggregate final post-close")
        except (ContractError, OSError) as error:
            if first_error is None:
                first_error = error if isinstance(error, ContractError) else ContractError(
                    "aggregate final replay failed: {0}".format(error))
        if first_error is not None:
            raise first_error


def _strict_equal(actual, expected, label):
    if type(actual) is not type(expected):
        raise ContractError("{0} JSON type differs".format(label))
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ContractError("{0} keys differ".format(label))
        for key in sorted(expected):
            _strict_equal(actual[key], expected[key], "{0}.{1}".format(label, key))
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ContractError("{0} length differs".format(label))
        for index, expected_item in enumerate(expected):
            _strict_equal(actual[index], expected_item, "{0}[{1}]".format(label, index))
    elif actual != expected:
        raise ContractError("{0} differs".format(label))


def _expected_claims():
    return {
        "candidate_integrated": False,
        "compat_runtime_executed": False,
        "configured_kernel_compiled": False,
        "credit_eligible": False,
        "durable_evidence_archived": False,
        "exact_probe_updated": False,
        "gate_pass": False,
        "independent_review_complete": False,
        "license_authority_updated": False,
        "main_patch_series_updated": False,
        "module_runtime_executed": False,
        "rk006_authority_updated": False,
        "rs006_authority_superseded": False,
        "source_lock_updated": False,
        "stage_manifest_updated": False,
        "tracker_credit": False,
        "workflow_applies_candidate": False,
    }


def _expected_blockers():
    return [
        "Integrate the candidate immediately after patch 0020 in every ordered Rocky patch consumer.",
        "Refresh source-lock, license-inventory, RK-006, and RS-006 authorities against the integrated bytes.",
        "Refresh exact API-probe, configuration-resolution, review, and workflow bindings against the new postimage.",
        "Apply the complete ordered patch series to the exact locked Rocky archive and build the configured kernel and modules with CONFIG_COMPAT enabled.",
        "Obtain independent source, license, module-owner, compat-ABI, and pinned-lifetime review of the integrated result.",
        "Exercise module pinning, open-file deregistration ordering, native ioctl, and 32-bit compat ioctl behavior at runtime.",
        "Archive durable build and runtime evidence and obtain explicit RS-006 gate and tracker adjudication.",
    ]


def _load_contract(data):
    expected_digest = "5936b3bda67570babeac0f10d58d6eaa838921bc1a0884a07e544016ed0f0ca9"
    if type(data) is not bytes:
        raise ContractError("contract input must be bytes")
    if _sha256(data) != expected_digest:
        raise ContractError("follow-up contract digest changed")
    try:
        contract = json.loads(data.decode("utf-8"), object_pairs_hook=_json_without_duplicates)
    except (UnicodeError, ValueError) as error:
        raise ContractError("cannot parse follow-up contract: {0}".format(error))
    canonical = (json.dumps(contract, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if data != canonical:
        raise ContractError("follow-up contract is not canonical JSON")
    _validate_contract_object(contract)
    return contract


def _validate_identity_inventory(rows, label, expected_count=None):
    if type(rows) is not list or not rows:
        raise ContractError("{0} must be a nonempty list".format(label))
    paths = []
    by_path = {}
    for index, row in enumerate(rows):
        row_label = "{0}[{1}]".format(label, index)
        if type(row) is not dict or set(row) != {"path", "sha256", "size"}:
            raise ContractError("{0} identity row differs".format(row_label))
        path = _safe_relative(row["path"], row_label + ".path")
        digest = row["sha256"]
        size = row["size"]
        if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ContractError("{0} digest differs".format(row_label))
        if type(size) is not int or isinstance(size, bool) or size <= 0:
            raise ContractError("{0} size differs".format(row_label))
        if path in by_path:
            raise ContractError("{0} contains a duplicate path".format(label))
        paths.append(path)
        by_path[path] = row
    if paths != sorted(paths):
        raise ContractError("{0} paths are not canonical".format(label))
    if expected_count is not None and len(paths) != expected_count:
        raise ContractError("{0} count differs".format(label))
    return by_path


def _validate_contract_object(contract):
    expected_top = {
        "blockers", "candidate", "claims", "consumer_update_plan", "contract_id",
        "deferred_consumer_inventory", "fixture", "intended_semantics",
        "predecessor", "result_authority", "schema_version", "scope", "target",
    }
    if type(contract) is not dict or set(contract) != expected_top:
        raise ContractError("follow-up contract top-level keys differ")
    _strict_equal(contract["schema_version"], 1, "schema_version")
    _strict_equal(
        contract["contract_id"],
        "rs-006-miscdevice-module-owner-followup-v1",
        "contract_id",
    )
    _strict_equal(contract["claims"], _expected_claims(), "claims")
    _strict_equal(contract["blockers"], _expected_blockers(), "blockers")
    _strict_equal(
        contract["target"],
        {
            "architecture": "x86_64",
            "gate_id": "RS-006",
            "kernel_line": "Rocky Linux 6.12",
            "ordered_position": "immediately after 0020 and before 0021",
        },
        "target",
    )
    _strict_equal(
        contract["scope"],
        {
            "allowed": "generic Linux Rust miscdevice file-operations ownership, explicit compat dispatch, and registration/vtable lifetime shape",
            "excluded": "IHK policy, project-driver integration, source authority, build/runtime evidence, gate completion, and tracker credit",
        },
        "scope",
    )
    expected_candidate = {
        "license_expression": "GPL-2.0",
        "origin": "repository-local-unintegrated-candidate",
        "path": CANDIDATE_PATH,
        "provenance_reviewed": False,
        "sha256": "7990b1d8feac4b32c4fff87a8cc7c6e3fe2a273dc09c17d3f61eefb847f988a5",
        "size": 3250,
        "touched_paths": ["rust/kernel/miscdevice.rs"],
    }
    _strict_equal(contract["candidate"], expected_candidate, "candidate")
    _strict_equal(
        contract["fixture"],
        {
            "claim_scope": "userspace compile-shape only; not a kernel build or runtime result",
            "path": COMPILE_FIXTURE_PATH,
            "sha256": "909cabadb7862019bc8826dd70ab4bec84e87175b3a42a1570741f8c9fee79c8",
            "size": 4258,
        },
        "fixture",
    )
    _strict_equal(
        contract["intended_semantics"],
        {
            "compat": {
                "explicit_vtable_expression": "compat_ioctl: maybe_fn(T::HAS_COMPAT_IOCTL, fops_compat_ioctl::<T>),",
                "implicit_fallback_forbidden": "bindings::compat_ptr_ioctl",
            },
            "lifetime": {
                "deregister_before_pinned_storage_release": True,
                "per_registration_file_operations": False,
                "registration_storage": "PinInit-backed pinned Opaque<bindings::miscdevice>",
                "vtable_storage": "static per MiscDevice implementation type",
            },
            "module_owner": {
                "trait_item": "const MODULE: &'static ThisModule;",
                "vtable_expression": "owner: T::MODULE.as_ptr(),",
            },
        },
        "intended_semantics",
    )
    predecessor = contract["predecessor"]
    if type(predecessor) is not dict or set(predecessor) != {
            "local_replay_fixture", "miscdevice_postimage", "ordered_patches",
            "post_0020_dependency_inventory"}:
        raise ContractError("predecessor keys differ")
    local_fixture = predecessor["local_replay_fixture"]
    if type(local_fixture) is not dict or set(local_fixture) != {
            "authority", "inventory", "path", "scope"}:
        raise ContractError("local replay fixture keys differ")
    _strict_equal(
        {
            "authority": local_fixture["authority"],
            "path": local_fixture["path"],
            "scope": local_fixture["scope"],
        },
        {
            "authority": False,
            "path": REPLAY_FIXTURE_PATH,
            "scope": "minimal patch-context replay only; not the locked Rocky source archive",
        },
        "predecessor.local_replay_fixture",
    )
    fixture_inventory = _validate_identity_inventory(
        local_fixture["inventory"], "predecessor.local_replay_fixture.inventory", 37)
    required_fixture_records = {
        "rust/bindings/bindings_helper.h": {
            "path": "rust/bindings/bindings_helper.h",
            "sha256": "e7590a0468bb99dbf3f32dc5a3d40d2f5f35b4ac50803e9f755825a856ad518c",
            "size": 1201,
        },
        "rust/kernel/lib.rs": {
            "path": "rust/kernel/lib.rs",
            "sha256": "730fce907dbd8c48439f63f506d9400ceb707282846f1e325822c77dc99a56f0",
            "size": 4089,
        },
        "rust/kernel/types.rs": {
            "path": "rust/kernel/types.rs",
            "sha256": "3fe4d0cc0910560abefbd668afdb7aad90629b90079ad5e09a6b4346203f9413",
            "size": 19590,
        },
        "rust/macros/module.rs": {
            "path": "rust/macros/module.rs",
            "sha256": "5fbe26a038e97bdd04e629195e405987f61132d688f4fe808742d02a6bce223f",
            "size": 13807,
        },
    }
    for path, expected in required_fixture_records.items():
        if path not in fixture_inventory:
            raise ContractError("required replay dependency is absent: {0}".format(path))
        _strict_equal(fixture_inventory[path], expected, "replay dependency " + path)
    _strict_equal(
        predecessor["miscdevice_postimage"],
        {
            "path": "rust/kernel/miscdevice.rs",
            "sha256": "6cfa6ed228561b7a8d41df50700868480d29514dd3469935679b11015c93fc9c",
            "size": 7627,
        },
        "predecessor.miscdevice_postimage",
    )
    _strict_equal(
        predecessor["ordered_patches"],
        [
            {
                "path": "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
                "sha256": "bc9b84c4c8bf36b7fac02dd3d04e1a170b86ee143b76739a6eed3e564cdebc2b",
                "size": 1935,
            },
            {
                "path": "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch",
                "sha256": "d377b5bd91d507e383b8673beac42381b9b6c37a47bba7955c768a8f6ddaad25",
                "size": 10726,
            },
        ],
        "predecessor.ordered_patches",
    )
    expected_post_dependencies = [
        {
            "path": "rust/bindings/bindings_helper.h",
            "sha256": "f2644392ca91a791e4ab2ffb05a9b30a911a51f1ae025c696c710cfb3a447d07",
            "size": 1231,
        },
        {
            "path": "rust/kernel/lib.rs",
            "sha256": "c8eca83f523e46a211b6bc1ad48704899b372d46a28ceef9026aa21d873bf7a5",
            "size": 4109,
        },
        {
            "path": "rust/kernel/miscdevice.rs",
            "sha256": "6cfa6ed228561b7a8d41df50700868480d29514dd3469935679b11015c93fc9c",
            "size": 7627,
        },
        {
            "path": "rust/kernel/types.rs",
            "sha256": "3fde339b8a41b521407faa9e45d51ce9ecb183a170e9c650a72d25c73d50f6f7",
            "size": 20478,
        },
        {
            "path": "rust/macros/module.rs",
            "sha256": "5fbe26a038e97bdd04e629195e405987f61132d688f4fe808742d02a6bce223f",
            "size": 13807,
        },
    ]
    _strict_equal(
        predecessor["post_0020_dependency_inventory"],
        expected_post_dependencies,
        "predecessor.post_0020_dependency_inventory",
    )
    _strict_equal(
        contract["result_authority"],
        {
            "candidate_postimage": {
                "path": "rust/kernel/miscdevice.rs",
                "sha256": "0f2c43a6a64688b6b8387de4813a76289a66f67a1787893d747273c36983b8ee",
                "size": 7705,
            },
            "integration_status": "required-missing",
            "review_status": "required-missing",
            "runtime_status": "required-missing",
        },
        "result_authority",
    )
    plan = contract["consumer_update_plan"]
    if type(plan) is not dict or set(plan) != {
            "configuration_and_review", "exact_probe", "ordered_build",
            "patch_authority", "predecessor_contract", "source_and_license",
            "stage_manifest"}:
        raise ContractError("consumer update plan keys differ")
    planned_paths = []
    for group, rows in plan.items():
        if group == "stage_manifest":
            _strict_equal(
                rows,
                {
                    "path": "host-kernel/kbuild/stage-manifest.json",
                    "reason_not_modified": "The candidate changes a generic kernel patch only; it does not add or change a staged project source input. Reassess only when an integrated consumer changes.",
                },
                "consumer_update_plan.stage_manifest",
            )
            planned_paths.append(rows["path"])
            continue
        if type(rows) is not list or not rows:
            raise ContractError("consumer update plan {0} is not a sorted nonempty list".format(group))
        for index, relative in enumerate(rows):
            _safe_relative(relative, "consumer update plan {0}[{1}]".format(group, index))
            planned_paths.append(relative)
        if rows != sorted(rows):
            raise ContractError("consumer update plan {0} is not a sorted nonempty list".format(group))
    if len(planned_paths) != len(set(planned_paths)):
        raise ContractError("consumer update plan contains duplicate paths")
    consumer_inventory = _validate_identity_inventory(
        contract["deferred_consumer_inventory"], "deferred_consumer_inventory", 30)
    if sorted(planned_paths) != sorted(consumer_inventory):
        raise ContractError("deferred consumer inventory does not match the exact plan")


def _record(data):
    return {"sha256": _sha256(data), "size": len(data)}


def _validate_record(data, expected, label):
    if type(data) is not bytes:
        raise ContractError("{0} input must be bytes".format(label))
    if type(expected) is not dict or not {"sha256", "size"}.issubset(set(expected)):
        raise ContractError("{0} identity record is incomplete".format(label))
    if type(expected["sha256"]) is not str or type(expected["size"]) is not int:
        raise ContractError("{0} identity types differ".format(label))
    if len(data) != expected["size"] or _sha256(data) != expected["sha256"]:
        raise ContractError("{0} identity changed".format(label))


def _validate_candidate_patch(data, expected):
    _validate_record(data, expected, "candidate patch")
    if not data.startswith(b"From: local compatibility candidate\n"):
        raise ContractError("candidate status header differs")
    required_header = (
        b"Status: candidate only; not integrated into any source authority or workflow\n"
    )
    if data.count(required_header) != 1:
        raise ContractError("candidate-only status is not exact")
    headers = _PATCH_HEADER.findall(data)
    if headers != [(b"rust/kernel/miscdevice.rs", b"rust/kernel/miscdevice.rs")]:
        raise ContractError("candidate patch path vector differs")
    lowered = data.lower()
    for forbidden in (b"ihk", b"mckernel", b"mcctrl", b"mcexec"):
        if forbidden in lowered:
            raise ContractError("candidate patch crosses the generic-only boundary")
    required_additions = (
        b"+    ThisModule,\n",
        b"+    const MODULE: &'static ThisModule;\n",
        b"+            owner: T::MODULE.as_ptr(),\n",
        b"+            compat_ioctl: maybe_fn(T::HAS_COMPAT_IOCTL, fops_compat_ioctl::<T>),\n",
    )
    for addition in required_additions:
        if data.count(addition) != 1:
            raise ContractError("candidate semantic addition differs")
    if data.count(b"-                Some(bindings::compat_ptr_ioctl)\n") != 1:
        raise ContractError("candidate does not remove the implicit compat fallback exactly")


def _decode_text(data, label):
    try:
        return data.decode("utf-8")
    except UnicodeError as error:
        raise ContractError("{0} is not UTF-8: {1}".format(label, error))


def _load_json_bytes(data, label):
    try:
        value = json.loads(_decode_text(data, label), object_pairs_hook=_json_without_duplicates)
    except ValueError as error:
        raise ContractError("cannot parse {0}: {1}".format(label, error))
    if type(value) is not dict:
        raise ContractError("{0} must be a JSON object".format(label))
    return value


def _validate_replay_dependency_semantics(preimage_bytes, postimage_bytes):
    required_preimages = {
        "rust/bindings/bindings_helper.h", "rust/kernel/lib.rs",
        "rust/kernel/types.rs", "rust/macros/module.rs",
    }
    if not required_preimages.issubset(set(preimage_bytes)):
        raise ContractError("replay dependency preimages are incomplete")
    lib_text = _decode_text(preimage_bytes["rust/kernel/lib.rs"], "fixture kernel lib")
    as_ptr = (
        "    pub const fn as_ptr(&self) -> *mut bindings::module {\n"
        "        self.0\n"
        "    }"
    )
    if lib_text.count("pub struct ThisModule(*mut bindings::module);") != 1:
        raise ContractError("ThisModule pointer storage differs")
    if lib_text.count(as_ptr) != 1:
        raise ContractError("ThisModule::as_ptr does not expose its retained module pointer")
    if "pub const fn as_ptr(&self) -> *mut bindings::module {\n        core::ptr::null_mut()" in lib_text:
        raise ContractError("ThisModule::as_ptr was replaced by a null pointer")

    macro_text = _decode_text(
        preimage_bytes["rust/macros/module.rs"], "fixture module macro")
    loadable_module = (
        "#[cfg(MODULE)]\n"
        "            static THIS_MODULE: kernel::ThisModule = unsafe {{"
    )
    if macro_text.count(loadable_module) != 1:
        raise ContractError("loadable-module ThisModule binding differs")
    if macro_text.count("kernel::ThisModule::from_ptr(__this_module.get())") != 1:
        raise ContractError("loadable-module ThisModule is not bound to __this_module")
    if macro_text.count(
            "#[cfg(not(MODULE))]\n"
            "            static THIS_MODULE: kernel::ThisModule = unsafe {{\n"
            "                kernel::ThisModule::from_ptr(core::ptr::null_mut())") != 1:
        raise ContractError("built-in-module null owner boundary differs")

    types_text = _decode_text(preimage_bytes["rust/kernel/types.rs"], "fixture Opaque")
    opaque_start = types_text.find("#[repr(transparent)]\npub struct Opaque<T> {")
    opaque_end = types_text.find("\n}\n\nimpl<T> Opaque<T> {", opaque_start)
    if opaque_start < 0 or opaque_end < 0:
        raise ContractError("Opaque dependency block is unavailable")
    opaque_block = types_text[opaque_start:opaque_end]
    for token in ("value: UnsafeCell<MaybeUninit<T>>", "_pin: PhantomPinned"):
        if opaque_block.count(token) != 1:
            raise ContractError("Opaque dependency differs: {0}".format(token))
    bindings_text = _decode_text(
        preimage_bytes["rust/bindings/bindings_helper.h"], "fixture bindings helper")
    if "#include <linux/miscdevice.h>" in bindings_text:
        raise ContractError("miscdevice binding is already present in the replay preimage")

    expected_post_paths = {
        "rust/bindings/bindings_helper.h", "rust/kernel/lib.rs",
        "rust/kernel/miscdevice.rs", "rust/kernel/types.rs", "rust/macros/module.rs",
    }
    if set(postimage_bytes) != expected_post_paths:
        raise ContractError("post-0020 dependency path vector differs")
    post_lib = _decode_text(postimage_bytes["rust/kernel/lib.rs"], "post-0020 kernel lib")
    if post_lib.count(as_ptr) != 1 or post_lib.count("pub mod miscdevice;") != 1:
        raise ContractError("post-0020 kernel lib dependency differs")
    post_types = _decode_text(
        postimage_bytes["rust/kernel/types.rs"], "post-0019 Opaque dependency")
    for token in (
            "pub fn try_ffi_init<E>(",
            "init_func: impl FnOnce(*mut T) -> Result<(), E>",
            "init::pin_init_from_closure::<_, E>(move |slot| init_func(Self::raw_get(slot)))"):
        if post_types.count(token) != 1:
            raise ContractError("post-0019 Opaque initializer differs")
    post_bindings = _decode_text(
        postimage_bytes["rust/bindings/bindings_helper.h"], "post-0020 bindings helper")
    if post_bindings.count("#include <linux/miscdevice.h>") != 1:
        raise ContractError("post-0020 miscdevice binding differs")
    if postimage_bytes["rust/macros/module.rs"] != preimage_bytes["rust/macros/module.rs"]:
        raise ContractError("module macro changed during replay")


def _validate_deferred_consumers(contract, consumer_bytes):
    rows = contract["deferred_consumer_inventory"]
    expected_paths = [row["path"] for row in rows]
    if set(consumer_bytes) != set(expected_paths):
        raise ContractError("deferred consumer byte set differs")
    forbidden_tokens = (
        contract["candidate"]["path"],
        os.path.basename(contract["candidate"]["path"]),
        contract["candidate"]["sha256"],
        contract["result_authority"]["candidate_postimage"]["sha256"],
        "host-kernel/rocky/candidates/",
        "rocky/candidates/",
        "rs006-miscdevice-module-owner-followup-v1",
        "rs006_miscdevice_module_owner_followup",
    )
    for row in rows:
        path = row["path"]
        data = consumer_bytes[path]
        _validate_record(data, row, "deferred consumer " + path)
        text = _decode_text(data, "deferred consumer " + path)
        for token in forbidden_tokens:
            if token in text:
                raise ContractError(
                    "deferred consumer references or applies the unintegrated candidate: {0}".format(path))

    series = _load_json_bytes(
        consumer_bytes["host-kernel/rocky/patches/series.json"], "Rocky series")
    for row in series.get("patches", []):
        if type(row) is not dict or type(row.get("path")) is not str:
            raise ContractError("Rocky series patch row differs")
        if "candidates/" in row["path"] or "0020-followup" in row["path"]:
            raise ContractError("Rocky series applies the unintegrated candidate")
    rs006 = _load_json_bytes(
        consumer_bytes["host-kernel/contracts/rs006-miscdevice-substrate-v1.json"],
        "predecessor RS-006 contract",
    )
    readiness = rs006.get("readiness")
    if type(readiness) is not dict or readiness.get("status") != "NOT_READY" \
            or readiness.get("credit_eligible") is not False:
        raise ContractError("predecessor RS-006 false readiness state differs")
    rk006 = _load_json_bytes(
        consumer_bytes["host-kernel/rocky/rk006-patch-authority-v1.json"],
        "RK-006 patch authority",
    )
    gate = rk006.get("gate")
    if type(gate) is not dict or gate.get("gate_status_claimed") != "TODO" \
            or gate.get("credit_eligible") is not False \
            or gate.get("tracker_credit") is not False:
        raise ContractError("RK-006 false gate state differs")
    source_lock = _load_json_bytes(
        consumer_bytes["host-kernel/rocky/source-lock.json"], "source lock")
    if type(source_lock.get("gate")) is not dict \
            or source_lock["gate"].get("credit_eligible") is not False:
        raise ContractError("source-lock false credit state differs")
    stage = _load_json_bytes(
        consumer_bytes["host-kernel/kbuild/stage-manifest.json"], "stage manifest")
    if type(stage.get("readiness")) is not dict \
            or stage["readiness"].get("credit_eligible") is not False:
        raise ContractError("stage-manifest false readiness state differs")


def _registration_block(text):
    start = text.find("pub struct MiscDeviceRegistration<T> {")
    end = text.find("}\n\n// SAFETY:", start)
    if start < 0 or end < 0:
        raise ContractError("pinned registration block is unavailable")
    return text[start:end]


def _validate_postimage(data, expected):
    _validate_record(data, expected, "candidate miscdevice postimage")
    try:
        text = data.decode("utf-8")
    except UnicodeError as error:
        raise ContractError("candidate postimage is not UTF-8: {0}".format(error))
    exact_once = (
        "const MODULE: &'static ThisModule;",
        "owner: T::MODULE.as_ptr(),",
        "compat_ioctl: maybe_fn(T::HAS_COMPAT_IOCTL, fops_compat_ioctl::<T>),",
        "const VTABLE: bindings::file_operations = bindings::file_operations {",
        "#[pin_data(PinnedDrop)]",
        "inner: Opaque<bindings::miscdevice>,",
        "unsafe { bindings::misc_deregister(self.inner.get()) };",
    )
    for token in exact_once:
        if text.count(token) != 1:
            raise ContractError("postimage token must occur exactly once: {0}".format(token))
    if "bindings::compat_ptr_ioctl" in text:
        raise ContractError("postimage retains an implicit compat fallback")
    if "const fn create_vtable<T: MiscDevice>() -> &'static bindings::file_operations" not in text:
        raise ContractError("postimage vtable is not static per implementation type")
    registration = _registration_block(text)
    if "file_operations" in registration or "fops" in registration:
        raise ContractError("registration embeds per-registration file operations")
    pin_index = text.index("#[pin_data(PinnedDrop)]")
    inner_index = text.index("inner: Opaque<bindings::miscdevice>,")
    register_index = text.index("bindings::misc_register(slot)")
    drop_index = text.index("bindings::misc_deregister(self.inner.get())")
    if not pin_index < inner_index < register_index < drop_index:
        raise ContractError("pinned register/deregister ordering differs")


def _validate_compile_fixture(data, expected):
    _validate_record(data, expected, "compile-shape fixture")
    try:
        text = data.decode("utf-8")
    except UnicodeError as error:
        raise ContractError("compile-shape fixture is not UTF-8: {0}".format(error))
    required = (
        "const MODULE: &'static ThisModule;",
        "const MODULE: &'static ThisModule = &THIS_MODULE;",
        "owner: T::MODULE.as_ptr(),",
        "compat_ioctl: maybe_fn(T::HAS_COMPAT_IOCTL, fops_compat_ioctl::<T>),",
        "assert_eq!(fops.owner, THIS_MODULE.as_ptr());",
        "assert_ne!(fops.owner, OTHER_MODULE.as_ptr());",
        "assert!(create_vtable::<NoCompatDevice>().compat_ioctl.is_none());",
        "inner: Pin<Box<RawMiscDevice>>",
        "impl<T: MiscDevice> Drop for MiscDeviceRegistration<T>",
        "raw.registered = false;",
        "size_of::<MiscDeviceRegistration<ExplicitCompatDevice>>()",
        "assert!(std::ptr::eq(fops, create_vtable::<ExplicitCompatDevice>()));",
        "assert_eq!(DROP_STAGE.load(Ordering::SeqCst), 2);",
    )
    for token in required:
        if token not in text:
            raise ContractError("compile-shape fixture token is missing: {0}".format(token))
    if "compat_ptr_ioctl" in text:
        raise ContractError("compile-shape fixture contains an implicit compat fallback")
    implementation_blocks = {}
    for device_name in ("ExplicitCompatDevice", "NoCompatDevice"):
        marker = "impl MiscDevice for {0} {{".format(device_name)
        start = text.find(marker)
        end = text.find("\n}\n", start)
        if start < 0 or end < 0:
            raise ContractError("compile-shape {0} implementation is unavailable".format(device_name))
        implementation_blocks[device_name] = text[start:end + 2]
    explicit_block = implementation_blocks["ExplicitCompatDevice"]
    no_compat_block = implementation_blocks["NoCompatDevice"]
    module_binding = "const MODULE: &'static ThisModule = &THIS_MODULE;"
    if explicit_block.count(module_binding) != 1 or "&OTHER_MODULE" in explicit_block:
        raise ContractError("explicit-compat device is not bound to the intended ThisModule")
    if no_compat_block.count(module_binding) != 1 or "&OTHER_MODULE" in no_compat_block:
        raise ContractError("no-compat device is not bound to the intended ThisModule")
    if explicit_block.count("const HAS_COMPAT_IOCTL: bool = true;") != 1:
        raise ContractError("explicit-compat device flag differs")
    if explicit_block.count("fn compat_ioctl(") != 1:
        raise ContractError("explicit compat callback is not implemented exactly once")
    if no_compat_block.count("const HAS_COMPAT_IOCTL: bool = false;") != 1:
        raise ContractError("no-compat device flag differs")
    if "fn compat_ioctl(" in no_compat_block:
        raise ContractError("no-compat device unexpectedly implements compat ioctl")
    registration_start = text.index("struct MiscDeviceRegistration<T: MiscDevice>")
    registration_end = text.index("impl<T: MiscDevice> MiscDeviceRegistration<T>", registration_start)
    if "FileOperations" in text[registration_start:registration_end]:
        raise ContractError("compile-shape registration embeds file operations")


def _apply_patch(tree, data, label, expect_success=True):
    command = [
        "patch", "--batch", "--forward", "--fuzz=0", "--no-backup-if-mismatch",
        "-p1",
    ]
    process = subprocess.Popen(
        command,
        cwd=tree,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate(data)
    combined = stdout + stderr
    if expect_success and process.returncode != 0:
        raise ContractError(
            "{0} strict replay failed: {1}".format(
                label, combined.decode("utf-8", "replace")[-2000:]))
    if expect_success and (b"fuzz" in combined.lower() or b"offset" in combined.lower()):
        raise ContractError("{0} replay used fuzz or an offset".format(label))
    if not expect_success and process.returncode == 0:
        raise ContractError("{0} unexpectedly reapplied".format(label))
    return combined


def _tree_records(root):
    records = {}
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        directories.sort()
        filenames.sort()
        for directory_name in directories:
            directory_path = os.path.join(current, directory_name)
            if stat.S_ISLNK(os.lstat(directory_path).st_mode):
                raise ContractError("replay fixture contains a symlink directory")
        for filename in filenames:
            path = os.path.join(current, filename)
            info = os.lstat(path)
            if not stat.S_ISREG(info.st_mode):
                raise ContractError("replay fixture contains a non-regular file")
            with open(path, "rb") as stream:
                data = stream.read()
            relative = os.path.relpath(path, root).replace(os.sep, "/")
            records[relative] = (len(data), _sha256(data))
    return records


def _bytes_for(repo_root, relative, overrides, label):
    if relative in overrides:
        data = overrides[relative]
        if type(data) is not bytes:
            raise ContractError("{0} override must be bytes".format(label))
        return data
    return _read_regular(repo_root, relative, label)


def _replay_candidate(contract, input_bytes):
    predecessor = contract["predecessor"]
    candidate = contract["candidate"]
    patch_rows = predecessor["ordered_patches"]
    patch_bytes = []
    for index, row in enumerate(patch_rows):
        data = input_bytes[row["path"]]
        _validate_record(data, row, "predecessor patch {0}".format(index))
        patch_bytes.append(data)
    candidate_bytes = input_bytes[candidate["path"]]
    _validate_candidate_patch(candidate_bytes, candidate)
    fixture = predecessor["local_replay_fixture"]
    fixture_prefix = fixture["path"] + "/"
    fixture_bytes = {}
    for row in fixture["inventory"]:
        repository_path = fixture_prefix + row["path"]
        data = input_bytes[repository_path]
        _validate_record(data, row, "replay fixture " + row["path"])
        fixture_bytes[row["path"]] = data

    with tempfile.TemporaryDirectory(prefix="rs006-owner-replay-") as temporary:
        tree = os.path.join(temporary, "tree")
        os.mkdir(tree)
        for relative in sorted(fixture_bytes):
            target = os.path.join(tree, *relative.split("/"))
            parent = os.path.dirname(target)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            with open(target, "wb") as stream:
                stream.write(fixture_bytes[relative])
        if set(_tree_records(tree)) != set(fixture_bytes):
            raise ContractError("materialized replay fixture path set differs")
        _apply_patch(tree, patch_bytes[0], "patch 0019")
        _apply_patch(tree, patch_bytes[1], "patch 0020")
        dependency_postimages = {}
        for row in predecessor["post_0020_dependency_inventory"]:
            path = os.path.join(tree, *row["path"].split("/"))
            with open(path, "rb") as stream:
                data = stream.read()
            _validate_record(data, row, "post-0020 dependency " + row["path"])
            dependency_postimages[row["path"]] = data
        _validate_replay_dependency_semantics(fixture_bytes, dependency_postimages)
        predecessor_bytes = dependency_postimages["rust/kernel/miscdevice.rs"]
        _validate_record(predecessor_bytes, predecessor["miscdevice_postimage"],
                         "patch-0020 miscdevice postimage")
        miscdevice_path = os.path.join(tree, "rust", "kernel", "miscdevice.rs")
        before = _tree_records(tree)
        _apply_patch(tree, candidate_bytes, "module-owner candidate")
        after = _tree_records(tree)
        changed = sorted(
            path for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        )
        if changed != candidate["touched_paths"]:
            raise ContractError("candidate replay changed paths outside its exact vector")
        with open(miscdevice_path, "rb") as stream:
            postimage = stream.read()
        _validate_postimage(postimage, contract["result_authority"]["candidate_postimage"])
        _apply_patch(tree, candidate_bytes, "module-owner candidate second apply", False)
        with open(miscdevice_path, "rb") as stream:
            after_second_apply = stream.read()
        if after_second_apply != postimage:
            raise ContractError("failed second apply changed the candidate postimage")
        return {
            "changed_paths": changed,
            "postimage_sha256": _sha256(postimage),
            "postimage_size": len(postimage),
            "predecessor_patch_count": len(patch_rows),
            "strict_fuzz": 0,
        }


def _compile_fixture(data, require_rustc):
    compiler = shutil.which("rustc")
    if compiler is None:
        if require_rustc:
            raise ContractError("rustc is required for the compile-shape fixture")
        return {"compiler": "unavailable", "status": "SKIPPED"}
    with tempfile.TemporaryDirectory(prefix="rs006-owner-compile-") as temporary:
        source = os.path.join(temporary, "fixture.rs")
        binary = os.path.join(temporary, "fixture")
        with open(source, "wb") as stream:
            stream.write(data)
        command = [compiler, "--edition=2021", "-D", "warnings", source, "-o", binary]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise ContractError(
                "compile-shape fixture failed: {0}".format(
                    (stdout + stderr).decode("utf-8", "replace")[-3000:]))
        process = subprocess.Popen([binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise ContractError(
                "compile-shape fixture assertions failed: {0}".format(
                    (stdout + stderr).decode("utf-8", "replace")[-3000:]))
        return {"compiler": os.path.basename(compiler), "status": "PASS"}


def check(repo_root, contract_override=None, file_overrides=None,
          compile_fixture=True, require_rustc=False):
    if type(compile_fixture) is not bool or type(require_rustc) is not bool:
        raise ContractError("compile controls must be booleans")
    if type(repo_root) is not str or not repo_root:
        raise ContractError("repository root must be nonempty text")
    repo_root = os.path.abspath(repo_root)
    if file_overrides is None:
        overrides = {}
    elif type(file_overrides) is dict:
        overrides = dict(file_overrides)
    else:
        raise ContractError("file overrides must be a dictionary")
    allowed_overrides = {
        CANDIDATE_PATH,
        COMPILE_FIXTURE_PATH,
        "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
        "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch",
    }
    if not set(overrides).issubset(allowed_overrides):
        raise ContractError("file override keys exceed the bounded input set")
    for relative, data in overrides.items():
        if type(data) is not bytes:
            raise ContractError("file override must be bytes: {0}".format(relative))

    snapshot = None
    failure = None
    result = None
    try:
        snapshot = _AggregateSnapshot(repo_root)
        captured_contract = snapshot.open_file(
            CONTRACT_PATH, "follow-up contract", _MAX_AUTHORITY_BYTES)
        contract_bytes = captured_contract if contract_override is None else contract_override
        contract = _load_contract(contract_bytes)
        snapshot.checkpoint("contract validation")

        candidate = contract["candidate"]
        snapshot.open_file(candidate["path"], "candidate patch", candidate["size"])
        fixture_expected = contract["fixture"]
        snapshot.open_file(
            fixture_expected["path"], "compile-shape fixture", fixture_expected["size"])
        for index, row in enumerate(contract["predecessor"]["ordered_patches"]):
            snapshot.open_file(
                row["path"], "predecessor patch {0}".format(index), row["size"])
        for row in contract["deferred_consumer_inventory"]:
            snapshot.open_file(
                row["path"], "deferred consumer " + row["path"], row["size"])
        local_fixture = contract["predecessor"]["local_replay_fixture"]
        for row in local_fixture["inventory"]:
            repository_path = local_fixture["path"] + "/" + row["path"]
            snapshot.open_file(
                repository_path, "replay fixture " + row["path"], row["size"])
        snapshot.assert_tree(
            local_fixture["path"],
            [row["path"] for row in local_fixture["inventory"]],
            "replay fixture inventory",
        )
        snapshot.checkpoint("aggregate input capture")

        input_bytes = snapshot.bytes_by_path()
        input_bytes.update(overrides)
        _validate_candidate_patch(input_bytes[candidate["path"]], candidate)
        snapshot.checkpoint("candidate validation")
        consumer_bytes = {
            row["path"]: input_bytes[row["path"]]
            for row in contract["deferred_consumer_inventory"]
        }
        _validate_deferred_consumers(contract, consumer_bytes)
        snapshot.checkpoint("deferred false-state validation")
        fixture_bytes = input_bytes[fixture_expected["path"]]
        _validate_compile_fixture(fixture_bytes, fixture_expected)
        snapshot.checkpoint("compile-shape validation")
        replay = _replay_candidate(contract, input_bytes)
        snapshot.checkpoint("strict candidate replay validation")
        if compile_fixture:
            compile_result = _compile_fixture(fixture_bytes, require_rustc)
        else:
            if require_rustc:
                raise ContractError("cannot require rustc while fixture compilation is disabled")
            compile_result = {"compiler": "not-requested", "status": "SKIPPED"}
        snapshot.checkpoint("fixture compile validation")
        result = {
            "claims": dict(_expected_claims()),
            "compile_shape": compile_result,
            "contract_id": contract["contract_id"],
            "integration_status": "required-missing",
            "replay": replay,
            "review_status": "required-missing",
            "runtime_status": "required-missing",
            "status": "CANDIDATE_VALIDATED_NONAUTHORITATIVE",
        }
    except ContractError as error:
        failure = error
    except (OSError, TypeError, ValueError) as error:
        failure = ContractError("aggregate validation failed closed: {0}".format(error))
    if snapshot is not None:
        try:
            snapshot.close()
        except ContractError as error:
            if failure is None:
                failure = error
    if failure is not None:
        raise failure
    if result is None:
        raise ContractError("aggregate validation produced no result")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--skip-fixture-compile", action="store_true")
    parser.add_argument("--require-rustc", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = check(
            args.repo,
            compile_fixture=not args.skip_fixture_compile,
            require_rustc=args.require_rustc,
        )
    except ContractError as error:
        print("ERROR: {0}".format(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
