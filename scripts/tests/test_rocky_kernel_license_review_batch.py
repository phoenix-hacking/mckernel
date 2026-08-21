#!/usr/bin/env python3
"""Adversarial tests for bounded, non-crediting RK-001 review batch 0001."""

from __future__ import print_function

import ast
import copy
import hashlib
import io
import json
import os
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS))

import rocky_kernel_license_review_batch as batch


CONTRACT = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/"
    "rk001-license-review-batch-ef58-0001-contract-v1.json"
)
DEFAULT_ARTIFACT = Path(
    "/workspace/scratch/1962bd8160f6/ci-evidence/ef58860e/"
    "rk001-license-inventory-32192199002-1.zip"
)
ASSIGNED_FILES = (
    ".github/workflows/rk001-license-review-batch-v1.yml",
    "host-kernel/rocky/evidence/rk001-license-review-batch-ef58-0001-contract-v1.json",
    "scripts/rocky_kernel_license_review_batch.py",
    "scripts/tests/test_rocky_kernel_license_review_batch.py",
)


def leaf_paths(value, prefix=()):
    if isinstance(value, dict):
        for key in sorted(value):
            for path in leaf_paths(value[key], prefix + (key,)):
                yield path
    elif isinstance(value, list):
        for index, item in enumerate(value):
            for path in leaf_paths(item, prefix + (index,)):
                yield path
    else:
        yield prefix


def changed_leaf(value):
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "-retargeted"
    raise AssertionError("unexpected leaf type")


def replace_leaf(value, path, replacement):
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement


class LicenseReviewBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("MCKERNEL_RK001_LICENSE_ARTIFACT")
        candidates = []
        if configured:
            candidates.append(Path(configured))
        candidates.extend(
            [
                DEFAULT_ARTIFACT,
                Path("/tmp/rk001-license-inventory-32192199002-1.zip"),
            ]
        )
        cls.artifact = next((path for path in candidates if path.is_file()), None)
        cls.authority = batch.load_authority(REPO_ROOT)
        cls.module, cls.queue_authority = batch.load_queue_checker(
            REPO_ROOT, cls.authority
        )
        cls.decision_module, cls.decision_authority = cls.module._load_frozen_checker(
            REPO_ROOT, cls.queue_authority
        )
        cls.records = None
        cls.result = None
        cls.groups = None
        cls.units = None
        if cls.artifact is not None:
            cls.module, cls.records = batch.derive_queue(
                REPO_ROOT, cls.artifact, cls.authority
            )
            cls.result, cls.groups, cls.units = batch.select_batch(
                cls.module, cls.records
            )

    def require_artifact(self):
        if self.artifact is None:
            self.skipTest("exact ef58860e RK-001 inventory artifact is not materialized")

    def test_exactly_assigned_files_retain_python36_and_static_contract_scope(self):
        for relative in ASSIGNED_FILES:
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)
        for relative in ASSIGNED_FILES[2:]:
            source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=relative)
            self.assertIsNotNone(tree)
            for forbidden in (
                ".is_relative" + "_to(",
                ".remove" + "prefix(",
                ".remove" + "suffix(",
                "capture_" + "output=",
                "missing_" + "ok=",
            ):
                self.assertNotIn(forbidden, source)

    def test_contract_is_canonical_digest_locked_and_recursively_exact(self):
        data = CONTRACT.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), batch.AUTHORITY_SHA256)
        value = batch.read_json_bytes(data, "batch authority", canonical=True)
        self.assertEqual(batch.validate_authority(copy.deepcopy(value)), value)
        for path in leaf_paths(value):
            mutation = copy.deepcopy(value)
            target = mutation
            for key in path:
                target = target[key]
            replace_leaf(mutation, path, changed_leaf(target))
            with self.subTest(path=path):
                with self.assertRaises(batch.ReviewBatchError):
                    batch.validate_authority(mutation)
        extra = copy.deepcopy(value)
        extra["reviewer_signature"] = "placeholder"
        with self.assertRaises(batch.ReviewBatchError):
            batch.validate_authority(extra)

    def test_frozen_authority_chain_and_inventory_origin_are_exact(self):
        for key in (
            "queue_authority",
            "queue_checker",
            "decision_authority",
            "decision_checker",
            "source_lock",
            "workflow",
        ):
            record = self.authority["inputs"][key]
            active = batch.CURRENT_IMPLEMENTATION_OVERRIDES.get(
                record["path"], record
            )
            data = (REPO_ROOT / active["path"]).read_bytes()
            self.assertEqual(len(data), active["size"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), active["sha256"])
        self.assertEqual(
            self.authority["inputs"]["source_lock"],
            {
                "path": "host-kernel/rocky/source-lock.json",
                "sha256": "707ee40466ac0bb0cd0600383bba0b13fc1146e7080034786bf5668a95b27682",
                "size": 18236,
            },
        )
        self.assertNotEqual(
            batch.CURRENT_IMPLEMENTATION_OVERRIDES[
                self.authority["inputs"]["source_lock"]["path"]
            ]["sha256"],
            self.authority["inputs"]["source_lock"]["sha256"],
        )
        self.assertEqual(
            self.authority["inputs"]["inventory_artifact"],
            batch.INVENTORY_ARTIFACT,
        )
        self.assertEqual(
            self.authority["inputs"]["inventory_member"], batch.INVENTORY_MEMBER
        )
        self.assertEqual(batch.SOURCE_COMMIT, "ef58860e4806ee16e2c506e4e93c7b6ad8ad8f4b")

    def test_all_claims_gate_and_future_schema_remain_noncrediting(self):
        self.assertTrue(all(value is False for value in batch.EXPECTED_CLAIMS.values()))
        self.assertEqual(batch.EXPECTED_GATE["status"], "TODO")
        self.assertEqual(batch.EXPECTED_GATE["points_awarded"], 0)
        self.assertIs(batch.EXPECTED_GATE["tracker_credit"], False)
        future = self.authority["future_decision_schema"]
        self.assertIs(future["implemented_by_this_batch"], False)
        self.assertIs(future["group_auto_resolves_units"], False)
        self.assertIs(future["signed_response_root_required"], True)
        contract_text = CONTRACT.read_text(encoding="ascii")
        self.assertNotIn('"reviewer_identity":"', contract_text)
        self.assertNotIn('"signed_response_root":"', contract_text)

    def test_exact_selection_counts_order_boundary_and_streams(self):
        self.require_artifact()
        self.assertEqual(self.result, batch.EXPECTED_RESULT)
        self.assertEqual(len(self.groups), 512)
        self.assertEqual(len(self.units), 2096)
        self.assertEqual(
            [record["group_id"] for record in self.groups],
            sorted(record["group_id"] for record in self.groups),
        )
        self.assertEqual(
            [record["evidence"]["path"] for record in self.units],
            sorted(record["evidence"]["path"] for record in self.units),
        )
        group_stream = batch.stream_bytes(self.module, self.groups)
        unit_stream = batch.stream_bytes(self.module, self.units)
        self.assertEqual(len(group_stream), 184917)
        self.assertEqual(
            hashlib.sha256(group_stream).hexdigest(),
            "a1a5ed89800a35ca9fbbe59074628ef62e6f90f0a27da38078e2f96596146710",
        )
        self.assertEqual(len(unit_stream), 2555534)
        self.assertEqual(
            hashlib.sha256(unit_stream).hexdigest(),
            "c6c02b9da1dbda617ff057cbd8e2bb630ded1b35920c3ba2869b186f85cf19c2",
        )

    def test_selection_eligibility_reasons_and_tie_order_are_exact(self):
        self.require_artifact()
        units_by_group = {}
        for unit in self.records["review-units"]:
            units_by_group.setdefault(unit["exact_content_group_id"], []).append(unit)
        selected_ids = {record["group_id"] for record in self.groups}
        for group_id in selected_ids:
            units = units_by_group[group_id]
            self.assertGreaterEqual(len(units), 2)
            self.assertTrue(
                all(unit["basis"] == "missing-spdx-needs-review" for unit in units)
            )
            self.assertEqual(
                len({tuple(unit["evidence"]["unresolved_reasons"]) for unit in units}),
                1,
            )
        groups = {
            record["group_id"]: record
            for record in self.records["exact-content-groups"]
        }
        eligible = []
        for group_id, units in units_by_group.items():
            if group_id is None or groups[group_id]["path_count"] < 2:
                continue
            if all(unit["basis"] == "missing-spdx-needs-review" for unit in units) and len(
                {tuple(unit["evidence"]["unresolved_reasons"]) for unit in units}
            ) == 1:
                eligible.append(groups[group_id])
        eligible.sort(key=lambda record: (-record["path_count"], record["group_id"]))
        self.assertEqual(
            eligible[511]["group_id"], batch.EXPECTED_RESULT["boundary_group_id"]
        )
        self.assertEqual(
            selected_ids, {record["group_id"] for record in eligible[:512]}
        )
        for left, right in zip(eligible, eligible[1:]):
            if left["path_count"] == right["path_count"]:
                self.assertLess(left["group_id"], right["group_id"])

    def test_emitted_stream_reordering_is_not_an_equivalent_batch(self):
        self.require_artifact()
        reordered_groups = list(reversed(self.groups))
        reordered_units = list(reversed(self.units))
        group_stream = batch.stream_bytes(self.module, reordered_groups)
        unit_stream = batch.stream_bytes(self.module, reordered_units)
        self.assertNotEqual(
            hashlib.sha256(group_stream).hexdigest(),
            batch.EXPECTED_RESULT["content_group_stream_sha256"],
        )
        self.assertNotEqual(
            hashlib.sha256(unit_stream).hexdigest(),
            batch.EXPECTED_RESULT["review_unit_stream_sha256"],
        )
        with self.assertRaises(batch.ReviewBatchError):
            batch.require_exact(
                hashlib.sha256(group_stream).hexdigest(),
                batch.EXPECTED_RESULT["content_group_stream_sha256"],
                "reordered group stream",
            )

    def test_omission_duplication_retarget_and_reason_promotion_fail_closed(self):
        self.require_artifact()
        selected_id = self.groups[0]["group_id"]
        cases = []
        omitted = copy.deepcopy(self.records)
        omitted["exact-content-groups"] = [
            record
            for record in omitted["exact-content-groups"]
            if record["group_id"] != selected_id
        ]
        cases.append(("omission", omitted))
        duplicated = copy.deepcopy(self.records)
        duplicated["exact-content-groups"].append(
            copy.deepcopy(duplicated["exact-content-groups"][0])
        )
        cases.append(("duplicate", duplicated))
        retargeted = copy.deepcopy(self.records)
        selected_units = [
            unit
            for unit in retargeted["review-units"]
            if unit["exact_content_group_id"] == selected_id
        ]
        selected_units[0]["exact_content_group_id"] = self.groups[1]["group_id"]
        cases.append(("retarget", retargeted))
        promoted = copy.deepcopy(self.records)
        selected_units = [
            unit
            for unit in promoted["review-units"]
            if unit["exact_content_group_id"] == selected_id
        ]
        selected_units[0]["evidence"]["unresolved_reasons"].append(
            "reviewer-promoted-without-authority"
        )
        cases.append(("reason-promotion", promoted))
        for label, records in cases:
            with self.subTest(label=label):
                with self.assertRaises(batch.ReviewBatchError):
                    batch.select_batch(self.module, records)

    def test_path_context_and_candidate_mutations_fail_frozen_result(self):
        self.require_artifact()
        cases = []
        path_mutation = copy.deepcopy(self.records)
        target = next(
            unit
            for unit in path_mutation["review-units"]
            if unit["exact_content_group_id"] == self.groups[-1]["group_id"]
        )
        target["evidence"]["path"] += "-retargeted"
        cases.append(("path", path_mutation))
        context_mutation = copy.deepcopy(self.records)
        target = next(
            unit
            for unit in context_mutation["review-units"]
            if unit["exact_content_group_id"] == self.groups[-1]["group_id"]
        )
        target["context_group_id"] = self.units[0]["context_group_id"]
        cases.append(("context", context_mutation))
        candidate_mutation = copy.deepcopy(self.records)
        target = next(
            unit
            for unit in candidate_mutation["review-units"]
            if unit["exact_content_group_id"] == self.groups[-1]["group_id"]
            and unit["candidate_directory_signal_id"] is None
        )
        target["candidate_directory_signal_id"] = "candidate-directory:" + "0" * 64
        cases.append(("candidate", candidate_mutation))
        for label, records in cases:
            with self.subTest(label=label):
                with self.assertRaises(batch.ReviewBatchError):
                    batch.select_batch(self.module, records)

    def test_selected_units_do_not_leak_archive_or_spec_review_into_batch(self):
        self.require_artifact()
        archive_suffixes = (
            ".bz2",
            ".cpio",
            ".gz",
            ".rpm",
            ".src.rpm",
            ".tar",
            ".tar.bz2",
            ".tar.gz",
            ".tar.xz",
            ".tgz",
            ".xz",
            ".zip",
            ".spec",
        )
        for unit in self.units:
            self.assertFalse(unit["evidence"]["path"].lower().endswith(archive_suffixes))
            self.assertEqual(unit["decision"], "unresolved")
            self.assertEqual(unit["review_state"], "independent-review-required")

    def test_content_corruption_and_digest_filename_mismatch_fail_closed(self):
        data = b"bounded-review-content\n"
        digest = hashlib.sha256(data).hexdigest()
        group = {
            "group_id": "exact-content:test",
            "identity": {"entry_type": "regular", "sha256": digest, "size": len(data)},
            "path_count": 2,
            "path_set_sha256": "0" * 64,
            "review_state": "independent-review-required",
        }
        with mock.patch.object(batch, "GROUP_LIMIT", 1):
            self.assertEqual(
                batch.content_map([group], {group["group_id"]: data}), {digest: data}
            )
            with self.assertRaises(batch.ReviewBatchError):
                batch.content_map([group], {group["group_id"]: data + b"corrupt"})
            changed = copy.deepcopy(group)
            changed["identity"]["sha256"] = "0" * 64
            with self.assertRaises(batch.ReviewBatchError):
                batch.content_map([changed], {changed["group_id"]: data})

    def test_complete_synthetic_package_verifies_and_corruption_fails(self):
        data = b"synthetic bounded review content\n"
        digest = hashlib.sha256(data).hexdigest()
        identity = {"entry_type": "regular", "sha256": digest, "size": len(data)}
        group_id = self.module.stable_id("exact-content", identity)
        paths = ["linux/synthetic-a", "linux/synthetic-b"]
        group = {
            "group_id": group_id,
            "identity": identity,
            "path_count": len(paths),
            "path_set_sha256": self.module.path_set_sha256(paths),
            "review_state": "independent-review-required",
        }
        units = []
        for index, path in enumerate(paths):
            units.append(
                {
                    "basis": "missing-spdx-needs-review",
                    "candidate_directory_signal_id": None,
                    "context_group_id": "context:" + str(index),
                    "decision": "unresolved",
                    "evidence": {
                        "entry_type": "regular",
                        "namespace": "linux",
                        "path": path,
                        "sha256": digest,
                        "size": len(data),
                    },
                    "exact_content_group_id": group_id,
                    "review_state": "independent-review-required",
                }
            )
        group_stream = batch.stream_bytes(self.module, [group])
        unit_stream = batch.stream_bytes(self.module, units)
        result = {
            "boundary_group_id": group_id,
            "candidate_signal_unit_count": 0,
            "content_group_count": 1,
            "content_group_stream_bytes": len(group_stream),
            "content_group_stream_sha256": hashlib.sha256(group_stream).hexdigest(),
            "context_group_count": 2,
            "maximum_content_size": len(data),
            "namespace_review_unit_counts": {
                "dist-git": 0,
                "linux": 2,
                "repository": 0,
                "srpm": 0,
            },
            "review_unit_count": 2,
            "review_unit_stream_bytes": len(unit_stream),
            "review_unit_stream_sha256": hashlib.sha256(unit_stream).hexdigest(),
            "selected_path_set_sha256": self.module.path_set_sha256(paths),
            "unique_content_bytes": len(data),
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            batch, "GROUP_LIMIT", 1
        ), mock.patch.object(batch, "EXPECTED_RESULT", result):
            output = Path(temporary) / "package"
            files = batch.package_files(
                self.module,
                self.authority,
                result,
                [group],
                units,
                {group_id: data},
            )
            batch.publish_package(output, files)
            self.assertEqual(
                batch.verify_package(output, self.authority, self.module)["result"],
                result,
            )
            content_path = output / "content" / digest
            os.chmod(str(content_path), 0o644)
            content_path.write_bytes(data + b"corrupt")
            with self.assertRaises(batch.ReviewBatchError):
                batch.verify_package(output, self.authority, self.module)

    def test_symlink_traversal_and_resource_attacks_fail_closed(self):
        for value in ("../escape", "/absolute", "a//b", "a/./b", "a\\b"):
            with self.subTest(value=value):
                with self.assertRaises(batch.ReviewBatchError):
                    batch.safe_relative(value, "hostile path")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.write_bytes(b"x")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(batch.ReviewBatchError):
                batch.read_regular_file_once(link, "symlink", 10)
        with mock.patch.object(batch, "MAX_STREAM_BYTES", 8):
            with self.assertRaises(batch.ReviewBatchError):
                batch.parse_jsonl(b'{"value":1}\n', "oversize")

    def test_directory_package_aggregate_cap_preflights_before_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "package"
            root.mkdir()
            (root / "content").mkdir()
            for index in range(4):
                (root / ("member-{0}".format(index))).write_bytes(b"12345678")
            with mock.patch.object(batch, "MAX_PACKAGE_BYTES", 8), mock.patch.object(
                batch,
                "_read_open_regular_descriptor",
                wraps=batch._read_open_regular_descriptor,
            ) as reader:
                with self.assertRaisesRegex(
                    batch.ReviewBatchError, "aggregate size exceeds"
                ):
                    batch.read_package(root)
                self.assertEqual(reader.call_count, 0)

    def test_directory_package_runtime_cap_blocks_raced_member_before_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "package"
            root.mkdir()
            (root / "content").mkdir()
            paths = []
            for index in range(4):
                path = root / ("member-{0}".format(index))
                path.write_bytes(b"")
                paths.append(path)

            with mock.patch.object(batch, "MAX_PACKAGE_BYTES", 8), mock.patch.object(
                batch, "_read_open_regular_descriptor", return_value=b"12345678"
            ) as reader:
                with self.assertRaisesRegex(
                    batch.ReviewBatchError, "retention cap is exhausted before"
                ):
                    batch.read_package(root)
                self.assertEqual(reader.call_count, 1)
                self.assertEqual(reader.call_args_list[0][0][2], 8)

    def test_preflight_read_ancestor_symlink_swap_never_accepts_outside_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            landing = base / "landing"
            package = landing / "package"
            package.mkdir(parents=True)
            (package / "content").mkdir()
            (package / "member").write_bytes(b"ORIGINAL")
            outside = base / "outside"
            outside_package = outside / "package"
            outside_package.mkdir(parents=True)
            (outside_package / "content").mkdir()
            (outside_package / "member").write_bytes(b"EXTERNAL")
            held = base / "held-original"
            original_preflight = batch._package_preflight

            def swap_ancestor(catalog, authority=None, expected_result=None, group_limit=None):
                result = original_preflight(
                    catalog, authority, expected_result, group_limit
                )
                landing.rename(held)
                landing.symlink_to(outside, target_is_directory=True)
                return result

            with mock.patch.object(
                batch, "_package_preflight", side_effect=swap_ancestor
            ), mock.patch.object(
                batch,
                "_read_open_regular_descriptor",
                wraps=batch._read_open_regular_descriptor,
            ) as reader:
                with self.assertRaisesRegex(
                    batch.ReviewBatchError,
                    "directory component namespace changed",
                ):
                    batch.read_package(package)
                self.assertEqual(reader.call_count, 0)
            self.assertEqual((landing / "package" / "member").read_bytes(), b"EXTERNAL")
            self.assertEqual((held / "package" / "member").read_bytes(), b"ORIGINAL")

    def test_leaf_replacement_and_same_byte_inode_swap_fail_before_read(self):
        for label, replacement in (
            ("different-bytes", b"EXTERNAL"),
            ("same-bytes-new-inode", b"ORIGINAL"),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                package = base / "package"
                package.mkdir()
                (package / "content").mkdir()
                member = package / "member"
                member.write_bytes(b"ORIGINAL")
                held = base / "held-member"
                original_preflight = batch._package_preflight

                def swap_leaf(catalog, authority=None, expected_result=None, group_limit=None):
                    result = original_preflight(
                        catalog, authority, expected_result, group_limit
                    )
                    member.rename(held)
                    member.write_bytes(replacement)
                    return result

                with mock.patch.object(
                    batch, "_package_preflight", side_effect=swap_leaf
                ), mock.patch.object(
                    batch,
                    "_read_open_regular_descriptor",
                    wraps=batch._read_open_regular_descriptor,
                ) as reader:
                    with self.assertRaisesRegex(
                        batch.ReviewBatchError, "member namespace identity changed"
                    ):
                        batch.read_package(package)
                    self.assertEqual(reader.call_count, 0)

    def test_in_place_member_mutation_fails_before_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "package"
            package.mkdir()
            (package / "content").mkdir()
            member = package / "member"
            member.write_bytes(b"ORIGINAL")
            original_preflight = batch._package_preflight

            def mutate_member(catalog, authority=None, expected_result=None, group_limit=None):
                result = original_preflight(
                    catalog, authority, expected_result, group_limit
                )
                member.write_bytes(b"MUTATED!")
                os.chmod(str(member), 0o400)
                return result

            with mock.patch.object(
                batch, "_package_preflight", side_effect=mutate_member
            ), mock.patch.object(
                batch,
                "_read_open_regular_descriptor",
                wraps=batch._read_open_regular_descriptor,
            ) as reader:
                with self.assertRaisesRegex(
                    batch.ReviewBatchError, "member namespace identity changed"
                ):
                    batch.read_package(package)
                self.assertEqual(reader.call_count, 0)

    def test_linux_tar_logical_aggregate_cap_blocks_over_limit_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "aggregate.tar.xz"
            with tarfile.open(str(path), "w:xz") as archive:
                for index in range(4):
                    info = tarfile.TarInfo("safe/member-{0}".format(index))
                    info.size = 8
                    archive.addfile(info, io.BytesIO(b"12345678"))
            replacement = dict(batch.LINUX_ARCHIVE)
            replacement["size"] = path.stat().st_size
            replacement["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            replacement["top_directory"] = "safe"
            wanted = {
                "linux/member-1": {
                    "group_id": "exact-content:over-limit",
                    "sha256": hashlib.sha256(b"12345678").hexdigest(),
                    "size": 8,
                }
            }
            extracted = []
            original_extractfile = tarfile.TarFile.extractfile

            def observe_extractfile(archive, member):
                extracted.append(member.name)
                return original_extractfile(archive, member)

            with mock.patch.object(batch, "LINUX_ARCHIVE", replacement), mock.patch.object(
                batch, "MAX_TAR_LOGICAL_BYTES", 8
            ), mock.patch.object(
                tarfile.TarFile, "extractfile", new=observe_extractfile
            ):
                with self.assertRaisesRegex(
                    batch.ReviewBatchError, "logical size exceeds"
                ):
                    batch.read_linux_content(path, wanted)
            self.assertEqual(extracted, [])

    def test_zip_stream_content_and_directory_variants_have_aggregate_bounds(self):
        self.assertEqual(
            self.authority["package_policy"]["maximum_package_bytes"],
            batch.MAX_PACKAGE_BYTES,
        )
        self.assertIs(
            self.authority["package_policy"]["descriptor_rooted_reads"], True
        )
        self.assertEqual(
            self.authority["package_policy"]["namespace_replay"],
            "root-and-member-identities-before-during-and-after-retention",
        )
        self.assertLess(batch.MAX_PACKAGE_BYTES, batch.MAX_STREAM_BYTES)
        self.assertLess(batch.INVENTORY_ARTIFACT["size"], batch.MAX_ARTIFACT_BYTES)
        self.assertLessEqual(
            batch.EXPECTED_RESULT["unique_content_bytes"], batch.MAX_CONTENT_BYTES
        )
        decision_source = (
            REPO_ROOT / batch.DECISION_CHECKER["path"]
        ).read_text(encoding="utf-8")
        for token in (
            "MAX_ARTIFACT_BYTES",
            "MAX_INVENTORY_COMPRESSED_BYTES",
            "MAX_INVENTORY_BYTES",
            "info.file_size != record[\"size\"]",
            "expanded > MAX_INVENTORY_BYTES",
        ):
            self.assertIn(token, decision_source)
        with tempfile.TemporaryDirectory() as temporary:
            hostile = Path(temporary) / "hostile.zip"
            hostile.write_bytes(b"123456789")
            record = {
                "zip_sha256": hashlib.sha256(hostile.read_bytes()).hexdigest(),
                "zip_size": hostile.stat().st_size,
            }
            with mock.patch.object(
                self.decision_module, "MAX_ARTIFACT_BYTES", 8
            ), mock.patch.object(
                self.decision_module.os,
                "read",
                wraps=self.decision_module.os.read,
            ) as reader:
                with self.assertRaises(self.decision_module.DecisionError):
                    self.decision_module.read_artifact(hostile, record)
                self.assertEqual(reader.call_count, 0)

    def test_linux_tar_traversal_and_duplicate_members_fail_without_extraction(self):
        for case in ("traversal", "duplicate"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "source.tar.xz"
                with tarfile.open(str(path), "w:xz") as archive:
                    names = (
                        ["../escape"]
                        if case == "traversal"
                        else ["safe/member", "safe/member"]
                    )
                    for name in names:
                        info = tarfile.TarInfo(name)
                        info.size = 1
                        archive.addfile(info, io.BytesIO(b"x"))
                replacement = dict(batch.LINUX_ARCHIVE)
                replacement["size"] = path.stat().st_size
                replacement["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                replacement["top_directory"] = "safe"
                with mock.patch.object(batch, "LINUX_ARCHIVE", replacement):
                    with self.assertRaises(batch.ReviewBatchError):
                        batch.read_linux_content(path, {})

    def test_partial_publication_and_existing_target_fail_closed(self):
        files = {"batch-summary.json": b"{}\n", "content/" + "0" * 64: b"x"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "batch"
            original = batch._write_exclusive
            calls = {"count": 0}

            def fail_second(path, data, mode=0o444):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise batch.ReviewBatchError("injected partial write")
                return original(path, data, mode)

            with mock.patch.object(batch, "_write_exclusive", fail_second):
                with self.assertRaises(batch.ReviewBatchError):
                    batch.publish_package(output, files)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.iterdir()), [])
            complete = root / "complete"
            batch.publish_package(complete, files)
            packaged = batch.read_package(complete)
            self.assertEqual(
                set(packaged),
                {"SHA256SUMS", "batch-summary.json", "content/" + "0" * 64},
            )
            self.assertEqual(
                packaged["SHA256SUMS"], batch.checksum_manifest(files)
            )
            output.mkdir()
            with self.assertRaises(batch.ReviewBatchError):
                batch.publish_package(output, files)

    def test_workflow_is_dispatch_only_exact_head_and_never_claims_credit(self):
        text = (REPO_ROOT / ASSIGNED_FILES[0]).read_text(encoding="utf-8")
        for token in (
            "workflow_dispatch:",
            "test \"$GITHUB_WORKFLOW_SHA\" = \"$EXPECTED_HEAD_SHA\"",
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            "INVENTORY_RUN_ID: '32192199002'",
            batch.INVENTORY_ARTIFACT["sha256"],
            "--proto '=https'",
            "--build",
            "--verify-package",
            "compression-level: 0",
        ):
            self.assertIn(token, text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("\n  push:", text)
        self.assertNotIn("gate-ready", text)
        self.assertNotIn("reviewer_signature", text)
        self.assertNotIn("source-lock.json\n          ", text)


if __name__ == "__main__":
    unittest.main()
