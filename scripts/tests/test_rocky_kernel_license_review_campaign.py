#!/usr/bin/env python3
"""Adversarial tests for the full non-crediting RK-001 review campaign."""

from __future__ import print_function

import ast
import collections
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS))

import rocky_kernel_license_review_campaign as campaign


CONTRACT = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json"
)
DEFAULT_ARTIFACT = Path(
    "/workspace/scratch/1962bd8160f6/ci-evidence/ef58860e/"
    "rk001-license-inventory-32192199002-1.zip"
)
ASSIGNED_FILES = (
    ".github/workflows/rk001-license-review-campaign-v1.yml",
    "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json",
    "scripts/rocky_kernel_license_review_campaign.py",
    "scripts/tests/test_rocky_kernel_license_review_campaign.py",
)


def changed_leaf(value):
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        return value + "-retargeted"
    if value is None:
        return "retargeted"
    raise AssertionError("unsupported leaf type: {0!r}".format(type(value)))


def replace_leaf(value, path, replacement):
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement


def canonical_stream(records):
    return b"".join(campaign.canonical_json(record, newline=True) for record in records)


class LicenseReviewCampaignTests(unittest.TestCase):
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
        cls.authority = campaign.load_authority(REPO_ROOT)
        cls.batch, cls.batch_authority = campaign.load_batch_checker(
            REPO_ROOT, cls.authority
        )
        cls.derived = None
        if cls.artifact is not None:
            cls.derived = campaign.derive_campaign(
                REPO_ROOT, cls.artifact, cls.authority
            )

    def require_artifact(self):
        if self.derived is None:
            self.skipTest("exact ef58860e RK-001 inventory artifact is not materialized")

    def build_symlink_packet(self, parent, name="packet"):
        self.require_artifact()
        output = Path(parent) / name
        files = campaign.package_files(self.authority, self.derived, "0219", {})
        campaign.publish_package(self.batch, output, files)
        return output

    def test_exact_four_file_scope_and_python36_grammar(self):
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
        self.assertEqual(hashlib.sha256(data).hexdigest(), campaign.AUTHORITY_SHA256)
        value = campaign.read_json_bytes(data, "campaign authority", canonical=True)
        self.assertEqual(campaign.validate_authority(copy.deepcopy(value)), value)
        representative_paths = [
            (
                "archive_expansion_bindings",
                0,
                "child_inventory",
                "capture_namespace_closure",
                "source_manifest_sha256",
            ),
            ("archive_expansion_bindings", 0, "container", "unit_id"),
            ("campaign_id",),
            ("claims", "campaign_complete"),
            ("expected_result", "content_group_count"),
            ("future_response_schema", "implemented_by_this_campaign"),
            ("gate", "points_awarded"),
            ("inputs", "batch_checker", "sha256"),
            ("inputs", "source_lock_validator", "sha256"),
            ("package_policy", "maximum_package_bytes"),
            ("partition_policy", "group_limit"),
            ("remaining_blockers", 0),
            ("schema_version",),
        ]
        for path in representative_paths:
            mutation = copy.deepcopy(value)
            target = mutation
            for key in path:
                target = target[key]
            replace_leaf(mutation, path, changed_leaf(target))
            with self.subTest(path=path):
                with self.assertRaises(campaign.ReviewCampaignError):
                    campaign.validate_authority(mutation)
        for index in range(len(value["packets"])):
            mutation = copy.deepcopy(value)
            mutation["packets"][index]["path_set_sha256"] = "0" * 64
            with self.subTest(packet=index + 1):
                with self.assertRaises(campaign.ReviewCampaignError):
                    campaign.validate_authority(mutation)
        extra = copy.deepcopy(value)
        extra["reviewer_signature"] = "placeholder"
        with self.assertRaises(campaign.ReviewCampaignError):
            campaign.validate_authority(extra)

    def test_frozen_batch_queue_decision_workflow_and_source_chain_is_exact(self):
        for key, record in self.authority["inputs"].items():
            if "path" not in record:
                continue
            active = campaign.CURRENT_IMPLEMENTATION_OVERRIDES.get(
                record["path"], record
            )
            data = (REPO_ROOT / active["path"]).read_bytes()
            self.assertEqual(len(data), active["size"], key)
            self.assertEqual(
                hashlib.sha256(data).hexdigest(), active["sha256"], key
            )
        self.assertEqual(
            self.authority["inputs"]["source_lock"], campaign.SOURCE_LOCK
        )
        self.assertNotEqual(
            campaign.CURRENT_IMPLEMENTATION_OVERRIDES[
                campaign.SOURCE_LOCK["path"]
            ]["sha256"],
            campaign.SOURCE_LOCK["sha256"],
        )
        self.assertEqual(self.batch.AUTHORITY_SHA256, campaign.BATCH_AUTHORITY["sha256"])
        self.assertEqual(self.batch.BATCH_ID, campaign.BATCH_AUTHORITY["batch_id"])
        self.assertEqual(self.batch.SOURCE_COMMIT, campaign.SOURCE_COMMIT)
        self.assertEqual(
            self.authority["inputs"]["inventory_artifact"],
            campaign.INVENTORY_ARTIFACT,
        )
        self.assertEqual(
            self.authority["inputs"]["inventory_member"], campaign.INVENTORY_MEMBER
        )
        self.assertEqual(
            self.authority["inputs"]["source_lock_validator"],
            campaign.SOURCE_LOCK_VALIDATOR,
        )

    def test_authority_and_bound_input_hold_ancestor_namespace_during_swap(self):
        for target in ("authority", "bound-input"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                landing = base / "landing"
                landing.mkdir()
                outside = base / "outside"
                outside.mkdir()
                held = base / "held-landing"
                if target == "authority":
                    name = "authority.json"
                    data = CONTRACT.read_bytes()
                    record = None
                else:
                    name = "checker.py"
                    data = (REPO_ROOT / campaign.BATCH_CHECKER["path"]).read_bytes()
                    record = {
                        "path": "landing/" + name,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "size": len(data),
                    }
                (landing / name).write_bytes(data)
                (outside / name).write_bytes(data)
                original_pass = campaign._read_descriptor_pass
                calls = [0]

                def swap_ancestor(context, label, size_cap):
                    calls[0] += 1
                    if calls[0] == 1:
                        landing.rename(held)
                        landing.symlink_to(outside, target_is_directory=True)
                    return original_pass(context, label, size_cap)

                with mock.patch.object(
                    campaign, "_read_descriptor_pass", side_effect=swap_ancestor
                ):
                    with self.assertRaisesRegex(
                        campaign.ReviewCampaignError, "directory namespace changed"
                    ):
                        if target == "authority":
                            campaign.load_authority(REPO_ROOT, landing / name)
                        else:
                            campaign._read_bound(base, record, "hostile frozen input")
                self.assertEqual((landing / name).read_bytes(), data)
                self.assertEqual((held / name).read_bytes(), data)

    def test_over_one_megabyte_same_inode_splice_fails_double_byte_replay(self):
        data = b"A" * (2 * 1024 * 1024 + 17)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "large-input"
            path.write_bytes(data)
            before = path.stat()
            real_read = campaign.os.read
            calls = [0]

            def splice_one_chunk(descriptor, size):
                value = real_read(descriptor, size)
                calls[0] += 1
                if calls[0] == 2 and value:
                    value = b"B" + value[1:]
                return value

            with mock.patch.object(campaign.os, "read", side_effect=splice_one_chunk):
                with self.assertRaisesRegex(
                    campaign.ReviewCampaignError, "byte replay differs"
                ):
                    campaign.read_regular_file_once(
                        path, "same-inode spliced input", len(data)
                    )
            after = path.stat()
            self.assertEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
            self.assertEqual(path.read_bytes(), data)
            self.assertGreaterEqual(calls[0], 8)

    def test_all_claims_gate_and_future_response_remain_noncrediting(self):
        self.assertTrue(all(value is False for value in campaign.EXPECTED_CLAIMS.values()))
        self.assertEqual(campaign.EXPECTED_GATE["status"], "TODO")
        self.assertEqual(campaign.EXPECTED_GATE["points_awarded"], 0)
        self.assertIs(campaign.EXPECTED_GATE["tracker_credit"], False)
        future = self.authority["future_response_schema"]
        self.assertIs(future["implemented_by_this_campaign"], False)
        self.assertIs(future["machine_classification_auto_accepted"], False)
        self.assertIs(future["content_finding_auto_resolves_paths"], False)
        self.assertIs(future["signed_response_root_required"], True)
        self.assertIs(future["archive_expansion_response_required"], True)
        self.assertIs(future["unexpanded_container_attachment_can_close"], False)
        contract_text = CONTRACT.read_text(encoding="ascii")
        self.assertNotIn('"reviewer_identity":"', contract_text)
        self.assertNotIn('"signed_response_root":"', contract_text)

    def test_exact_full_stream_counts_hashes_and_decision_separation(self):
        self.require_artifact()
        result = self.derived["result"]
        self.assertEqual(result, campaign.EXPECTED_RESULT)
        groups = self.derived["groups"]
        units = self.derived["units"]
        self.assertEqual(len(groups), 111004)
        self.assertEqual(len(units), 115265)
        group_stream = canonical_stream(groups)
        unit_stream = canonical_stream(units)
        self.assertEqual(len(group_stream), 44961974)
        self.assertEqual(
            hashlib.sha256(group_stream).hexdigest(),
            "35f981e50085d19a45d459aa9684f2b95eaad987781eea59bed8e3e5e356e31c",
        )
        self.assertEqual(len(unit_stream), 143777216)
        self.assertEqual(
            hashlib.sha256(unit_stream).hexdigest(),
            "33ce34f36cd7f75b63d5ee0f54dde9dde6ee18292b39b580fde1722582a0acd9",
        )
        units_by_group = collections.defaultdict(list)
        for unit in units:
            units_by_group[unit["exact_content_group_id"]].append(unit)
            self.assertEqual(unit["review_state"], campaign.REVIEW_STATE)
        for group in groups:
            decisions = {
                unit["decision"] for unit in units_by_group[group["group_id"]]
            }
            self.assertEqual(decisions, {group["decision_class"]})
        self.assertEqual(
            collections.Counter(unit["decision"] for unit in units),
            {campaign.MACHINE: 72616, campaign.UNRESOLVED: 42649},
        )

    def test_all_unresolved_units_are_exact_frozen_queue_records(self):
        self.require_artifact()
        frozen = {
            unit["evidence"]["path"]: unit
            for unit in self.derived["queue_records"]["review-units"]
        }
        actual = {
            unit["evidence"]["path"]: unit
            for unit in self.derived["units"]
            if unit["decision"] == campaign.UNRESOLVED
        }
        self.assertEqual(len(frozen), 42649)
        self.assertEqual(actual, frozen)
        for unit in self.derived["units"]:
            if unit["decision"] == campaign.MACHINE:
                self.assertIsNone(unit["candidate_directory_signal_id"])
                self.assertEqual(unit["review_state"], campaign.REVIEW_STATE)

    def test_exact_219_packet_closure_order_boundaries_and_caps(self):
        self.require_artifact()
        packets = self.derived["packets"]
        self.assertEqual(packets, self.authority["packets"])
        manifest = canonical_stream(packets)
        self.assertEqual(len(manifest), 156033)
        self.assertEqual(
            hashlib.sha256(manifest).hexdigest(),
            "b4bf0e5c97d46f1443a70402fe39e624cd0ceab7d710170c425ea7eb940a1c06",
        )
        self.assertEqual([packet["packet_id"] for packet in packets], [
            "{0:04d}".format(index) for index in range(1, 220)
        ])
        ordinary = packets[1:217]
        self.assertEqual(len(ordinary), 216)
        self.assertTrue(all(packet["group_count"] <= 512 for packet in ordinary))
        self.assertTrue(all(packet["unit_count"] <= 2500 for packet in ordinary))
        self.assertTrue(
            all(packet["content_bytes"] <= 60 * 1024 * 1024 for packet in ordinary)
        )
        self.assertEqual(max(packet["unit_count"] for packet in ordinary), 602)
        self.assertEqual(max(packet["content_bytes"] for packet in ordinary), 33893367)
        all_group_ids = []
        all_unit_ids = []
        for packet in packets:
            all_group_ids.extend(
                group["group_id"]
                for group in self.derived["packet_groups"][packet["packet_id"]]
            )
            all_unit_ids.extend(
                unit["unit_id"]
                for unit in self.derived["packet_units"][packet["packet_id"]]
            )
        self.assertEqual(len(all_group_ids), len(set(all_group_ids)))
        self.assertEqual(len(all_unit_ids), len(set(all_unit_ids)))
        self.assertEqual(set(all_group_ids), {
            group["group_id"] for group in self.derived["groups"]
        })
        self.assertEqual(set(all_unit_ids), {
            unit["unit_id"] for unit in self.derived["units"]
        })

    def test_packet_0001_preserves_committed_streams_and_path_set_exactly(self):
        self.require_artifact()
        groups = self.derived["packet_groups"]["0001"]
        units = self.derived["packet_units"]["0001"]
        group_stream = canonical_stream(groups)
        unit_stream = canonical_stream(units)
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
        self.assertEqual(
            self.derived["packets"][0]["path_set_sha256"],
            "8b13ad470f0e56acc6c7cf6e01bc47aebfc4eb1ed8c45b8b9b6df8d39b96e7cd",
        )
        self.assertTrue(all("decision_class" not in group for group in groups))

    def test_package_and_symlink_lanes_never_promote_raw_content_or_links(self):
        self.require_artifact()
        special = self.derived["packets"][217]
        symlinks = self.derived["packets"][218]
        self.assertEqual(special["packet_id"], "0218")
        self.assertEqual(special["group_count"], 12)
        self.assertEqual(special["unit_count"], 31)
        self.assertEqual(special["content_bytes"], 155257655)
        self.assertEqual(special["materialized_content_bytes"], 1863799)
        self.assertEqual(special["metadata_only_content_bytes"], 153393856)
        expansion = campaign.expansion_records(self.derived, "0218")
        self.assertEqual(
            [record["container"]["group_id"] for record in expansion],
            campaign.SPECIAL_ARCHIVE_GROUP_IDS,
        )
        self.assertEqual(
            [record["role"] for record in expansion],
            [
                "existing-inventory-closure",
                "future-v2-child-inventory-required",
                "future-v2-child-inventory-required",
            ],
        )
        linux_children = expansion[0]["child_inventory"]
        self.assertEqual(
            linux_children["capture_namespace_closure"],
            {
                "complete": True,
                "item_count": 115027,
                "path_set_algorithm": "utf8-path-newline",
                "path_set_sha256": "f7495feae099d970ef02bbb1a73a0669b88c83c33dad80d3cc6bfb4184b2b0c2",
                "source_closure_path_set_sha256": "f7495feae099d970ef02bbb1a73a0669b88c83c33dad80d3cc6bfb4184b2b0c2",
                "source_manifest_algorithm": "canonical-json-source-rows",
                "source_manifest_sha256": "321b8a227f7a9473a94db6fbf747c48727a39b20bd8a24474f68578915ca4e56",
            },
        )
        derived_children = linux_children["derived_review_closure"]
        self.assertEqual(derived_children["namespace"], "linux")
        self.assertEqual(
            derived_children["path_set_algorithm"], "canonical-json-path-rows"
        )
        self.assertEqual(
            derived_children["content_group_id_stream_algorithm"],
            "canonical-json-group-id-rows",
        )
        self.assertEqual(
            derived_children["review_unit_id_stream_algorithm"],
            "canonical-json-unit-id-rows",
        )
        self.assertEqual(derived_children["review_unit_count"], 115027)
        self.assertEqual(derived_children["content_group_count"], 110910)
        self.assertEqual(
            derived_children["review_unit_id_stream_sha256"],
            "f24cc1417f7cf1f343bdb9802565398c3d4269263f738b4fff70784930b79180",
        )
        self.assertEqual(
            derived_children["content_group_id_stream_sha256"],
            "fde9cf1678f54eadf2bf1bce93a752edcd7a10b5b5ff834568235b4a61b1948b",
        )
        self.assertIsNone(expansion[1]["child_inventory"])
        self.assertIsNone(expansion[2]["child_inventory"])
        self.assertTrue(
            all(
                record["attachment_alone_counts_as_reviewed"] is False
                and record["attachment_alone_credit_eligible"] is False
                and record["child_review_complete"] is False
                and record["container_review_state"] == campaign.REVIEW_STATE
                for record in expansion
            )
        )
        self.assertEqual(symlinks["packet_id"], "0219")
        self.assertEqual(symlinks["group_count"], 0)
        self.assertEqual(symlinks["unit_count"], 83)
        self.assertEqual(symlinks["content_bytes"], 0)
        self.assertTrue(
            all(
                unit["evidence"]["entry_type"] == "symlink"
                and unit["exact_content_group_id"] is None
                for unit in self.derived["packet_units"]["0219"]
            )
        )

    def test_omission_duplication_reorder_boundary_and_cap_mutations_fail(self):
        packets = self.authority["packets"]
        cases = []
        omitted = copy.deepcopy(packets)
        del omitted[10]
        cases.append(("omission", omitted))
        duplicated = copy.deepcopy(packets)
        duplicated[10] = copy.deepcopy(duplicated[9])
        duplicated[10]["packet_id"] = "0011"
        cases.append(("duplication", duplicated))
        reordered = copy.deepcopy(packets)
        reordered[9], reordered[10] = reordered[10], reordered[9]
        cases.append(("reorder", reordered))
        boundary = copy.deepcopy(packets)
        boundary[2]["first_group_id"] = boundary[1]["last_group_id"]
        cases.append(("boundary", boundary))
        cap = copy.deepcopy(packets)
        cap[2]["unit_count"] = 2501
        cases.append(("unit-cap", cap))
        raw_promotion = copy.deepcopy(packets)
        raw_promotion[217]["materialized_content_bytes"] += raw_promotion[217][
            "metadata_only_content_bytes"
        ]
        raw_promotion[217]["metadata_only_content_bytes"] = 0
        cases.append(("archive-promotion", raw_promotion))
        for label, mutation in cases:
            with self.subTest(label=label):
                with self.assertRaises(campaign.ReviewCampaignError):
                    campaign.validate_packet_manifest(mutation)

    def test_path_context_origin_decision_candidate_and_group_retargets_change_authority(self):
        self.require_artifact()
        original = self.derived["units"][0]
        cases = []
        for label, mutate in (
            ("path", lambda unit: unit["evidence"].__setitem__("path", unit["evidence"]["path"] + "-retargeted")),
            ("context", lambda unit: unit.__setitem__("context_group_id", "context:" + "0" * 64)),
            ("origin", lambda unit: unit["evidence"].__setitem__("origin", "retargeted-origin")),
            ("source", lambda unit: unit["evidence"]["source_identity"].__setitem__(next(iter(unit["evidence"]["source_identity"])), "0" * len(unit["evidence"]["source_identity"][next(iter(unit["evidence"]["source_identity"]))]))),
            ("group", lambda unit: unit.__setitem__("exact_content_group_id", self.derived["groups"][1]["group_id"])),
            ("candidate", lambda unit: unit.__setitem__("candidate_directory_signal_id", "candidate-directory:" + "0" * 64)),
            ("decision", lambda unit: unit.__setitem__("decision", campaign.UNRESOLVED if unit["decision"] == campaign.MACHINE else campaign.MACHINE)),
        ):
            mutation = copy.deepcopy(original)
            mutate(mutation)
            payload = dict(mutation)
            del payload["unit_id"]
            mutation["unit_id"] = self.derived["module"].stable_id("review-unit", payload)
            cases.append((label, mutation))
        for label, mutation in cases:
            with self.subTest(label=label):
                self.assertNotEqual(mutation["unit_id"], original["unit_id"])
                self.assertNotEqual(
                    campaign.canonical_json(mutation), campaign.canonical_json(original)
                )
        changed = list(self.derived["units"])
        changed[0] = cases[0][1]
        digest = hashlib.sha256(canonical_stream(changed)).hexdigest()
        with self.assertRaises(campaign.ReviewCampaignError):
            campaign.require_exact(
                digest,
                campaign.EXPECTED_RESULT["review_unit_stream_sha256"],
                "coherently retargeted unit stream",
            )

    def test_machine_decision_and_group_promotion_changes_both_frozen_streams(self):
        self.require_artifact()
        index = next(
            index
            for index, group in enumerate(self.derived["groups"])
            if group["decision_class"] == campaign.MACHINE
        )
        groups = list(self.derived["groups"])
        mutation = copy.deepcopy(groups[index])
        mutation["decision_class"] = campaign.UNRESOLVED
        groups[index] = mutation
        changed_digest = hashlib.sha256(canonical_stream(groups)).hexdigest()
        self.assertNotEqual(
            changed_digest, campaign.EXPECTED_RESULT["content_group_stream_sha256"]
        )
        self.assertIs(campaign.EXPECTED_CLAIMS["machine_classification_is_legal_review"], False)
        self.assertIs(
            campaign.EXPECTED_FUTURE_RESPONSE_SCHEMA["machine_classification_auto_accepted"],
            False,
        )

    def test_complete_symlink_packet_verifies_and_content_corruption_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = self.build_symlink_packet(temporary)
            summary = campaign.verify_package(
                self.authority, self.derived, "0219", output
            )
            self.assertEqual(summary["packet"]["packet_id"], "0219")
            member = output / "review-units.jsonl"
            os.chmod(str(member), 0o644)
            data = member.read_bytes()
            member.write_bytes(b"X" + data[1:])
            os.chmod(str(member), 0o444)
            with self.assertRaises(campaign.ReviewCampaignError):
                campaign.verify_package(self.authority, self.derived, "0219", output)

    def test_symlink_fifo_writable_mode_and_hardlink_package_members_fail_closed(self):
        cases = ("symlink", "fifo", "mode", "hardlink")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                output = self.build_symlink_packet(temporary)
                member = output / "packet-summary.json"
                os.chmod(str(output), 0o755)
                if case == "mode":
                    os.chmod(str(member), 0o644)
                else:
                    data = member.read_bytes()
                    member.unlink()
                    if case == "symlink":
                        outside = Path(temporary) / "outside"
                        outside.write_bytes(data)
                        member.symlink_to(outside)
                    elif case == "fifo":
                        os.mkfifo(str(member), 0o444)
                    else:
                        outside = Path(temporary) / "outside"
                        outside.write_bytes(data)
                        os.chmod(str(outside), 0o444)
                        os.link(str(outside), str(member))
                with self.assertRaises(campaign.ReviewCampaignError):
                    campaign.verify_package(
                        self.authority, self.derived, "0219", output
                    )

    def test_package_aggregate_cap_preflights_before_retaining_any_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = self.build_symlink_packet(temporary)
            packet = self.derived["packets"][218]
            metadata = campaign.packet_metadata_files(
                self.authority, self.derived, "0219"
            )
            with mock.patch.object(campaign, "MAX_PACKAGE_BYTES", 1), mock.patch.object(
                self.batch,
                "_read_open_regular_descriptor",
                wraps=self.batch._read_open_regular_descriptor,
            ) as reader:
                with self.assertRaisesRegex(
                    campaign.ReviewCampaignError, "aggregate size exceeds"
                ):
                    campaign.read_packet_package(
                        self.batch, output, metadata, {}, packet
                    )
                self.assertEqual(reader.call_count, 0)

    def test_ancestor_leaf_and_in_place_toctou_never_retain_raced_bytes(self):
        for case in ("ancestor", "leaf", "same-byte-inode", "in-place"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                landing = base / "landing"
                landing.mkdir()
                output = self.build_symlink_packet(landing)
                held = base / "held"
                outside = base / "outside"
                outside.mkdir()
                outside_packet = self.build_symlink_packet(outside)
                member = output / "packet-summary.json"
                held_member = base / "held-member"
                original_preflight = campaign._package_preflight

                def race(catalog, metadata, content, packet):
                    result = original_preflight(catalog, metadata, content, packet)
                    if case == "ancestor":
                        landing.rename(held)
                        landing.symlink_to(outside, target_is_directory=True)
                    elif case in ("leaf", "same-byte-inode"):
                        os.chmod(str(output), 0o755)
                        data = member.read_bytes()
                        member.rename(held_member)
                        member.write_bytes(
                            data if case == "same-byte-inode" else b"X" + data[1:]
                        )
                        os.chmod(str(member), 0o444)
                    else:
                        os.chmod(str(member), 0o644)
                        data = member.read_bytes()
                        member.write_bytes(b"X" + data[1:])
                        os.chmod(str(member), 0o444)
                    return result

                with mock.patch.object(
                    campaign, "_package_preflight", side_effect=race
                ), mock.patch.object(
                    self.batch,
                    "_read_open_regular_descriptor",
                    wraps=self.batch._read_open_regular_descriptor,
                ) as reader:
                    with self.assertRaises(campaign.ReviewCampaignError):
                        campaign.verify_package(
                            self.authority, self.derived, "0219", output
                        )
                    self.assertEqual(reader.call_count, 0)
                self.assertTrue(outside_packet.is_dir())

    def test_tar_zip_and_gzip_compressed_expanded_and_member_caps_fail_closed(self):
        self.require_artifact()
        decision = self.derived["decision"]
        compressed = gzip.compress(b"123456789\n")
        with mock.patch.object(decision, "MAX_INVENTORY_BYTES", 8):
            with self.assertRaises(decision.DecisionError):
                list(decision.bounded_gzip_lines(compressed))
        with mock.patch.object(decision, "MAX_LINE_BYTES", 4):
            with self.assertRaises(decision.DecisionError):
                list(decision.bounded_gzip_lines(gzip.compress(b"12345\n")))
        with tempfile.TemporaryDirectory() as temporary:
            hostile = Path(temporary) / "hostile.zip"
            hostile.write_bytes(b"123456789")
            record = {
                "zip_sha256": hashlib.sha256(hostile.read_bytes()).hexdigest(),
                "zip_size": hostile.stat().st_size,
            }
            with mock.patch.object(decision, "MAX_ARTIFACT_BYTES", 8), mock.patch.object(
                decision.os, "read", wraps=decision.os.read
            ) as reader:
                with self.assertRaises(decision.DecisionError):
                    decision.read_artifact(hostile, record)
                self.assertEqual(reader.call_count, 0)
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "aggregate.tar.xz"
            with tarfile.open(str(archive_path), "w:xz") as archive:
                for index in range(4):
                    info = tarfile.TarInfo("safe/member-{0}".format(index))
                    info.size = 8
                    archive.addfile(info, io.BytesIO(b"12345678"))
            replacement = dict(self.batch.LINUX_ARCHIVE)
            replacement["size"] = archive_path.stat().st_size
            replacement["sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
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

            with mock.patch.object(
                self.batch, "LINUX_ARCHIVE", replacement
            ), mock.patch.object(
                self.batch, "MAX_TAR_LOGICAL_BYTES", 8
            ), mock.patch.object(
                tarfile.TarFile, "extractfile", new=observe_extractfile
            ):
                with self.assertRaises(self.batch.ReviewBatchError):
                    self.batch.read_linux_content(archive_path, wanted)
            self.assertEqual(extracted, [])

    def test_materialization_rejects_corruption_and_digest_filename_drift(self):
        data = b"bounded campaign content\n"
        digest = hashlib.sha256(data).hexdigest()
        group = {
            "decision_class": campaign.MACHINE,
            "group_id": "exact-content:test",
            "identity": {"entry_type": "regular", "sha256": digest, "size": len(data)},
            "path_count": 1,
            "path_set_sha256": "0" * 64,
            "review_state": campaign.REVIEW_STATE,
        }
        derived = {
            "archive_group_ids": set(),
            "packet_groups": {"0002": [group]},
            "packet_units": {"0002": []},
            "packets": [None, {
                "materialized_content_bytes": len(data)
            }],
        }
        authority = self.authority
        with mock.patch.object(
            campaign, "packet_metadata_files", return_value={
                "content-groups.jsonl": b"",
                "expansion-required.jsonl": b"",
                "packet-summary.json": b"{}\n",
                "review-units.jsonl": b"",
            }
        ):
            files = campaign.package_files(
                authority, derived, "0002", {group["group_id"]: data}
            )
            self.assertEqual(files["content/" + digest], data)
            with self.assertRaises(campaign.ReviewCampaignError):
                campaign.package_files(
                    authority, derived, "0002", {group["group_id"]: data + b"x"}
                )

    def test_candidate_worktree_mutations_fail_clean_replay_without_changing_private_bytes(self):
        authority_paths = (
            ".github/workflows/rk001-license-review-campaign-v1.yml",
            "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json",
            "scripts/rocky_kernel_license_review_campaign.py",
            "scripts/rocky_kernel_source_lock.py",
        )

        def git(repo, *arguments):
            return subprocess.run(
                ["git", "-c", "core.filemode=true"] + list(arguments),
                cwd=str(repo),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        def require_git(repo, *arguments):
            result = git(repo, *arguments)
            self.assertEqual(
                result.returncode,
                0,
                result.stderr.decode("utf-8", "replace"),
            )
            return result.stdout

        def candidate_is_clean(repo, expected_head):
            head = git(repo, "rev-parse", "--verify", "HEAD^{commit}")
            if head.returncode or head.stdout.decode("ascii").strip() != expected_head:
                return False
            if git(repo, "diff-files", "--quiet", "--").returncode:
                return False
            if git(
                repo,
                "diff-index",
                "--cached",
                "--quiet",
                expected_head,
                "--",
            ).returncode:
                return False
            others = git(repo, "ls-files", "--others", "--")
            if others.returncode or others.stdout != b"":
                return False
            for relative in authority_paths:
                expected = git(
                    repo,
                    "rev-parse",
                    expected_head + ":" + relative,
                )
                actual = git(
                    repo,
                    "hash-object",
                    "--no-filters",
                    "--",
                    str(repo / relative),
                )
                if (
                    expected.returncode
                    or actual.returncode
                    or actual.stdout != expected.stdout
                ):
                    return False
            return True

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            candidate = base / "candidate"
            private = base / "private"
            candidate.mkdir()
            private.mkdir()
            require_git(candidate, "init", "--quiet")
            require_git(candidate, "config", "user.email", "campaign@example.invalid")
            require_git(candidate, "config", "user.name", "Campaign Test")
            originals = {}
            for relative in authority_paths:
                data = ("committed authority: " + relative + "\n").encode("utf-8")
                originals[relative] = data
                path = candidate / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            require_git(candidate, "add", "--", ".")
            require_git(candidate, "commit", "--quiet", "-m", "authority")
            expected_head = require_git(
                candidate, "rev-parse", "HEAD^{commit}"
            ).decode("ascii").strip()
            for relative in authority_paths:
                private_path = private / relative
                private_path.parent.mkdir(parents=True, exist_ok=True)
                private_path.write_bytes(
                    require_git(candidate, "show", expected_head + ":" + relative)
                )
            self.assertTrue(candidate_is_clean(candidate, expected_head))
            for relative in authority_paths:
                path = candidate / relative
                path.write_bytes(originals[relative] + b"candidate mutation\n")
                with self.subTest(kind="worktree", path=relative):
                    self.assertFalse(candidate_is_clean(candidate, expected_head))
                    self.assertEqual((private / relative).read_bytes(), originals[relative])
                path.write_bytes(originals[relative])
                # Start the next mutation from a fresh-checkout-equivalent index
                # state instead of Git's filesystem-dependent racy-clean cache.
                require_git(
                    candidate, "update-index", "--really-refresh", "--", relative
                )
                self.assertTrue(candidate_is_clean(candidate, expected_head))
            splice_target = candidate / authority_paths[1]
            before = splice_target.stat()
            same_size = bytearray(originals[authority_paths[1]])
            same_size[0] ^= 1
            splice_target.write_bytes(bytes(same_size))
            os.utime(
                str(splice_target),
                ns=(before.st_atime_ns, before.st_mtime_ns),
            )
            self.assertFalse(candidate_is_clean(candidate, expected_head))
            self.assertEqual(
                (private / authority_paths[1]).read_bytes(),
                originals[authority_paths[1]],
            )
            splice_target.write_bytes(originals[authority_paths[1]])
            require_git(
                candidate,
                "update-index",
                "--really-refresh",
                "--",
                authority_paths[1],
            )
            self.assertTrue(candidate_is_clean(candidate, expected_head))
            mode_target = candidate / authority_paths[2]
            mode_target.chmod(0o755)
            self.assertFalse(candidate_is_clean(candidate, expected_head))
            mode_target.chmod(0o644)
            require_git(
                candidate,
                "update-index",
                "--really-refresh",
                "--",
                authority_paths[2],
            )
            self.assertTrue(candidate_is_clean(candidate, expected_head))
            indexed = authority_paths[2]
            (candidate / indexed).write_bytes(originals[indexed] + b"index mutation\n")
            require_git(candidate, "add", "--", indexed)
            self.assertFalse(candidate_is_clean(candidate, expected_head))
            (candidate / indexed).write_bytes(originals[indexed])
            require_git(candidate, "add", "--", indexed)
            self.assertTrue(candidate_is_clean(candidate, expected_head))
            untracked = candidate / "scripts/candidate-substitute.py"
            untracked.write_bytes(b"substitute\n")
            self.assertFalse(candidate_is_clean(candidate, expected_head))
            untracked.unlink()
            self.assertTrue(candidate_is_clean(candidate, expected_head))

    def test_workflow_is_dispatch_only_exact_head_packet_bounded_and_noncrediting(self):
        workflow_path = REPO_ROOT / campaign.CAMPAIGN_WORKFLOW["path"]
        data = workflow_path.read_bytes()
        self.assertEqual(len(data), campaign.CAMPAIGN_WORKFLOW["size"])
        self.assertEqual(
            hashlib.sha256(data).hexdigest(), campaign.CAMPAIGN_WORKFLOW["sha256"]
        )
        text = data.decode("utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("\n  push:", text)
        self.assertNotIn("\n  pull_request:", text)
        self.assertNotIn("\n  schedule:", text)
        self.assertIn("test \"$GITHUB_SHA\" = \"$EXPECTED_HEAD_SHA\"", text)
        self.assertIn("test \"$GITHUB_WORKFLOW_SHA\" = \"$EXPECTED_HEAD_SHA\"", text)
        self.assertIn('archive \\\n            --format=tar "$EXPECTED_HEAD_SHA"', text)
        self.assertIn("scripts/rocky_kernel_source_lock.py", text)
        self.assertIn('"$AUTHORITY_ROOT/scripts/rocky_kernel_source_lock.py"', text)
        self.assertIn('--repo "$AUTHORITY_ROOT"', text)
        self.assertIn('--authority "$private_authority"', text)
        self.assertIn("find \"$AUTHORITY_ROOT\" -type f -exec chmod a-w", text)
        self.assertEqual(text.count("--quiet --no-ext-diff --"), 3)
        self.assertEqual(text.count("diff-index \\\n"), 3)
        self.assertEqual(text.count("ls-files --others --"), 3)
        self.assertEqual(
            text.count('candidate_blob="$(/usr/bin/git hash-object --no-filters'),
            3,
        )
        self.assertEqual(text.count("verify_candidate_authority"), 6)
        self.assertNotIn(
            "/usr/bin/python3 -I -S -B scripts/rocky_kernel_source_lock.py",
            text,
        )
        self.assertNotIn(
            "scripts/rocky_kernel_license_review_campaign.py \\\n              \"${common[@]}\"",
            text,
        )
        acquisition = text.split(
            "- name: Acquire the exact SRPM, Linux archive, and dist-git objects",
            1,
        )[1].split("- name: Build and independently verify", 1)[0]
        source_lock_call = acquisition.index(
            '"$AUTHORITY_ROOT/scripts/rocky_kernel_source_lock.py"'
        )
        self.assertNotEqual(
            acquisition.rfind("verify_candidate_authority", 0, source_lock_call),
            -1,
        )
        self.assertNotEqual(
            acquisition.find("verify_candidate_authority", source_lock_call),
            -1,
        )
        build = text.split(
            "- name: Build and independently verify exactly one campaign packet",
            1,
        )[1].split("- name: Upload temporary unreviewed packet", 1)[0]
        build_call = build.index("--build-packet")
        verify_call = build.index("--verify-package")
        self.assertNotEqual(
            build.rfind("verify_candidate_authority", 0, build_call), -1
        )
        self.assertGreater(
            build.rfind("verify_candidate_authority", build_call, verify_call),
            build_call,
        )
        self.assertIn("packet_number=\"$((10#$PACKET_ID))\"", text)
        self.assertIn("test \"$packet_number\" -le 219", text)
        self.assertIn("--build-packet", text)
        self.assertIn("--verify-package", text)
        self.assertIn("retention-days: 30", text)
        self.assertIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", text)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", text)
        self.assertNotIn("final-push.txt", text)
        self.assertNotIn("migration.txt", text)


if __name__ == "__main__":
    unittest.main()
