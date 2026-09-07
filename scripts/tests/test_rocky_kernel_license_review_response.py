#!/usr/bin/env python3
"""Adversarial tests for the generic non-crediting RK-001 response verifier."""

from __future__ import print_function

import ast
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS))

import rocky_kernel_license_review_response as response
import rocky_kernel_license_review_campaign as campaign


CONTRACT = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk001-license-review-response-contract-ef58-v1.json"
)
ASSIGNED_FILES = (
    ".github/workflows/rk001-license-review-response-v1.yml",
    "host-kernel/rocky/evidence/rk001-license-review-response-contract-ef58-v1.json",
    "scripts/rocky_kernel_license_review_response.py",
    "scripts/tests/test_rocky_kernel_license_review_response.py",
)


def sign_bytes(private_key, data, namespace=response.SIGNATURE_NAMESPACE):
    result = subprocess.run(
        [
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            str(private_key),
            "-n",
            namespace,
        ],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError("cannot sign test fixture: {0!r}".format(result.stderr))
    return result.stdout


def make_unit(group_id, content_sha, content_size):
    evidence = {
        "authorship_signals": [],
        "entry_type": "regular",
        "license_text_paths": [],
        "link_target": None,
        "namespace": "linux",
        "origin": "linux-archive:sha256:" + "1" * 64,
        "parent_directory": "linux/drivers/test",
        "path": "linux/drivers/test/example.c",
        "sha256": content_sha,
        "size": content_size,
        "source_identity": {"archive_sha256": "1" * 64},
        "spdx_expression": "NOASSERTION",
        "unresolved_reasons": ["independent-review-required", "missing-spdx"],
    }
    payload = {
        "basis": "missing-spdx-needs-review",
        "candidate_directory_signal_id": None,
        "capture_review_status": "captured-unreviewed",
        "context_group_id": "context:" + "2" * 64,
        "decision": "unresolved",
        "evidence": evidence,
        "exact_content_group_id": group_id,
        "reason_cluster_id": "reason:" + "3" * 64,
        "review_state": "independent-review-required",
    }
    unit = dict(payload)
    unit["unit_id"] = response.stable_id("review-unit", payload)
    return unit


class ReviewResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key_root = tempfile.TemporaryDirectory(prefix="rk001-test-reviewer-")
        cls.private_key = Path(cls.key_root.name) / "reviewer"
        result = subprocess.run(
            [
                "/usr/bin/ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "",
                "-f",
                str(cls.private_key),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("cannot create test-only SSH key: {0!r}".format(result.stderr))
        public_parts = (cls.private_key.with_suffix(".pub")).read_text(
            encoding="ascii"
        ).strip().split()
        cls.public_key = " ".join(public_parts[:2])
        cls.fingerprint = response._public_key_fingerprint(
            cls.public_key, "ssh-ed25519"
        )
        cls.alternate_private_key = Path(cls.key_root.name) / "alternate-reviewer"
        result = subprocess.run(
            [
                "/usr/bin/ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "",
                "-f",
                str(cls.alternate_private_key),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("cannot create alternate test-only SSH key: {0!r}".format(result.stderr))
        alternate_parts = cls.alternate_private_key.with_suffix(".pub").read_text(
            encoding="ascii"
        ).strip().split()
        cls.alternate_public_key = " ".join(alternate_parts[:2])
        cls.alternate_fingerprint = response._public_key_fingerprint(
            cls.alternate_public_key, "ssh-ed25519"
        )
        data = CONTRACT.read_bytes()
        cls.production_authority = response.read_json_bytes(
            data, "response contract", canonical=True
        )
        response.validate_authority(copy.deepcopy(cls.production_authority))
        cls.test_authority = copy.deepcopy(cls.production_authority)
        cls.test_authority["reviewer_authority_policy"] = {
            "independence_registration_required": True,
            "registered_reviewers": [
                {
                    "authority_id": "test-only-reviewer-authority-v1",
                    "independence_authority_sha256": "4" * 64,
                    "independent_from_capture": True,
                    "key_type": "ssh-ed25519",
                    "packet_max": "0219",
                    "packet_min": "0001",
                    "reviewer_identity": "test-reviewer@example.invalid",
                    "ssh_fingerprint": cls.fingerprint,
                    "ssh_public_key": cls.public_key,
                    "valid_from": "2026-01-01T00:00:00Z",
                    "valid_through": "2027-01-01T00:00:00Z",
                }
            ],
            "registration_status": "registered",
            "self_asserted_identity_forbidden": True,
        }
        response.validate_authority(copy.deepcopy(cls.test_authority))

    @classmethod
    def tearDownClass(cls):
        cls.key_root.cleanup()

    def test_campaign_advertises_the_exact_response_unit_schema_and_claim_boundary(self):
        advertised = campaign.EXPECTED_FUTURE_RESPONSE_SCHEMA
        self.assertEqual(set(advertised["unit_decision_fields"]), response.UNIT_DECISION_KEYS)
        self.assertEqual(
            advertised["acceptance"],
            "signed-response-structure-may-include-unresolved-decisions; "
            "campaign-closure-requires-every-unit-independent-fields-affirmative",
        )
        self.assertFalse(advertised["implemented_by_this_campaign"])

    def fixture(self, disposition="resolved"):
        content = b"reviewed fixture content\n"
        content_sha = hashlib.sha256(content).hexdigest()
        identity = {
            "entry_type": "regular",
            "sha256": content_sha,
            "size": len(content),
        }
        group_id = response.stable_id("exact-content", identity)
        groups = [
            {
                "decision_class": "unresolved",
                "group_id": group_id,
                "identity": identity,
                "path_count": 1,
                "path_set_sha256": "5" * 64,
                "review_state": "independent-review-required",
            }
        ]
        units = [make_unit(group_id, content_sha, len(content))]

        support_data = b"external reviewer support\n"
        support_sha = hashlib.sha256(support_data).hexdigest()
        support_payload = {
            "description": "test-only independent support",
            "kind": "license-text",
            "member": "support/" + support_sha,
            "sha256": support_sha,
            "size": len(support_data),
        }
        support_row = dict(support_payload)
        support_row["reference_id"] = response.stable_id("support", support_payload)
        support_ids = [support_row["reference_id"]]

        finding_payload = {
            "conclusion": "resolved" if disposition == "resolved" else "unresolved",
            "content_group_id": group_id,
            "content_sha256": content_sha,
            "content_size": len(content),
            "reviewer_identity": "test-reviewer@example.invalid",
            "spdx_expression_or_unresolved": (
                "GPL-2.0-only" if disposition == "resolved" else "unresolved"
            ),
            "support_reference_ids": support_ids,
        }
        finding = dict(finding_payload)
        finding["content_finding_id"] = response.stable_id(
            "content-finding", finding_payload
        )
        decision = {
            "authorship_status": "affirmed" if disposition == "resolved" else "unresolved",
            "content_finding_id": finding["content_finding_id"],
            "context_group_id": units[0]["context_group_id"],
            "license_status": "affirmed" if disposition == "resolved" else "unresolved",
            "namespace": units[0]["evidence"]["namespace"],
            "origin": units[0]["evidence"]["origin"],
            "path": units[0]["evidence"]["path"],
            "provenance_status": "affirmed" if disposition == "resolved" else "unresolved",
            "redistribution_status": "approved" if disposition == "resolved" else "unresolved",
            "resolved_or_unresolved": disposition,
            "reviewer_identity": "test-reviewer@example.invalid",
            "signed_response_root": "rk001-response-root:" + "0" * 64,
            "source_identity": units[0]["evidence"]["source_identity"],
            "support_reference_ids": support_ids,
            "unit_evidence_sha256": hashlib.sha256(
                response.canonical_json(units[0])
            ).hexdigest(),
            "unit_id": units[0]["unit_id"],
        }
        records = {
            "archive_expansions": [],
            "archive_members": [],
            "content_findings": [finding],
            "support_index": [support_row],
            "unit_decisions": [decision],
        }
        files = {
            "archive-expansions.jsonl": response.canonical_stream(
                records["archive_expansions"]
            ),
            "archive-members.jsonl": response.canonical_stream(
                records["archive_members"]
            ),
            "content-findings.jsonl": response.canonical_stream(
                records["content_findings"]
            ),
            "support-index.jsonl": response.canonical_stream(
                records["support_index"]
            ),
            "unit-decisions.jsonl": response.canonical_stream(
                records["unit_decisions"]
            ),
            "support/" + support_sha: support_data,
        }
        payload_stream = response.unit_payload_stream(records["unit_decisions"])
        streams = {
            "archive_expansions": response.stream_descriptor(
                "archive-expansions.jsonl",
                files["archive-expansions.jsonl"],
                records["archive_expansions"],
            ),
            "archive_members": response.stream_descriptor(
                "archive-members.jsonl",
                files["archive-members.jsonl"],
                records["archive_members"],
            ),
            "content_findings": response.stream_descriptor(
                "content-findings.jsonl",
                files["content-findings.jsonl"],
                records["content_findings"],
            ),
            "support_index": response.stream_descriptor(
                "support-index.jsonl",
                files["support-index.jsonl"],
                records["support_index"],
            ),
            "unit_decisions": response.stream_descriptor(
                "unit-decisions.jsonl",
                files["unit-decisions.jsonl"],
                records["unit_decisions"],
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
                "all_units_individually_reviewed": True,
                "archive_expansion_complete": False,
                "content_findings_auto_resolve_paths": False,
                "credit_eligible": False,
                "durable_archive": False,
                "independent_from_capture": True,
                "machine_classification_auto_accepted": False,
                "tracker_credit": False,
            },
            "campaign_authority_sha256": "a" * 64,
            "campaign_id": response.CAMPAIGN_ID,
            "packet_id": "0002",
            "response_contract_id": response.CONTRACT_ID,
            "review_completed_at": "2026-08-19T12:00:00Z",
            "reviewer_authority_id": "test-only-reviewer-authority-v1",
            "reviewer_identity": "test-reviewer@example.invalid",
            "reviewer_key_fingerprint": self.fingerprint,
            "schema_version": 1,
            "signed_response_root": "rk001-response-root:" + "0" * 64,
            "streams": streams,
        }
        root_id = response.signed_response_root(root)
        root["signed_response_root"] = root_id
        records["unit_decisions"][0]["signed_response_root"] = root_id
        files["unit-decisions.jsonl"] = response.canonical_stream(
            records["unit_decisions"]
        )
        root["streams"]["unit_decisions"].update(
            response.stream_descriptor(
                "unit-decisions.jsonl",
                files["unit-decisions.jsonl"],
                records["unit_decisions"],
            )
        )
        root_bytes = response.canonical_json(root, newline=True)
        files["response-root.json"] = root_bytes
        files["response-root.sig"] = sign_bytes(self.private_key, root_bytes)
        files["SHA256SUMS"] = response._checksum_manifest(files)
        return groups, units, files

    def resign(self, files):
        files["response-root.sig"] = sign_bytes(
            self.private_key, files["response-root.json"]
        )
        files["SHA256SUMS"] = response._checksum_manifest(files)

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

    def test_frozen_contract_is_canonical_empty_single_packet_and_noncrediting(self):
        data = CONTRACT.read_bytes()
        value = response.read_json_bytes(data, "response contract", canonical=True)
        self.assertEqual(response.validate_authority(copy.deepcopy(value)), value)
        self.assertEqual(value["campaign_closure"]["binding_status"], "frozen")
        self.assertEqual(len(value["campaign_closure"]["archive_bindings"]), 3)
        self.assertEqual(value["reviewer_authority_policy"]["registration_status"], "required-missing")
        self.assertEqual(value["reviewer_authority_policy"]["registered_reviewers"], [])
        self.assertTrue(all(claim is False for claim in value["claims"].values()))
        self.assertEqual(value["gate"], response.EXPECTED_GATE)
        self.assertEqual(value["verification_scope"]["mode"], "single-packet-only")
        self.assertFalse(value["verification_scope"]["aggregate_index_supported"])
        self.assertFalse(value["verification_scope"]["campaign_closure_can_be_established"])
        self.assertTrue(
            all(record["sha256"] is not None and record["size"] is not None for record in value["inputs"].values())
        )
        self.assertNotIn("ssh-ed25519 AAAA", data.decode("ascii"))

    def test_contract_recursive_types_duplicate_keys_and_nonfinite_fail(self):
        cases = []
        mutation = copy.deepcopy(self.production_authority)
        mutation["claims"]["campaign_complete"] = 0
        cases.append(mutation)
        mutation = copy.deepcopy(self.production_authority)
        mutation["gate"]["points_awarded"] = False
        cases.append(mutation)
        mutation = copy.deepcopy(self.production_authority)
        mutation["extra"] = False
        cases.append(mutation)
        for mutation in cases:
            with self.assertRaises(response.ReviewResponseError):
                response.validate_authority(mutation)
        mutation = copy.deepcopy(self.test_authority)
        mutation["reviewer_authority_policy"]["registered_reviewers"][0][
            "valid_from"
        ] = "2026-02-31T00:00:00Z"
        with self.assertRaises(response.ReviewResponseError):
            response.validate_authority(mutation)
        malformed_key = self.public_key.split(" ")[0] + " AAAA"
        with self.assertRaises(response.ReviewResponseError):
            response._public_key_fingerprint(malformed_key, "ssh-ed25519")
        for data in (
            b'{"a":1,"a":2}\n',
            b'{"a":NaN}\n',
            b'{"a":1.5}\n',
        ):
            with self.assertRaises(response.ReviewResponseError):
                response.read_json_bytes(data, "hostile JSON", canonical=True)

    def test_campaign_archive_binding_is_exact_and_source_manifest_complete(self):
        campaign_path = REPO_ROOT / self.production_authority["inputs"]["campaign_authority"]["path"]
        campaign_authority = response.read_json_bytes(
            campaign_path.read_bytes(), "campaign authority", canonical=True
        )
        self.assertEqual(
            self.production_authority["campaign_closure"]["archive_bindings"],
            campaign_authority["archive_expansion_bindings"],
        )
        linux = self.production_authority["campaign_closure"]["archive_bindings"][0]
        capture = linux["child_inventory"]["capture_namespace_closure"]
        derived = linux["child_inventory"]["derived_review_closure"]
        self.assertEqual(
            capture["source_manifest_sha256"],
            "321b8a227f7a9473a94db6fbf747c48727a39b20bd8a24474f68578915ca4e56",
        )
        self.assertEqual(
            derived["review_unit_id_stream_sha256"],
            "f24cc1417f7cf1f343bdb9802565398c3d4269263f738b4fff70784930b79180",
        )
        self.assertEqual(
            derived["content_group_id_stream_sha256"],
            "fde9cf1678f54eadf2bf1bce93a752edcd7a10b5b5ff834568235b4a61b1948b",
        )

    def test_valid_test_only_signed_response_is_structural_but_never_crediting(self):
        groups, units, files = self.fixture()
        result = response.verify_response_data(
            self.test_authority, groups, units, files, "a" * 64
        )
        self.assertTrue(result["signature_valid"])
        self.assertTrue(result["reviewer_registered"])
        self.assertEqual(result["reviewed_unit_count"], 1)
        self.assertEqual(result["unresolved_unit_count"], 0)
        self.assertFalse(result["archive_expansion_complete"])
        self.assertFalse(result["campaign_complete"])
        self.assertFalse(result["durable_archive"])
        self.assertFalse(result["credit_eligible"])
        self.assertFalse(result["tracker_credit"])
        self.assertEqual(result["points_awarded"], 0)

    def test_production_empty_registry_rejects_same_valid_signature(self):
        groups, units, files = self.fixture()
        with self.assertRaisesRegex(
            response.ReviewResponseError, "not uniquely registered"
        ):
            response.verify_response_data(
                self.production_authority, groups, units, files, "a" * 64
            )

    def test_wrong_signature_namespace_key_principal_and_root_fail(self):
        groups, units, original = self.fixture()
        cases = []
        wrong_namespace = dict(original)
        wrong_namespace["response-root.sig"] = sign_bytes(
            self.private_key,
            wrong_namespace["response-root.json"],
            namespace="wrong-namespace",
        )
        wrong_namespace["SHA256SUMS"] = response._checksum_manifest(wrong_namespace)
        cases.append(("namespace", self.test_authority, wrong_namespace))

        wrong_principal = copy.deepcopy(self.test_authority)
        wrong_principal["reviewer_authority_policy"]["registered_reviewers"][0][
            "reviewer_identity"
        ] = "different-reviewer@example.invalid"
        cases.append(("principal", wrong_principal, original))

        wrong_root = dict(original)
        root = response.read_json_bytes(
            wrong_root["response-root.json"], "response root", canonical=True
        )
        root["review_completed_at"] = "2026-08-20T12:00:00Z"
        wrong_root["response-root.json"] = response.canonical_json(root, newline=True)
        wrong_root["SHA256SUMS"] = response._checksum_manifest(wrong_root)
        cases.append(("root", self.test_authority, wrong_root))

        for label, authority, files in cases:
            with self.subTest(label=label):
                with self.assertRaises(response.ReviewResponseError):
                    response.verify_response_data(
                        authority, groups, units, files, "a" * 64
                    )
        alternate_reviewer = copy.deepcopy(
            self.test_authority["reviewer_authority_policy"]["registered_reviewers"][0]
        )
        alternate_reviewer["ssh_public_key"] = self.alternate_public_key
        alternate_reviewer["ssh_fingerprint"] = self.alternate_fingerprint
        response.validate_reviewer(alternate_reviewer)
        with self.assertRaises(response.ReviewResponseError):
            response.verify_sshsig(
                original["response-root.json"],
                original["response-root.sig"],
                alternate_reviewer,
            )

    def test_false_independence_and_impossible_review_time_fail(self):
        unused_groups, unused_units, files = self.fixture()
        root = response.read_json_bytes(
            files["response-root.json"], "response root", canonical=True
        )
        root["attestations"]["independent_from_capture"] = False
        with self.assertRaises(response.ReviewResponseError):
            response.validate_root(root, self.test_authority)
        root = response.read_json_bytes(
            files["response-root.json"], "response root", canonical=True
        )
        root["review_completed_at"] = "2026-02-31T00:00:00Z"
        with self.assertRaises(response.ReviewResponseError):
            response.validate_root(root, self.test_authority)

    def test_unit_path_context_source_evidence_finding_and_root_retargets_fail(self):
        groups, units, original = self.fixture()
        for field, replacement in (
            ("path", "linux/retargeted.c"),
            ("context_group_id", "context:" + "9" * 64),
            ("source_identity", {"archive_sha256": "9" * 64}),
            ("unit_evidence_sha256", "9" * 64),
            ("content_finding_id", "content-finding:" + "9" * 64),
            ("signed_response_root", "rk001-response-root:" + "9" * 64),
        ):
            files = dict(original)
            decisions = response.parse_jsonl(
                files["unit-decisions.jsonl"], "unit decisions", 10
            )
            decisions[0][field] = replacement
            files["unit-decisions.jsonl"] = response.canonical_stream(decisions)
            files["SHA256SUMS"] = response._checksum_manifest(files)
            with self.subTest(field=field):
                with self.assertRaises(response.ReviewResponseError):
                    response.verify_response_data(
                        self.test_authority, groups, units, files, "a" * 64
                    )

    def test_resolved_status_requires_every_affirmative_field_and_support(self):
        groups, units, original = self.fixture()
        for field, replacement in (
            ("license_status", "unresolved"),
            ("provenance_status", "unresolved"),
            ("authorship_status", "unresolved"),
            ("redistribution_status", "not-approved"),
            ("support_reference_ids", []),
        ):
            files = dict(original)
            decisions = response.parse_jsonl(
                files["unit-decisions.jsonl"], "unit decisions", 10
            )
            decisions[0][field] = replacement
            files["unit-decisions.jsonl"] = response.canonical_stream(decisions)
            files["SHA256SUMS"] = response._checksum_manifest(files)
            with self.subTest(field=field):
                with self.assertRaises(response.ReviewResponseError):
                    response.verify_response_data(
                        self.test_authority, groups, units, files, "a" * 64
                    )

    def test_omitted_duplicated_reordered_and_extra_stream_rows_fail(self):
        groups, units, original = self.fixture()
        mutations = []
        omitted = dict(original)
        omitted["unit-decisions.jsonl"] = b""
        mutations.append(omitted)
        duplicated = dict(original)
        duplicated["content-findings.jsonl"] += duplicated[
            "content-findings.jsonl"
        ]
        mutations.append(duplicated)
        extra = dict(original)
        extra["archive-expansions.jsonl"] = response.canonical_json(
            {
                "archive_group_id": "exact-content:" + "8" * 64,
                "container_path": "srpm/example.tar.xz",
            },
            newline=True,
        )
        mutations.append(extra)
        for files in mutations:
            files["SHA256SUMS"] = response._checksum_manifest(files)
            with self.assertRaises(response.ReviewResponseError):
                response.verify_response_data(
                    self.test_authority, groups, units, files, "a" * 64
                )

    def test_support_digest_member_omission_and_cross_reference_fail(self):
        groups, units, original = self.fixture()
        support_name = next(name for name in original if name.startswith("support/"))
        cases = []
        missing = dict(original)
        del missing[support_name]
        cases.append(missing)
        corrupt = dict(original)
        corrupt[support_name] = b"corrupt\n"
        cases.append(corrupt)
        cross = dict(original)
        decisions = response.parse_jsonl(
            cross["unit-decisions.jsonl"], "unit decisions", 10
        )
        decisions[0]["support_reference_ids"] = ["support:" + "f" * 64]
        cross["unit-decisions.jsonl"] = response.canonical_stream(decisions)
        cases.append(cross)
        for files in cases:
            files["SHA256SUMS"] = response._checksum_manifest(files)
            with self.assertRaises(response.ReviewResponseError):
                response.verify_response_data(
                    self.test_authority, groups, units, files, "a" * 64
                )

    def test_successor_archive_response_can_never_close_current_campaign(self):
        support = {"support:" + "1" * 64: {}}
        binding = copy.deepcopy(
            self.production_authority["campaign_closure"]["archive_bindings"][1]
        )
        authority = copy.deepcopy(self.production_authority)
        authority["campaign_closure"]["archive_bindings"] = [binding]
        member = {
            "archive_group_id": binding["container"]["group_id"],
            "entry_type": "regular",
            "link_target": None,
            "path": "child/file",
            "sha256": "5" * 64,
            "size": 1,
            "source_identity": {"archive_sha256": binding["container"]["sha256"]},
        }
        stream = response.canonical_stream([member])
        expansion = {
            "archive_binding_sha256": hashlib.sha256(
                response.canonical_json(binding)
            ).hexdigest(),
            "archive_group_id": binding["container"]["group_id"],
            "container_path": binding["container"]["path"],
            "container_sha256": binding["container"]["sha256"],
            "container_size": binding["container"]["size"],
            "expansion_role": binding["role"],
            "expansion_status": "future-v2-child-inventory-required",
            "member_count": 1,
            "member_stream_sha256": hashlib.sha256(stream).hexdigest(),
            "member_stream_size": len(stream),
            "reviewer_identity": "test-reviewer@example.invalid",
            "support_reference_ids": ["support:" + "1" * 64],
        }
        self.assertFalse(
            response.validate_archive_expansions(
                [expansion],
                [member],
                authority,
                "test-reviewer@example.invalid",
                support,
                "0218",
            )
        )
        promoted = dict(expansion)
        promoted["expansion_status"] = "matched-existing-inventory"
        with self.assertRaises(response.ReviewResponseError):
            response.validate_archive_expansions(
                [promoted],
                [member],
                authority,
                "test-reviewer@example.invalid",
                support,
                "0218",
            )
        retargeted = copy.deepcopy(member)
        retargeted["source_identity"] = {"archive_sha256": "0" * 64}
        with self.assertRaises(response.ReviewResponseError):
            response.validate_archive_expansions(
                [expansion],
                [retargeted],
                authority,
                "test-reviewer@example.invalid",
                support,
                "0218",
            )

    def materialize_response(self, parent, files):
        output = Path(parent) / "response"
        output.mkdir(mode=0o755)
        support = output / "support"
        support.mkdir(mode=0o755)
        for name, data in files.items():
            target = output / name
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            target.write_bytes(data)
            os.chmod(str(target), 0o444)
        return output

    def test_descriptor_package_reader_accepts_exact_directory_and_rejects_leaf_types(self):
        _, _, files = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            directory = self.materialize_response(temporary, files)
            self.assertEqual(response.read_response_package(directory), files)
        for case in ("mode", "symlink", "hardlink"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                directory = self.materialize_response(temporary, files)
                member = directory / "response-root.json"
                if case == "mode":
                    os.chmod(str(member), 0o644)
                else:
                    data = member.read_bytes()
                    member.unlink()
                    outside = Path(temporary) / "outside"
                    outside.write_bytes(data)
                    os.chmod(str(outside), 0o444)
                    if case == "symlink":
                        member.symlink_to(outside)
                    else:
                        os.link(str(outside), str(member))
                with self.assertRaises(response.ReviewResponseError):
                    response.read_response_package(directory)

    def test_authority_reader_rejects_leaf_and_ancestor_namespace_swaps(self):
        for case in ("leaf", "ancestor"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                outer = base / "outer"
                inner = outer / "inner"
                inner.mkdir(parents=True)
                target = inner / "authority.json"
                target.write_bytes(b'{"frozen":true}\n')
                original_pass = response._read_held_regular_pass
                calls = [0]

                def swap_after_first(context, label, cap):
                    data = original_pass(context, label, cap)
                    calls[0] += 1
                    if calls[0] == 1:
                        if case == "leaf":
                            replacement = inner / "replacement"
                            replacement.write_bytes(data)
                            os.replace(str(replacement), str(target))
                        else:
                            held = base / "held-outer"
                            outer.rename(held)
                            replacement_inner = outer / "inner"
                            replacement_inner.mkdir(parents=True)
                            (replacement_inner / "authority.json").write_bytes(data)
                    return data

                with mock.patch.object(
                    response, "_read_held_regular_pass", side_effect=swap_after_first
                ):
                    with self.assertRaises(response.ReviewResponseError):
                        response.read_regular_file_once(target, "hostile authority", 1024)

    def test_package_replay_rejects_named_member_and_root_swaps(self):
        unused_groups, unused_units, files = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            directory = self.materialize_response(temporary, files)
            root = response._open_dir(directory, "test response root")
            member = None
            try:
                root["expected_names"] = response._list_dir(
                    root, len(response.TOP_LEVEL_MEMBERS) + 1
                )
                member = response._open_member(
                    root, "response-root.json", "test response root member"
                )
                replacement = base / "replacement-root.json"
                replacement.write_bytes(files["response-root.json"])
                os.chmod(str(replacement), 0o444)
                os.replace(str(replacement), str(directory / "response-root.json"))
                with self.assertRaises(response.ReviewResponseError):
                    response._verify_member(member)
            finally:
                if member is not None:
                    os.close(member["fd"])
                response._close_dir(root)

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            directory = self.materialize_response(temporary, files)
            root = response._open_dir(directory, "test response root")
            try:
                root["expected_names"] = response._list_dir(
                    root, len(response.TOP_LEVEL_MEMBERS) + 1
                )
                held = base / "held-response"
                directory.rename(held)
                directory.mkdir()
                with self.assertRaises(response.ReviewResponseError):
                    response._replay_dir(root)
            finally:
                response._close_dir(root)

    def test_sshsig_uses_retained_immutable_pass_fds(self):
        unused_groups, unused_units, files = self.fixture()
        reviewer = self.test_authority["reviewer_authority_policy"][
            "registered_reviewers"
        ][0]
        with mock.patch.object(
            response.subprocess, "Popen", wraps=response.subprocess.Popen
        ) as popen:
            self.assertTrue(
                response.verify_sshsig(
                    files["response-root.json"], files["response-root.sig"], reviewer
                )
            )
        command = popen.call_args[0][0]
        passed = popen.call_args[1]["pass_fds"]
        self.assertEqual(len(passed), 2)
        self.assertEqual(command[command.index("-f") + 1], "/proc/self/fd/{0}".format(passed[0]))
        self.assertEqual(command[command.index("-s") + 1], "/proc/self/fd/{0}".format(passed[1]))
        self.assertFalse(any("rk001-response-signature-" in value for value in command))

    def test_package_preflight_rejects_aggregate_before_read(self):
        _, _, files = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            directory = self.materialize_response(temporary, files)
            with mock.patch.object(response, "MAX_RESPONSE_BYTES", 1), mock.patch.object(
                response, "_read_member", wraps=response._read_member
            ) as reader:
                with self.assertRaisesRegex(
                    response.ReviewResponseError, "aggregate exceeds"
                ):
                    response.read_response_package(directory)
                self.assertEqual(reader.call_count, 0)

    def test_workflow_is_dispatch_only_exact_head_external_signature_only(self):
        text = (REPO_ROOT / ASSIGNED_FILES[0]).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("\n  push:", text)
        self.assertNotIn("\n  pull_request:", text)
        self.assertNotIn("\n  schedule:", text)
        self.assertIn('test "$GITHUB_SHA" = "$EXPECTED_HEAD_SHA"', text)
        self.assertIn('test "$GITHUB_WORKFLOW_SHA" = "$EXPECTED_HEAD_SHA"', text)
        self.assertIn("--verify-response", text)
        self.assertNotIn("--verify-set", text)
        self.assertIn("exact single-packet response", text)
        self.assertIn("/usr/bin/ssh-keygen", text)
        self.assertNotIn("ssh-keygen -Y sign", text)
        self.assertNotIn("PRIVATE_KEY", text)
        self.assertIn("retention-days: 30", text)
        self.assertIn("durable=false gate=TODO points=0 credit=false", text)
        self.assertNotIn("final-push.txt", text)


if __name__ == "__main__":
    unittest.main()
