#!/usr/bin/env python3
"""Adversarial tests for the additive RK-001 child-inventory v2 scaffold."""

from __future__ import print_function

import ast
import copy
import gzip
import hashlib
import io
import lzma
import os
import stat
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rocky_kernel_license_child_inventory_v2 as inventory


CONTRACT = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/"
    / "rk001-license-child-inventory-contract-ef58-v2.json"
)
CHECKER = REPO_ROOT / "scripts/rocky_kernel_license_child_inventory_v2.py"
TESTS = REPO_ROOT / "scripts/tests/test_rocky_kernel_license_child_inventory_v2.py"
WORKFLOW = REPO_ROOT / ".github/workflows/rk001-license-child-inventory-v2.yml"
ASSIGNED_FILES = {
    ".github/workflows/rk001-license-child-inventory-v2.yml",
    "host-kernel/rocky/evidence/rk001-license-child-inventory-contract-ef58-v2.json",
    "scripts/rocky_kernel_license_child_inventory_v2.py",
    "scripts/tests/test_rocky_kernel_license_child_inventory_v2.py",
}


def add_directory(archive, name):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    archive.addfile(info)


def add_regular(archive, name, data):
    info = tarfile.TarInfo(name)
    info.type = tarfile.REGTYPE
    info.mode = 0o644
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def add_symlink(archive, name, target):
    info = tarfile.TarInfo(name)
    info.type = tarfile.SYMTYPE
    info.mode = 0o777
    info.linkname = target
    archive.addfile(info)


def add_hardlink(archive, name, target):
    info = tarfile.TarInfo(name)
    info.type = tarfile.LNKTYPE
    info.mode = 0o644
    info.linkname = target
    archive.addfile(info)


def add_fifo(archive, name):
    info = tarfile.TarInfo(name)
    info.type = tarfile.FIFOTYPE
    info.mode = 0o644
    archive.addfile(info)


def archive_record(path, template):
    record = copy.deepcopy(template)
    data = path.read_bytes()
    record["size"] = len(data)
    record["sha256"] = hashlib.sha256(data).hexdigest()
    return record


def gzip_bytes(data):
    target = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as stream:
        stream.write(data)
    return target.getvalue()


def normal_archive(path, nested=False):
    with tarfile.open(str(path), "w:xz") as archive:
        add_directory(archive, "root/")
        add_regular(archive, "root/file.txt", b"SPDX-License-Identifier: MIT\n")
        if nested:
            add_regular(archive, "root/disguised.bin", gzip_bytes(b"nested archive\n"))
        add_symlink(archive, "root/link", "file.txt")
        add_hardlink(archive, "root/hard", "root/file.txt")


def restore_tree(path):
    path = Path(path)
    if not path.exists():
        return
    for directory, subdirectories, files in os.walk(str(path), topdown=False):
        for name in files:
            os.chmod(str(Path(directory) / name), 0o600)
        for name in subdirectories:
            os.chmod(str(Path(directory) / name), 0o700)
    os.chmod(str(path), 0o700)


class ChildInventoryV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_bytes = CONTRACT.read_bytes()
        cls.authority = inventory.read_json_bytes(
            cls.contract_bytes, "test contract", canonical=True
        )
        inventory.validate_contract_schema(copy.deepcopy(cls.authority))

    def policy(self):
        return copy.deepcopy(self.authority["capture_policy"])

    def one_inventory(self, root, index=0, nested=False):
        path = Path(root) / ("archive-{0}.tar.xz".format(index))
        normal_archive(path, nested=nested)
        container = archive_record(path, self.authority["containers"][index])
        result = inventory.inventory_tar_xz(path, container, self.policy())
        return path, container, result

    def test_repository_contract_and_frozen_inputs_pass(self):
        authority, data = inventory.check_repository(REPO_ROOT)
        self.assertEqual(data, self.contract_bytes)
        self.assertEqual(authority, self.authority)

    def test_contract_is_canonical_null_count_and_strictly_non_crediting(self):
        self.assertEqual(
            self.contract_bytes,
            inventory.canonical_json(self.authority, newline=True),
        )
        self.assertIsNone(self.authority["expected_result"]["stablelists_child_count"])
        self.assertIsNone(self.authority["expected_result"]["kabi_dw_child_count"])
        self.assertEqual(
            set(self.authority["claims"].values()), {False}
        )
        self.assertEqual(self.authority["gate"], inventory.EXPECTED_GATE)

    def test_contract_rejects_claim_count_container_and_bool_integer_promotions(self):
        mutations = []
        promoted = copy.deepcopy(self.authority)
        promoted["claims"]["tracker_credit"] = True
        mutations.append(promoted)
        counted = copy.deepcopy(self.authority)
        counted["expected_result"]["stablelists_child_count"] = 1
        mutations.append(counted)
        retargeted = copy.deepcopy(self.authority)
        retargeted["containers"][0]["sha256"] = "0" * 64
        mutations.append(retargeted)
        aliased = copy.deepcopy(self.authority)
        aliased["gate"]["points_awarded"] = False
        mutations.append(aliased)
        for authority in mutations:
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.validate_contract_schema(authority)

    def test_contract_exactly_freezes_all_caps_and_blocker_text(self):
        expected_caps = {
            "maximum_archive_members": 250000,
            "maximum_archive_uncompressed_bytes": 536870912,
            "maximum_jsonl_uncompressed_bytes": 268435456,
            "maximum_member_bytes": 67108864,
            "maximum_path_bytes": 4096,
        }
        for key, expected in expected_caps.items():
            self.assertEqual(self.authority["capture_policy"][key], expected)
            mutated = copy.deepcopy(self.authority)
            mutated["capture_policy"][key] = 10 ** 30
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.validate_contract_schema(mutated)
        mutated = copy.deepcopy(self.authority)
        mutated["remaining_blockers"] = ["fabricated blocker"] * 6
        with self.assertRaises(inventory.ChildInventoryError):
            inventory.validate_contract_schema(mutated)
        self.assertEqual(
            self.authority["remaining_blockers"], inventory.EXPECTED_REMAINING_BLOCKERS
        )
        self.assertEqual(
            self.authority["capture_policy"]["container_open_policy"],
            "descriptor-rooted-nofollow-ancestor-replay-v1",
        )
        self.assertEqual(
            self.authority["artifact_policy"]["verification_snapshot_policy"],
            "single-retained-dirfd-and-member-fd-replay-v1",
        )
        self.assertEqual(
            self.authority["artifact_policy"]["member_set_policy"],
            "exact-initial-and-final-dirfd-list-v1",
        )

    def test_recursive_exact_comparison_rejects_nested_bool_integer_alias(self):
        with self.assertRaises(inventory.ChildInventoryError):
            inventory.require_exact(
                {"gate": {"points_awarded": False}},
                {"gate": {"points_awarded": 0}},
                "nested gate fixture",
            )

    def test_capture_binding_is_exact_and_rejects_bool_or_mutable_identity(self):
        binding = {
            "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
            "github_head_sha": "a" * 40,
            "github_repository": inventory.EXPECTED_REPOSITORY,
            "github_run_attempt": "1",
            "github_run_id": "123",
        }
        inventory.validate_capture_binding(binding)
        for key, value in (
            ("github_head_sha", "main"),
            ("github_repository", "fork/repository"),
            ("github_run_id", 123),
            ("github_run_attempt", "0"),
        ):
            mutated = copy.deepcopy(binding)
            mutated[key] = value
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.validate_capture_binding(mutated)

    def test_bounded_file_is_descriptor_first_and_ignores_path_read_swap(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-bounded-file-") as root:
            root_path = Path(root)
            held = root_path / "authority.json"
            evil = root_path / "evil.json"
            good_bytes = b'{"authority":"GOOD"}\n'
            evil_bytes = b'{"authority":"EVIL"}\n'
            self.assertEqual(len(good_bytes), len(evil_bytes))
            held.write_bytes(good_bytes)
            evil.write_bytes(evil_bytes)
            original_read_bytes = Path.read_bytes

            def swap_path_read(path_object):
                if path_object != held:
                    return original_read_bytes(path_object)
                retained = root_path / "retained.json"
                os.rename(str(held), str(retained))
                held.symlink_to(evil.name)
                try:
                    return original_read_bytes(held)
                finally:
                    held.unlink()
                    os.rename(str(retained), str(held))

            with mock.patch.object(Path, "read_bytes", new=swap_path_read):
                self.assertEqual(
                    inventory._bounded_file(held, "descriptor-first fixture", 4096),
                    good_bytes,
                )
            symlink = root_path / "authority-link.json"
            symlink.symlink_to(held.name)
            with self.assertRaises(inventory.ChildInventoryError):
                inventory._bounded_file(symlink, "symlink fixture", 4096)

    def test_bounded_file_rejects_parent_symlink_swap_during_leaf_open(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-parent-race-") as root:
            root_path = Path(root)
            authority_root = root_path / "authority-root"
            evil_root = root_path / "evil-root"
            retained_root = root_path / "retained-authority-root"
            authority_root.mkdir()
            evil_root.mkdir()
            leaf = authority_root / "authority.json"
            evil_leaf = evil_root / leaf.name
            good_bytes = b'{"authority":"GOOD"}\n'
            evil_bytes = b'{"authority":"EVIL"}\n'
            self.assertEqual(len(good_bytes), len(evil_bytes))
            leaf.write_bytes(good_bytes)
            evil_leaf.write_bytes(evil_bytes)
            original_open = os.open
            original_close = os.close
            state = {"leaf_descriptor": None, "swapped": False}

            def racing_open(path, flags, *args, **kwargs):
                path_text = os.fspath(path)
                if not state["swapped"] and path_text in (str(leaf), leaf.name):
                    os.rename(str(authority_root), str(retained_root))
                    authority_root.symlink_to(evil_root.name, target_is_directory=True)
                    state["swapped"] = True
                    descriptor = original_open(path, flags, *args, **kwargs)
                    state["leaf_descriptor"] = descriptor
                    return descriptor
                return original_open(path, flags, *args, **kwargs)

            def racing_close(descriptor):
                try:
                    return original_close(descriptor)
                finally:
                    if (
                        descriptor == state["leaf_descriptor"]
                        and state["swapped"]
                        and authority_root.is_symlink()
                    ):
                        authority_root.unlink()
                        os.rename(str(retained_root), str(authority_root))

            with mock.patch.object(os, "open", side_effect=racing_open), mock.patch.object(
                os, "close", side_effect=racing_close
            ):
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory._bounded_file(leaf, "ancestor swap fixture", 4096)
            self.assertTrue(state["swapped"])
            self.assertEqual(leaf.read_bytes(), good_bytes)

    def test_sequential_inventory_regular_directory_and_link_closure(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-basic-") as root:
            _path, container, result = self.one_inventory(root)
            capture = result["capture"]
            self.assertEqual(capture["member_count"], 4)
            self.assertEqual(capture["review_unit_count"], 3)
            self.assertEqual(capture["directory_count"], 1)
            self.assertEqual(capture["regular_count"], 1)
            self.assertEqual(capture["symlink_count"], 1)
            self.assertEqual(capture["hardlink_count"], 1)
            self.assertFalse(capture["child_review_complete"])
            self.assertFalse(capture["transitive_archive_expansion_complete"])
            self.assertEqual(
                capture["source_identity"], {"archive_sha256": container["sha256"]}
            )
            paths = [record["path"] for record in result["records"]]
            self.assertEqual(paths, sorted(paths))
            self.assertEqual(len(paths), len(set(paths)))

    def test_nested_archive_is_counted_but_never_promotes_completion(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-nested-") as root:
            _path, _container, result = self.one_inventory(root, nested=True)
            self.assertEqual(result["capture"]["nested_archive_member_count"], 1)
            disguised = [
                record
                for record in result["records"]
                if record["path"].endswith("/disguised.bin")
            ]
            self.assertEqual(len(disguised), 1)
            self.assertEqual(disguised[0]["nested_archive_format"], "gzip")
            self.assertFalse(
                result["capture"]["transitive_archive_expansion_complete"]
            )

    def test_nested_archive_detection_uses_magic_not_filename_suffix(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-nested-magic-") as root:
            path = Path(root) / "archive.tar.xz"
            with tarfile.open(str(path), "w:xz") as archive:
                add_regular(archive, "fake.tar.gz", b"plain text, not an archive\n")
                add_regular(archive, "real.data", gzip_bytes(b"real nested gzip\n"))
            container = archive_record(path, self.authority["containers"][0])
            result = inventory.inventory_tar_xz(path, container, self.policy())
            formats = {
                record["path"]: record["nested_archive_format"]
                for record in result["records"]
            }
            self.assertIsNone(formats["stablelists/fake.tar.gz"])
            self.assertEqual(formats["stablelists/real.data"], "gzip")
            self.assertEqual(result["capture"]["nested_archive_member_count"], 1)

    def test_archive_digest_and_size_drift_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-drift-") as root:
            path = Path(root) / "archive.tar.xz"
            normal_archive(path)
            container = archive_record(path, self.authority["containers"][0])
            for key, value in (("sha256", "0" * 64), ("size", container["size"] + 1)):
                mutated = copy.deepcopy(container)
                mutated[key] = value
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, mutated, self.policy())

    def test_corrupt_empty_and_non_xz_archives_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-corrupt-") as root:
            for number, data in enumerate((b"not-xz\n", b"")):
                path = Path(root) / "bad-{0}.tar.xz".format(number)
                path.write_bytes(data)
                container = archive_record(path, self.authority["containers"][0])
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, container, self.policy())
            path = Path(root) / "empty.tar.xz"
            with tarfile.open(str(path), "w:xz"):
                pass
            container = archive_record(path, self.authority["containers"][0])
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(path, container, self.policy())

    def test_nonzero_tar_tail_and_trailing_xz_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-tar-tail-") as root:
            tar_bytes = io.BytesIO()
            with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
                add_regular(archive, "root/file", b"payload")
            fixtures = (
                lzma.compress(tar_bytes.getvalue() + b"hidden-after-tar-end"),
                lzma.compress(tar_bytes.getvalue()) + b"hidden-after-xz-end",
            )
            for index, data in enumerate(fixtures):
                path = Path(root) / "tail-{0}.tar.xz".format(index)
                path.write_bytes(data)
                container = archive_record(path, self.authority["containers"][0])
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, container, self.policy())

    def test_traversal_absolute_backslash_and_duplicate_members_fail(self):
        names = (
            "../escape",
            "/absolute",
            "root\\backslash",
            "root/new\nline",
            "root/control\x1fbyte",
        )
        with tempfile.TemporaryDirectory(prefix="rk001-child-paths-") as root:
            for number, name in enumerate(names):
                path = Path(root) / "unsafe-{0}.tar.xz".format(number)
                with tarfile.open(str(path), "w:xz") as archive:
                    add_regular(archive, name, b"bad")
                container = archive_record(path, self.authority["containers"][0])
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, container, self.policy())
            duplicate = Path(root) / "duplicate.tar.xz"
            with tarfile.open(str(duplicate), "w:xz") as archive:
                add_regular(archive, "root/file", b"one")
                add_regular(archive, "root/file", b"two")
            container = archive_record(duplicate, self.authority["containers"][0])
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(duplicate, container, self.policy())

    def test_missing_escaping_and_absolute_links_fail(self):
        fixtures = (
            ("missing", "root/missing"),
            ("../../escape", None),
            ("/absolute", None),
        )
        with tempfile.TemporaryDirectory(prefix="rk001-child-links-") as root:
            for number, values in enumerate(fixtures):
                target, _unused = values
                path = Path(root) / "link-{0}.tar.xz".format(number)
                with tarfile.open(str(path), "w:xz") as archive:
                    add_directory(archive, "root/")
                    add_symlink(archive, "root/link", target)
                container = archive_record(path, self.authority["containers"][0])
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, container, self.policy())

    def test_hardlink_cycle_and_nonregular_target_fail(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-hardlinks-") as root:
            cycle = Path(root) / "cycle.tar.xz"
            with tarfile.open(str(cycle), "w:xz") as archive:
                add_hardlink(archive, "one", "two")
                add_hardlink(archive, "two", "one")
            container = archive_record(cycle, self.authority["containers"][0])
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(cycle, container, self.policy())
            directory = Path(root) / "directory-target.tar.xz"
            with tarfile.open(str(directory), "w:xz") as archive:
                add_directory(archive, "root/")
                add_hardlink(archive, "hard", "root")
            container = archive_record(directory, self.authority["containers"][0])
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(directory, container, self.policy())

    def test_symlink_cycle_fails(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-symlink-cycle-") as root:
            path = Path(root) / "cycle.tar.xz"
            with tarfile.open(str(path), "w:xz") as archive:
                add_symlink(archive, "one", "two")
                add_symlink(archive, "two", "one")
            container = archive_record(path, self.authority["containers"][0])
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(path, container, self.policy())

    def test_fifo_and_other_special_members_fail(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-special-") as root:
            path = Path(root) / "fifo.tar.xz"
            with tarfile.open(str(path), "w:xz") as archive:
                add_fifo(archive, "root/fifo")
            container = archive_record(path, self.authority["containers"][0])
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(path, container, self.policy())

    def test_member_count_member_size_total_and_path_caps_fail(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-caps-") as root:
            path = Path(root) / "caps.tar.xz"
            with tarfile.open(str(path), "w:xz") as archive:
                add_regular(archive, "root/first", b"1234")
                add_regular(archive, "root/second", b"5678")
            container = archive_record(path, self.authority["containers"][0])
            for key, value in (
                ("maximum_archive_members", 1),
                ("maximum_member_bytes", 3),
                ("maximum_archive_uncompressed_bytes", 7),
                ("maximum_path_bytes", 5),
            ):
                policy = self.policy()
                policy[key] = value
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, container, policy)

    def test_symlink_hardlink_and_writeable_container_files_fail(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-file-security-") as root:
            root_path = Path(root)
            path = root_path / "archive.tar.xz"
            normal_archive(path)
            container = archive_record(path, self.authority["containers"][0])
            alias = root_path / "alias.tar.xz"
            os.link(str(path), str(alias))
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(path, container, self.policy())
            alias.unlink()
            symlink = root_path / "link.tar.xz"
            symlink.symlink_to(path.name)
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(symlink, container, self.policy())
            os.chmod(str(path), 0o666)
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.inventory_tar_xz(path, container, self.policy())

    def test_archive_open_rejects_transient_parent_symlink_during_leaf_open(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-archive-open-race-") as root:
            root_path = Path(root)
            live = root_path / "live"
            held = root_path / "held"
            live.mkdir()
            path = live / "archive.tar.xz"
            normal_archive(path)
            container = archive_record(path, self.authority["containers"][0])
            original_open = os.open
            original_close = os.close
            state = {
                "leaf_descriptor": None,
                "restored": False,
                "rooted_leaf_open": False,
                "swapped": False,
            }

            def racing_open(open_path, flags, *args, **kwargs):
                path_text = os.fspath(open_path)
                if (
                    not state["swapped"]
                    and path_text in (str(path), path.name)
                ):
                    state["rooted_leaf_open"] = (
                        path_text == path.name and kwargs.get("dir_fd") is not None
                    )
                    os.rename(str(live), str(held))
                    live.symlink_to(held.name, target_is_directory=True)
                    state["swapped"] = True
                    descriptor = original_open(open_path, flags, *args, **kwargs)
                    state["leaf_descriptor"] = descriptor
                    return descriptor
                return original_open(open_path, flags, *args, **kwargs)

            def racing_close(descriptor):
                try:
                    return original_close(descriptor)
                finally:
                    if (
                        descriptor == state["leaf_descriptor"]
                        and state["swapped"]
                        and live.is_symlink()
                    ):
                        live.unlink()
                        os.rename(str(held), str(live))
                        state["restored"] = True

            with mock.patch.object(os, "open", side_effect=racing_open), mock.patch.object(
                os, "close", side_effect=racing_close
            ):
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, container, self.policy())
            self.assertTrue(state["swapped"])
            self.assertTrue(state["restored"])
            self.assertTrue(state["rooted_leaf_open"])
            self.assertTrue(path.is_file())

    def test_namespace_replacement_after_stream_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-race-") as root:
            root_path = Path(root)
            path = root_path / "archive.tar.xz"
            replacement = root_path / "replacement.tar.xz"
            normal_archive(path)
            normal_archive(replacement)
            container = archive_record(path, self.authority["containers"][0])
            original = inventory._validate_link_closure

            def replace_then_validate(records):
                path.unlink()
                os.rename(str(replacement), str(path))
                return original(records)

            with mock.patch.object(
                inventory, "_validate_link_closure", side_effect=replace_then_validate
            ):
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.inventory_tar_xz(path, container, self.policy())

    def test_in_place_archive_byte_swap_during_stream_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-in-place-race-") as root:
            root_path = Path(root)

            def archive_bytes(payload):
                target = io.BytesIO()
                with tarfile.open(fileobj=target, mode="w:xz") as archive:
                    add_directory(archive, "root/")
                    add_regular(archive, "root/file", payload)
                return target.getvalue()

            original_bytes = archive_bytes(b"A" * 128)
            alternate_bytes = None
            for value in range(1, 256):
                candidate = archive_bytes(bytes((value,)) * 128)
                if candidate != original_bytes and len(candidate) == len(original_bytes):
                    alternate_bytes = candidate
                    break
            self.assertIsNotNone(alternate_bytes)
            path = root_path / "archive.tar.xz"
            path.write_bytes(original_bytes)
            container = archive_record(path, self.authority["containers"][0])
            original_hash_descriptor = inventory._hash_descriptor
            original_link_closure = inventory._validate_link_closure
            state = {"hash_calls": 0}

            def swap_after_initial_hash(*args, **kwargs):
                result = original_hash_descriptor(*args, **kwargs)
                state["hash_calls"] += 1
                if state["hash_calls"] == 1:
                    with path.open("r+b") as stream:
                        stream.write(alternate_bytes)
                        stream.flush()
                        os.fsync(stream.fileno())
                return result

            def restore_before_final_hash(records):
                with path.open("r+b") as stream:
                    stream.write(original_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                return original_link_closure(records)

            try:
                with mock.patch.object(
                    inventory, "_hash_descriptor", side_effect=swap_after_initial_hash
                ), mock.patch.object(
                    inventory,
                    "_validate_link_closure",
                    side_effect=restore_before_final_hash,
                ):
                    with self.assertRaises(inventory.ChildInventoryError):
                        inventory.inventory_tar_xz(path, container, self.policy())
            finally:
                path.write_bytes(original_bytes)
            self.assertEqual(path.read_bytes(), original_bytes)

    def test_member_record_schema_rejects_source_group_link_and_directory_drift(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-records-") as root:
            _path, container, result = self.one_inventory(root)
            record = result["records"][0]
            mutations = []
            wrong_group = copy.deepcopy(record)
            wrong_group["archive_group_id"] = "exact-content:" + "0" * 64
            mutations.append(wrong_group)
            wrong_source = copy.deepcopy(record)
            wrong_source["source_identity"] = {"archive_sha256": "0" * 64}
            mutations.append(wrong_source)
            extra = copy.deepcopy(record)
            extra["reviewed"] = True
            mutations.append(extra)
            for mutated in mutations:
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.validate_member_record(mutated, container)

    def test_member_cap_and_link_size_digest_are_type_derived(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-record-derivation-") as root:
            _path, container, result = self.one_inventory(root)
            by_type = {record["entry_type"]: record for record in result["records"]}
            too_large = copy.deepcopy(by_type["regular"])
            too_large["size"] = 67108865
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.validate_member_record(too_large, container)
            for entry_type, bogus_size in (("symlink", 999), ("hardlink", 888)):
                bogus = copy.deepcopy(by_type[entry_type])
                bogus["size"] = bogus_size
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.validate_member_record(bogus, container)
                bogus = copy.deepcopy(by_type[entry_type])
                bogus["sha256"] = hashlib.sha256(b"unrelated").hexdigest()
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory.validate_member_record(bogus, container)
                target_bytes = by_type[entry_type]["link_target"].encode("utf-8")
                self.assertEqual(by_type[entry_type]["size"], len(target_bytes))
                self.assertEqual(
                    by_type[entry_type]["sha256"],
                    hashlib.sha256(target_bytes).hexdigest(),
                )

    def synthetic_authority_results(self, root):
        root_path = Path(root)
        authority = copy.deepcopy(self.authority)
        results = []
        for index in range(2):
            path = root_path / "capture-source-{0}.tar.xz".format(index)
            normal_archive(path, nested=index == 1)
            authority["containers"][index] = archive_record(
                path, authority["containers"][index]
            )
            results.append(
                inventory.inventory_tar_xz(
                    path, authority["containers"][index], authority["capture_policy"]
                )
            )
        return authority, results

    def test_deterministic_capture_and_self_verification(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-capture-") as root:
            root_path = Path(root)
            authority, results = self.synthetic_authority_results(root)
            contract_bytes = inventory.canonical_json(authority, newline=True)
            binding = {
                "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
                "github_head_sha": "a" * 40,
                "github_repository": inventory.EXPECTED_REPOSITORY,
                "github_run_attempt": "1",
                "github_run_id": "123",
            }
            first = root_path / "first"
            second = root_path / "second"
            try:
                with mock.patch.object(
                    inventory, "validate_contract_schema", return_value=authority
                ):
                    summary = inventory.write_capture(
                        first, authority, contract_bytes, results, binding
                    )
                    inventory.write_capture(
                        second, authority, contract_bytes, results, binding
                    )
                    inventory.verify_capture(first, authority, contract_bytes)
                self.assertEqual(summary["claims"], inventory.EXPECTED_CLAIMS)
                self.assertEqual(summary["result_authority_status"], "required-missing")
                for name in authority["artifact_policy"]["output_members"]:
                    self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            finally:
                restore_tree(first)
                restore_tree(second)

    def test_capture_checksum_summary_and_stream_tamper_fail(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-tamper-") as root:
            root_path = Path(root)
            authority, results = self.synthetic_authority_results(root)
            contract_bytes = inventory.canonical_json(authority, newline=True)
            binding = {
                "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
                "github_head_sha": "b" * 40,
                "github_repository": inventory.EXPECTED_REPOSITORY,
                "github_run_attempt": "1",
                "github_run_id": "456",
            }
            output = root_path / "capture"
            try:
                with mock.patch.object(
                    inventory, "validate_contract_schema", return_value=authority
                ):
                    inventory.write_capture(
                        output, authority, contract_bytes, results, binding
                    )
                    target = output / authority["containers"][0]["output_member"]
                    os.chmod(str(target), 0o600)
                    target.write_bytes(target.read_bytes() + b"tamper")
                    os.chmod(str(target), 0o444)
                    with self.assertRaises(inventory.ChildInventoryError):
                        inventory.verify_capture(output, authority, contract_bytes)
            finally:
                restore_tree(output)

    def test_verify_uses_one_retained_byte_snapshot_for_hash_and_parse(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-capture-byte-race-") as root:
            root_path = Path(root)
            authority, results = self.synthetic_authority_results(root)
            contract_bytes = inventory.canonical_json(authority, newline=True)
            binding = {
                "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
                "github_head_sha": "f" * 40,
                "github_repository": inventory.EXPECTED_REPOSITORY,
                "github_run_attempt": "5",
                "github_run_id": "321",
            }
            output = root_path / "capture"
            try:
                with mock.patch.object(
                    inventory, "validate_contract_schema", return_value=authority
                ):
                    inventory.write_capture(
                        output, authority, contract_bytes, results, binding
                    )
                    target_name = authority["containers"][0]["output_member"]
                    target = output / target_name
                    checksum_path = output / "SHA256SUMS"
                    retained_bytes = target.read_bytes()
                    alternate = bytearray(retained_bytes)
                    alternate[len(alternate) // 2] ^= 1
                    alternate_bytes = bytes(alternate)
                    retained_sha = hashlib.sha256(retained_bytes).hexdigest()
                    alternate_sha = hashlib.sha256(alternate_bytes).hexdigest()
                    self.assertNotEqual(retained_sha, alternate_sha)
                    old_line = (retained_sha + "  " + target_name + "\n").encode(
                        "ascii"
                    )
                    new_line = (alternate_sha + "  " + target_name + "\n").encode(
                        "ascii"
                    )
                    checksum_bytes = checksum_path.read_bytes()
                    self.assertEqual(checksum_bytes.count(old_line), 1)
                    os.chmod(str(checksum_path), 0o600)
                    checksum_path.write_bytes(checksum_bytes.replace(old_line, new_line, 1))
                    os.chmod(str(checksum_path), 0o444)

                    original_file_record = inventory.file_record
                    state = {"path_hash_calls": 0}

                    def stream_alternate_only_for_path_hash(record_path):
                        if Path(record_path) != target:
                            return original_file_record(record_path)
                        state["path_hash_calls"] += 1
                        os.chmod(str(target), 0o600)
                        target.write_bytes(alternate_bytes)
                        os.chmod(str(target), 0o444)
                        try:
                            return original_file_record(target)
                        finally:
                            os.chmod(str(target), 0o600)
                            target.write_bytes(retained_bytes)
                            os.chmod(str(target), 0o444)

                    probe = stream_alternate_only_for_path_hash(target)
                    self.assertEqual(probe["sha256"], alternate_sha)
                    self.assertEqual(probe["size"], len(alternate_bytes))
                    self.assertEqual(target.read_bytes(), retained_bytes)
                    state["path_hash_calls"] = 0
                    with mock.patch.object(
                        inventory,
                        "file_record",
                        side_effect=stream_alternate_only_for_path_hash,
                    ):
                        with self.assertRaises(inventory.ChildInventoryError):
                            inventory.verify_capture(output, authority, contract_bytes)
                    self.assertEqual(state["path_hash_calls"], 0)
                    self.assertEqual(target.read_bytes(), retained_bytes)
            finally:
                restore_tree(output)

    def test_verify_rejects_transient_extra_member_during_dirfd_listing(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-capture-set-race-") as root:
            root_path = Path(root)
            authority, results = self.synthetic_authority_results(root)
            contract_bytes = inventory.canonical_json(authority, newline=True)
            binding = {
                "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
                "github_head_sha": "1" * 40,
                "github_repository": inventory.EXPECTED_REPOSITORY,
                "github_run_attempt": "6",
                "github_run_id": "654321",
            }
            output = root_path / "capture"
            hidden = output / ".transient-hidden"
            try:
                with mock.patch.object(
                    inventory, "validate_contract_schema", return_value=authority
                ):
                    inventory.write_capture(
                        output, authority, contract_bytes, results, binding
                    )
                    original_listdir = os.listdir
                    state = {"calls": 0}

                    def transient_member_listdir(directory):
                        names = original_listdir(directory)
                        state["calls"] += 1
                        if state["calls"] == 1:
                            os.chmod(str(output), 0o755)
                            hidden.write_bytes(b"not-authorized\n")
                            os.chmod(str(hidden), 0o444)
                            os.chmod(str(output), 0o555)
                        elif state["calls"] == 2:
                            self.assertIn(hidden.name, names)
                            os.chmod(str(output), 0o755)
                            hidden.unlink()
                            os.chmod(str(output), 0o555)
                        return names

                    try:
                        with mock.patch.object(
                            os, "listdir", side_effect=transient_member_listdir
                        ):
                            with self.assertRaises(inventory.ChildInventoryError):
                                inventory.verify_capture(
                                    output, authority, contract_bytes
                                )
                    finally:
                        if hidden.exists():
                            os.chmod(str(output), 0o755)
                            hidden.unlink()
                            os.chmod(str(output), 0o555)
                    self.assertEqual(state["calls"], 2)
                    self.assertFalse(hidden.exists())
            finally:
                restore_tree(output)

    def test_output_must_be_fresh_and_capture_member_modes_are_read_only(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-output-") as root:
            root_path = Path(root)
            authority, results = self.synthetic_authority_results(root)
            contract_bytes = inventory.canonical_json(authority, newline=True)
            binding = {
                "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
                "github_head_sha": "c" * 40,
                "github_repository": inventory.EXPECTED_REPOSITORY,
                "github_run_attempt": "2",
                "github_run_id": "789",
            }
            output = root_path / "capture"
            try:
                with mock.patch.object(
                    inventory, "validate_contract_schema", return_value=authority
                ):
                    inventory.write_capture(
                        output, authority, contract_bytes, results, binding
                    )
                    for path in output.iterdir():
                        self.assertEqual(stat.S_IMODE(path.lstat().st_mode), 0o444)
                    with self.assertRaises(inventory.ChildInventoryError):
                        inventory.write_capture(
                            output, authority, contract_bytes, results, binding
                        )
            finally:
                restore_tree(output)

    def test_gzip_stream_is_deterministic_and_has_no_filename_or_time(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-gzip-") as root:
            _path, _container, result = self.one_inventory(root)
            first = Path(root) / "first.gz"
            second = Path(root) / "second.gz"
            inventory._write_gzip_records(first, result["records"])
            inventory._write_gzip_records(second, result["records"])
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes()[:10], inventory.EXPECTED_GZIP_HEADER)
            uncompressed = inventory._decompress_canonical_gzip(
                first.read_bytes(), self.authority["capture_policy"]["maximum_jsonl_uncompressed_bytes"]
            )
            self.assertEqual(
                uncompressed,
                b"".join(
                    inventory.canonical_json(record, newline=True)
                    for record in result["records"]
                ),
            )
            for offset, value in ((3, 8), (8, 0), (9, 3)):
                mutated = bytearray(first.read_bytes())
                mutated[offset] = value
                with self.assertRaises(inventory.ChildInventoryError):
                    inventory._decompress_canonical_gzip(
                        bytes(mutated),
                        self.authority["capture_policy"]["maximum_jsonl_uncompressed_bytes"],
                    )

    def test_capture_verify_rejects_rebound_nonzero_gzip_mtime(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-gzip-header-") as root:
            root_path = Path(root)
            authority, results = self.synthetic_authority_results(root)
            contract_bytes = inventory.canonical_json(authority, newline=True)
            binding = {
                "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
                "github_head_sha": "d" * 40,
                "github_repository": inventory.EXPECTED_REPOSITORY,
                "github_run_attempt": "3",
                "github_run_id": "987",
            }
            output = root_path / "capture"
            try:
                with mock.patch.object(
                    inventory, "validate_contract_schema", return_value=authority
                ):
                    summary = inventory.write_capture(
                        output, authority, contract_bytes, results, binding
                    )
                    stream_name = authority["containers"][0]["output_member"]
                    stream_path = output / stream_name
                    summary_path = output / "child-inventory-summary.json"
                    checksum_path = output / "SHA256SUMS"
                    for path in (stream_path, summary_path, checksum_path):
                        os.chmod(str(path), 0o600)
                    compressed = bytearray(stream_path.read_bytes())
                    compressed[4:8] = (123).to_bytes(4, byteorder="little")
                    stream_path.write_bytes(bytes(compressed))
                    summary["containers"][0]["stream"]["compressed_sha256"] = (
                        hashlib.sha256(bytes(compressed)).hexdigest()
                    )
                    summary["containers"][0]["stream"]["compressed_size"] = len(compressed)
                    summary_path.write_bytes(inventory.canonical_json(summary, newline=True))
                    checksum_bytes = b"".join(
                        (
                            inventory.file_record(output / name)["sha256"]
                            + "  "
                            + name
                            + "\n"
                        ).encode("ascii")
                        for name in sorted(
                            name
                            for name in authority["artifact_policy"]["output_members"]
                            if name != "SHA256SUMS"
                        )
                    )
                    checksum_path.write_bytes(checksum_bytes)
                    for path in (stream_path, summary_path, checksum_path):
                        os.chmod(str(path), 0o444)
                    with self.assertRaises(inventory.ChildInventoryError):
                        inventory.verify_capture(output, authority, contract_bytes)
            finally:
                restore_tree(output)

    def test_capture_verify_rejects_forged_header_level_one_gzip_body(self):
        with tempfile.TemporaryDirectory(prefix="rk001-child-gzip-body-") as root:
            root_path = Path(root)
            authority, results = self.synthetic_authority_results(root)
            container = results[0]["container"]
            regular = next(
                record
                for record in results[0]["records"]
                if record["entry_type"] == "regular"
            )
            expanded_records = []
            for index in range(512):
                record = copy.deepcopy(regular)
                record["path"] = "{0}/generated-{1:04d}.txt".format(
                    container["namespace"], index
                )
                expanded_records.append(record)
            results[0]["records"] = expanded_records
            results[0]["capture"] = inventory._derive_capture(
                container,
                expanded_records,
                sum(record["size"] for record in expanded_records),
            )
            contract_bytes = inventory.canonical_json(authority, newline=True)
            binding = {
                "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
                "github_head_sha": "e" * 40,
                "github_repository": inventory.EXPECTED_REPOSITORY,
                "github_run_attempt": "4",
                "github_run_id": "654",
            }
            output = root_path / "capture"
            try:
                with mock.patch.object(
                    inventory, "validate_contract_schema", return_value=authority
                ):
                    summary = inventory.write_capture(
                        output, authority, contract_bytes, results, binding
                    )
                    stream_name = authority["containers"][0]["output_member"]
                    stream_path = output / stream_name
                    summary_path = output / "child-inventory-summary.json"
                    checksum_path = output / "SHA256SUMS"
                    original_compressed = stream_path.read_bytes()
                    with gzip.GzipFile(
                        fileobj=io.BytesIO(original_compressed), mode="rb"
                    ) as source:
                        uncompressed = source.read()
                    target = io.BytesIO()
                    with gzip.GzipFile(
                        filename="",
                        mode="wb",
                        fileobj=target,
                        compresslevel=1,
                        mtime=0,
                    ) as compressed:
                        compressed.write(uncompressed)
                    forged = bytearray(target.getvalue())
                    self.assertEqual(forged[8], 4)
                    forged[8] = inventory.EXPECTED_GZIP_HEADER[8]
                    self.assertEqual(bytes(forged[:10]), inventory.EXPECTED_GZIP_HEADER)
                    self.assertNotEqual(bytes(forged), original_compressed)
                    self.assertEqual(
                        inventory._decompress_canonical_gzip(
                            bytes(forged),
                            authority["capture_policy"][
                                "maximum_jsonl_uncompressed_bytes"
                            ],
                        ),
                        uncompressed,
                    )
                    for path in (stream_path, summary_path, checksum_path):
                        os.chmod(str(path), 0o600)
                    stream_path.write_bytes(bytes(forged))
                    summary["containers"][0]["stream"]["compressed_sha256"] = (
                        hashlib.sha256(bytes(forged)).hexdigest()
                    )
                    summary["containers"][0]["stream"]["compressed_size"] = len(forged)
                    summary_path.write_bytes(inventory.canonical_json(summary, newline=True))
                    checksum_bytes = b"".join(
                        (
                            inventory.file_record(output / name)["sha256"]
                            + "  "
                            + name
                            + "\n"
                        ).encode("ascii")
                        for name in sorted(
                            name
                            for name in authority["artifact_policy"]["output_members"]
                            if name != "SHA256SUMS"
                        )
                    )
                    checksum_path.write_bytes(checksum_bytes)
                    for path in (stream_path, summary_path, checksum_path):
                        os.chmod(str(path), 0o444)
                    with self.assertRaises(inventory.ChildInventoryError):
                        inventory.verify_capture(output, authority, contract_bytes)
            finally:
                restore_tree(output)

    def test_json_duplicate_noncanonical_float_and_nonfinite_fail(self):
        for data in (
            b'{"a":1,"a":2}\n',
            b'{ "a":1}\n',
            b'{"a":1.5}\n',
            b'{"a":NaN}\n',
        ):
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.read_json_bytes(data, "hostile JSON", canonical=True)
        with self.assertRaises(inventory.ChildInventoryError):
            inventory.read_json_bytes(
                ('{"a":' + ('9' * 129) + '}\n').encode("ascii"),
                "oversized integer JSON",
                canonical=True,
            )

    def test_safe_relative_rejects_escape_absolute_backslash_and_empty(self):
        for value in (
            "",
            "../escape",
            "/absolute",
            "a/../b",
            "a\\b",
            "./a",
            "a\nb",
            "a\rb",
            "a\x1fb",
            "a\x7fb",
            "a\u0085b",
            "a\u202eb",
        ):
            with self.assertRaises(inventory.ChildInventoryError):
                inventory.safe_relative(value, "fixture")

    def test_path_set_length_framing_has_no_newline_serialization_collision(self):
        one_path = [{"path": "stablelists/a\nb"}]
        two_paths = [{"path": "stablelists/a"}, {"path": "b"}]
        self.assertNotEqual(
            inventory._path_set_sha256(one_path),
            inventory._path_set_sha256(two_paths),
        )
        self.assertEqual(
            self.authority["capture_policy"]["member_path_set_algorithm"],
            inventory.MEMBER_PATH_SET_ALGORITHM,
        )

    def test_workflow_semantics_reject_guard_bypass_comments_duplicates_and_order(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        inventory.validate_workflow_bytes(workflow.encode("utf-8"))
        guard = '[[ "$GITHUB_SHA" == "$EXPECTED_HEAD_SHA" ]]'
        workflow_guard = '[[ "$GITHUB_WORKFLOW_SHA" == "$EXPECTED_HEAD_SHA" ]]'
        indent = "          "
        mutations = [
            workflow.replace(indent + guard + "\n", "", 1),
            workflow.replace(indent + guard, indent + "# " + guard, 1),
            workflow.replace(
                indent + guard,
                indent + "printf '%s\\n' '" + guard + "'",
                1,
            ),
            workflow.replace(
                indent + guard,
                indent + "if false; then\n" + indent + guard + "\n" + indent + "fi",
                1,
            ),
            workflow.replace(
                "      - name: Reject mutable dispatch and runtime identity\n",
                "      - name: Reject mutable dispatch and runtime identity\n"
                "        if: ${{ false }}\n",
                1,
            ),
            workflow.replace(
                indent + guard + "\n" + indent + workflow_guard,
                indent + workflow_guard + "\n" + indent + guard,
                1,
            ),
        ]
        identity_start = workflow.index(
            "      - name: Reject mutable dispatch and runtime identity\n"
        )
        install_start = workflow.index(
            "      - name: Install bounded source and archive tools\n"
        )
        identity_block = workflow[identity_start:install_start]
        mutations.append(workflow[:install_start] + identity_block + workflow[install_start:])
        self.assertIn(guard, mutations[1])
        self.assertIn(guard, mutations[2])
        for mutated in mutations:
            with self.assertRaises(inventory.ChildInventoryError):
                inventory._validate_workflow_semantics(mutated)
        byte_mutation = workflow.replace("retention-days: 30", "retention-days: 31", 1)
        with self.assertRaises(inventory.ChildInventoryError):
            inventory.validate_workflow_bytes(byte_mutation.encode("utf-8"))

    def test_python_36_grammar_and_exact_new_file_scope(self):
        for path in (CHECKER, TESTS):
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
                feature_version=(3, 6),
            )
        self.assertEqual(
            ASSIGNED_FILES,
            {
                ".github/workflows/rk001-license-child-inventory-v2.yml",
                "host-kernel/rocky/evidence/rk001-license-child-inventory-contract-ef58-v2.json",
                "scripts/rocky_kernel_license_child_inventory_v2.py",
                "scripts/tests/test_rocky_kernel_license_child_inventory_v2.py",
            },
        )
        workflow_bytes = WORKFLOW.read_bytes()
        inventory.validate_workflow_bytes(workflow_bytes)
        self.assertEqual(
            self.authority["inputs"]["child_inventory_v2_workflow"],
            {
                "path": ".github/workflows/rk001-license-child-inventory-v2.yml",
                "sha256": hashlib.sha256(workflow_bytes).hexdigest(),
                "size": len(workflow_bytes),
            },
        )


if __name__ == "__main__":
    unittest.main()
