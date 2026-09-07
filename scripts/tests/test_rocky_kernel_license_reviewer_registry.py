#!/usr/bin/env python3
"""Adversarial tests for the non-registering RK-001 reviewer registry."""

from __future__ import print_function

import ast
import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS))

import rocky_kernel_license_reviewer_registry as registry


AUTHORITY = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk001-license-reviewer-registry-ef58-v1.json"
)
CAMPAIGN = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk001-license-review-campaign-ef58-v1.json"
)
CHECKER = REPO_ROOT / "scripts/rocky_kernel_license_reviewer_registry.py"
ASSIGNED_FILES = (
    "host-kernel/rocky/evidence/rk001-license-reviewer-registry-ef58-v1.json",
    "scripts/rocky_kernel_license_reviewer_registry.py",
    "scripts/tests/test_rocky_kernel_license_reviewer_registry.py",
)


def generate_key(root, name):
    private_key = Path(root) / name
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
            str(private_key),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("cannot generate fixture key: {0!r}".format(result.stderr))
    parts = private_key.with_suffix(".pub").read_text(encoding="ascii").strip().split()
    public_key = " ".join(parts[:2])
    fingerprint = registry._public_key_fingerprint(public_key, "ssh-ed25519")
    return private_key, public_key, fingerprint


def sign_bytes(private_key, payload, namespace):
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
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError("cannot sign fixture: {0!r}".format(result.stderr))
    return result.stdout.decode("ascii")


class ReviewerRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key_root = tempfile.TemporaryDirectory(prefix="rk001-registry-keys-")
        (
            cls.reviewer_private,
            cls.reviewer_public,
            cls.reviewer_fingerprint,
        ) = generate_key(cls.key_root.name, "reviewer")
        (
            cls.authority_private,
            cls.authority_public,
            cls.authority_fingerprint,
        ) = generate_key(cls.key_root.name, "appointing-authority")
        cls.production_bytes = AUTHORITY.read_bytes()
        cls.production_authority = registry.read_json_bytes(
            cls.production_bytes, "production authority", canonical=True
        )
        registry.validate_authority(copy.deepcopy(cls.production_authority))

    @classmethod
    def tearDownClass(cls):
        cls.key_root.cleanup()

    def signature_record(self, private_key, payload, namespace):
        payload_bytes = registry.canonical_json(payload, newline=True)
        return {
            "format": registry.SSHSIG_FORMAT,
            "namespace": namespace,
            "payload_algorithm": registry.PAYLOAD_ALGORITHM,
            "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "signature": sign_bytes(private_key, payload_bytes, namespace),
        }

    def fixture(self, status="active"):
        candidate = {
            "appointing_authority": {
                "authority_id": "outside-counsel-appointment-v1",
                "issued_at": "2026-08-01T00:00:00Z",
                "issuer_identity": "appointing-counsel@example.invalid",
                "issuer_organization": "Outside Counsel Group",
                "key_type": "ssh-ed25519",
                "ssh_fingerprint": self.authority_fingerprint,
                "ssh_public_key": self.authority_public,
            },
            "campaign_binding": {
                "campaign_authority_sha256": registry.CAMPAIGN_SHA256,
                "campaign_id": registry.CAMPAIGN_ID,
                "source_commit": registry.SOURCE_COMMIT,
            },
            "reviewer": {
                "key_type": "ssh-ed25519",
                "organization": "Independent Review Lab",
                "reviewer_identity": "reviewer@example.invalid",
                "role": "independent-license-reviewer",
                "ssh_fingerprint": self.reviewer_fingerprint,
                "ssh_public_key": self.reviewer_public,
            },
            "scope": {"packet_max": "0219", "packet_min": "0001"},
            "status": status,
            "validity": {
                "valid_from": "2026-08-02T00:00:00Z",
                "valid_through": "2027-08-02T00:00:00Z",
            },
        }
        candidate["appointment_id"] = registry.stable_id(
            "appointment", registry.appointment_identity_payload(candidate)
        )
        evidence = {
            "appointment_id": candidate["appointment_id"],
            "appointment_status": candidate["status"],
            "campaign_id": registry.CAMPAIGN_ID,
            "capture_operator_identities": ["capture-operator@example.invalid"],
            "capture_organization": "McKernel Capture Team",
            "conflict_check": "completed-no-conflict",
            "evidence_basis": "organizational-separation-and-conflict-check-v1",
            "independent_from_campaign_generation": True,
            "independent_from_capture": True,
            "independent_from_source_capture": True,
            "issued_at": candidate["appointing_authority"]["issued_at"],
            "issuer_identity": candidate["appointing_authority"]["issuer_identity"],
            "issuer_organization": candidate["appointing_authority"][
                "issuer_organization"
            ],
            "reviewer_identity": candidate["reviewer"]["reviewer_identity"],
            "reviewer_organization": candidate["reviewer"]["organization"],
            "schema_version": 1,
            "source_commit": registry.SOURCE_COMMIT,
            "statement": "The appointed reviewer is organizationally and operationally independent from source capture and campaign generation.",
        }
        evidence["evidence_id"] = registry.stable_id(
            "independence-evidence", registry.evidence_identity_payload(evidence)
        )
        evidence["authority_proof"] = self.signature_record(
            self.authority_private,
            registry.evidence_signing_payload(evidence),
            registry.INDEPENDENCE_NAMESPACE,
        )
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        candidate["independence_evidence"] = {
            "path": "independence-evidence.json",
            "sha256": hashlib.sha256(evidence_bytes).hexdigest(),
            "size": len(evidence_bytes),
        }
        candidate["proof_of_key_possession"] = self.signature_record(
            self.reviewer_private,
            registry.appointment_signing_payload(candidate),
            registry.POSSESSION_NAMESPACE,
        )
        return candidate, evidence

    def resign_candidate(self, candidate):
        candidate["proof_of_key_possession"] = self.signature_record(
            self.reviewer_private,
            registry.appointment_signing_payload(candidate),
            registry.POSSESSION_NAMESPACE,
        )

    def bind_evidence(self, candidate, evidence, resign_candidate=True):
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        candidate["independence_evidence"]["sha256"] = hashlib.sha256(
            evidence_bytes
        ).hexdigest()
        candidate["independence_evidence"]["size"] = len(evidence_bytes)
        if resign_candidate:
            self.resign_candidate(candidate)
        return evidence_bytes

    def write_fixture(self, root, candidate, evidence):
        root = Path(root)
        evidence_bytes = self.bind_evidence(candidate, evidence)
        candidate_path = root / "candidate.json"
        candidate_path.write_bytes(registry.canonical_json(candidate, newline=True))
        (root / candidate["independence_evidence"]["path"]).write_bytes(evidence_bytes)
        return candidate_path

    def assert_allowed_signers_popen_swap_rejected(
        self, candidate, evidence, target_namespace, replacement_public_key
    ):
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        original_popen = registry.subprocess.Popen
        swapped = [False]

        def popen_after_allowed_swap(command, *args, **kwargs):
            namespace = command[command.index("-n") + 1]
            if namespace == target_namespace and not swapped[0]:
                allowed_proc = command[command.index("-f") + 1]
                allowed_path = Path(os.readlink(allowed_proc))
                principal = command[command.index("-I") + 1]
                allowed_path.unlink()
                allowed_path.write_bytes(
                    (principal + " " + replacement_public_key + "\n").encode("ascii")
                )
                os.chmod(str(allowed_path), 0o400)
                swapped[0] = True
            return original_popen(command, *args, **kwargs)

        with mock.patch.object(
            registry.subprocess, "Popen", side_effect=popen_after_allowed_swap
        ):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.validate_candidate(candidate, evidence_bytes)
        self.assertTrue(swapped[0])

    def assert_structure_rejected(self, mutate):
        candidate, evidence = self.fixture()
        mutate(candidate)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_appointment_structure(candidate)

    def assert_evidence_rejected(self, mutate):
        candidate, evidence = self.fixture()
        mutate(evidence, candidate)
        evidence_bytes = self.bind_evidence(candidate, evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)

    def test_production_authority_is_exact_empty_and_non_crediting(self):
        authority, campaign = registry.check_repository(REPO_ROOT)
        self.assertEqual(authority["appointments"], [])
        self.assertEqual(authority["registration_status"], "required-missing")
        self.assertEqual(authority["registry_version"], registry.REGISTRY_VERSION)
        self.assertEqual(authority["revocation_epoch"], registry.REVOCATION_EPOCH)
        self.assertEqual(
            authority["appointment_policy"]["appointment_statuses"],
            ["active", "revoked"],
        )
        self.assertEqual(
            authority["appointment_policy"]["production_appointment_record_fields"],
            ["appointment", "independence_evidence"],
        )
        self.assertTrue(
            authority["appointment_policy"]["production_evidence_embedded"]
        )
        self.assertEqual(
            authority["appointment_policy"]["production_record_schema"],
            "embedded-appointment-and-independence-evidence-v1",
        )
        self.assertTrue(all(value is False for value in authority["claims"].values()))
        self.assertTrue(
            all(
                value is False
                for key, value in authority["durability"].items()
                if key != "status"
            )
        )
        self.assertFalse(authority["gate"]["gate_complete"])
        self.assertFalse(authority["gate"]["credit_eligible"])
        self.assertFalse(authority["gate"]["tracker_credit"])
        self.assertEqual(authority["gate"]["points_awarded"], 0)
        self.assertEqual(campaign["campaign_id"], registry.CAMPAIGN_ID)

    def test_authority_and_campaign_exact_frozen_bytes(self):
        authority_bytes = AUTHORITY.read_bytes()
        campaign_bytes = CAMPAIGN.read_bytes()
        self.assertEqual(len(authority_bytes), registry.AUTHORITY_SIZE)
        self.assertEqual(
            hashlib.sha256(authority_bytes).hexdigest(), registry.AUTHORITY_SHA256
        )
        self.assertEqual(len(campaign_bytes), registry.CAMPAIGN_SIZE)
        self.assertEqual(
            hashlib.sha256(campaign_bytes).hexdigest(), registry.CAMPAIGN_SHA256
        )
        self.assertEqual(
            authority_bytes,
            registry.canonical_json(self.production_authority, newline=True),
        )

    def test_check_cli_reports_no_registration_or_credit(self):
        result = subprocess.run(
            ["python3", str(CHECKER), "--check", "--repo", str(REPO_ROOT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout.decode("utf-8")
        self.assertIn("appointments=0", text)
        self.assertIn("registration=required-missing", text)
        self.assertIn("gate=TODO", text)
        self.assertIn("credit=0", text)

    def test_authority_mutations_fail_closed(self):
        mutations = []
        for key in registry.EXPECTED_CLAIMS:
            mutations.append(lambda value, key=key: value["claims"].__setitem__(key, True))
        for key in (
            "candidate_file_is_durable_registration",
            "durable_registration_present",
            "repository_registry_is_durable_authority",
            "workflow_artifact_is_durable_registration",
        ):
            mutations.append(
                lambda value, key=key: value["durability"].__setitem__(key, True)
            )
        mutations.extend(
            [
                lambda value: value.__setitem__("appointments", [{}]),
                lambda value: value.__setitem__("registration_status", "registered"),
                lambda value: value.__setitem__("registry_version", 2),
                lambda value: value.__setitem__("revocation_epoch", 0),
                lambda value: value["gate"].__setitem__("status", "PASS"),
                lambda value: value["gate"].__setitem__("points_awarded", 50),
                lambda value: value["gate"].__setitem__("gate_complete", True),
                lambda value: value["campaign_binding"].__setitem__("packet_count", 218),
                lambda value: value["appointment_policy"].__setitem__(
                    "candidate_lint_registers", True
                ),
                lambda value: value["appointment_policy"].__setitem__(
                    "production_evidence_embedded", False
                ),
                lambda value: value["appointment_policy"].__setitem__(
                    "production_appointment_record_fields", ["appointment"]
                ),
                lambda value: value["appointment_policy"].__setitem__(
                    "production_record_schema", "external-evidence-v1"
                ),
                lambda value: value.__setitem__("extra", False),
                lambda value: value.pop("remaining_blockers"),
            ]
        )
        for mutate in mutations:
            value = copy.deepcopy(self.production_authority)
            mutate(value)
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.validate_authority(value)

    def test_campaign_binding_mutations_fail_closed(self):
        campaign = registry.read_json_bytes(
            CAMPAIGN.read_bytes(), "campaign", canonical=True
        )
        mutations = (
            lambda value: value.__setitem__("campaign_id", "wrong"),
            lambda value: value["expected_result"].__setitem__("packet_count", 220),
            lambda value: value["expected_result"].__setitem__(
                "review_unit_count", 115264
            ),
            lambda value: value["expected_result"].__setitem__(
                "content_group_count", 111003
            ),
            lambda value: value["claims"].__setitem__("credit_eligible", True),
            lambda value: value["gate"].__setitem__("tracker_credit", True),
            lambda value: value["inputs"]["inventory_artifact"].__setitem__(
                "source_commit", "0" * 40
            ),
            lambda value: value["packets"].pop(),
        )
        for mutate in mutations:
            value = copy.deepcopy(campaign)
            mutate(value)
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.validate_campaign(value)

    def test_json_parser_rejects_noncanonical_and_hostile_values(self):
        cases = (
            b'{"a":1,"a":2}\n',
            b'{"a":1.0}\n',
            b'{"a":NaN}\n',
            b'{"a":"\xc3\xa9"}\n',
            b'{ "a":1}\n',
            b'[]\n',
        )
        for data in cases:
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.read_json_bytes(data, "hostile", canonical=True)
        deep = {}
        current = deep
        for _index in range(registry.MAX_JSON_NESTING + 2):
            current["x"] = {}
            current = current["x"]
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.canonical_json(deep)

    def test_safe_relative_rejects_escape_and_non_normal_paths(self):
        for value in (
            "/absolute.json",
            "../escape.json",
            "dir/../escape.json",
            "dir//file.json",
            "dir\\file.json",
            "./file.json",
        ):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.safe_relative(value, "fixture")

    def test_valid_candidate_and_both_cryptographic_proofs_pass(self):
        candidate, evidence = self.fixture()
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        candidate_copy, evidence_copy = registry.validate_candidate(
            candidate, evidence_bytes
        )
        self.assertEqual(
            candidate_copy["appointment_id"], candidate["appointment_id"]
        )
        self.assertEqual(evidence_copy["evidence_id"], evidence["evidence_id"])
        self.assertIsNot(candidate_copy, candidate)
        self.assertIsNot(evidence_copy, evidence)

    def test_candidate_cli_is_read_only_and_never_registers(self):
        candidate, evidence = self.fixture()
        before = AUTHORITY.read_bytes()
        with tempfile.TemporaryDirectory(prefix="rk001-candidate-cli-") as root:
            candidate_path = self.write_fixture(root, candidate, evidence)
            result = subprocess.run(
                [
                    "python3",
                    str(CHECKER),
                    "--candidate-lint",
                    str(candidate_path),
                    "--repo",
                    str(REPO_ROOT),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"VALID (NOT REGISTERED)", result.stdout)
        self.assertEqual(AUTHORITY.read_bytes(), before)

    def test_candidate_top_level_shape_mutations_fail(self):
        self.assert_structure_rejected(lambda value: value.__setitem__("extra", False))
        self.assert_structure_rejected(lambda value: value.pop("scope"))
        self.assert_structure_rejected(
            lambda value: value.__setitem__("appointment_id", "appointment:" + "0" * 64)
        )

    def test_candidate_campaign_binding_mutations_fail(self):
        mutations = (
            lambda value: value["campaign_binding"].__setitem__("campaign_id", "wrong"),
            lambda value: value["campaign_binding"].__setitem__(
                "campaign_authority_sha256", "0" * 64
            ),
            lambda value: value["campaign_binding"].__setitem__(
                "source_commit", "0" * 40
            ),
            lambda value: value["campaign_binding"].__setitem__("extra", False),
        )
        for mutate in mutations:
            self.assert_structure_rejected(mutate)

    def test_reviewer_identity_role_organization_and_key_mutations_fail(self):
        mutations = (
            lambda value: value["reviewer"].__setitem__("reviewer_identity", "bad identity"),
            lambda value: value["reviewer"].__setitem__("organization", "x"),
            lambda value: value["reviewer"].__setitem__("role", "capture-operator"),
            lambda value: value["reviewer"].__setitem__("key_type", "ssh-rsa"),
            lambda value: value["reviewer"].__setitem__("ssh_public_key", "ssh-ed25519 AAAA"),
            lambda value: value["reviewer"].__setitem__("ssh_fingerprint", "SHA256:wrong"),
            lambda value: value["reviewer"].__setitem__("extra", False),
        )
        for mutate in mutations:
            self.assert_structure_rejected(mutate)

    def test_appointing_authority_identity_and_separation_mutations_fail(self):
        mutations = (
            lambda value: value["appointing_authority"].__setitem__("authority_id", "BAD"),
            lambda value: value["appointing_authority"].__setitem__(
                "issuer_identity", value["reviewer"]["reviewer_identity"]
            ),
            lambda value: value["appointing_authority"].__setitem__(
                "issuer_organization", value["reviewer"]["organization"]
            ),
            lambda value: value["appointing_authority"].__setitem__(
                "ssh_fingerprint", "SHA256:wrong"
            ),
            lambda value: value["appointing_authority"].__setitem__("extra", False),
        )
        for mutate in mutations:
            self.assert_structure_rejected(mutate)

    def test_same_key_self_appointment_fails_even_with_distinct_names_and_orgs(self):
        candidate, evidence = self.fixture()
        candidate["appointing_authority"]["ssh_public_key"] = self.reviewer_public
        candidate["appointing_authority"][
            "ssh_fingerprint"
        ] = self.reviewer_fingerprint
        candidate["appointment_id"] = registry.stable_id(
            "appointment", registry.appointment_identity_payload(candidate)
        )
        evidence["appointment_id"] = candidate["appointment_id"]
        evidence["evidence_id"] = registry.stable_id(
            "independence-evidence", registry.evidence_identity_payload(evidence)
        )
        evidence["authority_proof"] = self.signature_record(
            self.reviewer_private,
            registry.evidence_signing_payload(evidence),
            registry.INDEPENDENCE_NAMESPACE,
        )
        evidence_bytes = self.bind_evidence(candidate, evidence)
        self.assertNotEqual(
            candidate["reviewer"]["reviewer_identity"],
            candidate["appointing_authority"]["issuer_identity"],
        )
        self.assertNotEqual(
            candidate["reviewer"]["organization"],
            candidate["appointing_authority"]["issuer_organization"],
        )
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)

    def test_appointment_status_is_signed_and_strict(self):
        self.assert_structure_rejected(
            lambda value: value.__setitem__("status", "candidate")
        )
        self.assert_structure_rejected(lambda value: value.pop("status"))

    def test_scope_mutations_fail(self):
        mutations = (
            lambda value: value["scope"].__setitem__("packet_min", "0000"),
            lambda value: value["scope"].__setitem__("packet_max", "0220"),
            lambda value: value["scope"].update(
                {"packet_min": "0100", "packet_max": "0099"}
            ),
            lambda value: value["scope"].__setitem__("packet_min", 1),
            lambda value: value["scope"].__setitem__("extra", False),
        )
        for mutate in mutations:
            self.assert_structure_rejected(mutate)

    def test_validity_mutations_fail(self):
        mutations = (
            lambda value: value["validity"].__setitem__(
                "valid_from", "2026-07-31T00:00:00Z"
            ),
            lambda value: value["validity"].update(
                {
                    "valid_from": "2027-01-02T00:00:00Z",
                    "valid_through": "2027-01-01T00:00:00Z",
                }
            ),
            lambda value: value["validity"].update(
                {
                    "valid_from": "2026-08-02T00:00:00Z",
                    "valid_through": "2027-08-04T00:00:00Z",
                }
            ),
            lambda value: value["validity"].__setitem__(
                "valid_from", "2026-02-30T00:00:00Z"
            ),
            lambda value: value["validity"].__setitem__("extra", False),
        )
        for mutate in mutations:
            self.assert_structure_rejected(mutate)

    def test_evidence_binding_mutations_fail(self):
        mutations = (
            lambda value: value["independence_evidence"].__setitem__(
                "path", "../escape.json"
            ),
            lambda value: value["independence_evidence"].__setitem__(
                "path", "/absolute.json"
            ),
            lambda value: value["independence_evidence"].__setitem__(
                "sha256", "not-a-digest"
            ),
            lambda value: value["independence_evidence"].__setitem__("size", 0),
            lambda value: value["independence_evidence"].__setitem__(
                "size", registry.MAX_EVIDENCE_BYTES + 1
            ),
            lambda value: value["independence_evidence"].__setitem__("extra", False),
        )
        for mutate in mutations:
            self.assert_structure_rejected(mutate)

    def test_evidence_identity_binding_and_conflict_mutations_fail(self):
        mutations = (
            lambda evidence, candidate: evidence.__setitem__("campaign_id", "wrong"),
            lambda evidence, candidate: evidence.__setitem__(
                "source_commit", "0" * 40
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "appointment_id", "appointment:" + "0" * 64
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "appointment_status", "revoked"
                if candidate["status"] == "active"
                else "active"
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "reviewer_identity", "other@example.invalid"
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "reviewer_organization", "Other Review Lab"
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "issuer_identity", "other-counsel@example.invalid"
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "issued_at", "2026-08-01T00:00:01Z"
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "conflict_check", "not-completed"
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "evidence_basis", "self-assertion"
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "statement", "This is not sufficient independence evidence."
            ),
            lambda evidence, candidate: evidence.__setitem__("schema_version", 2),
            lambda evidence, candidate: evidence.__setitem__("extra", False),
        )
        for mutate in mutations:
            self.assert_evidence_rejected(mutate)

    def test_evidence_independence_boolean_mutations_fail(self):
        for key in (
            "independent_from_campaign_generation",
            "independent_from_capture",
            "independent_from_source_capture",
        ):
            self.assert_evidence_rejected(
                lambda evidence, candidate, key=key: evidence.__setitem__(key, False)
            )
            self.assert_evidence_rejected(
                lambda evidence, candidate, key=key: evidence.__setitem__(key, 0)
            )

    def test_evidence_capture_separation_and_order_mutations_fail(self):
        mutations = (
            lambda evidence, candidate: evidence.__setitem__(
                "capture_organization", candidate["reviewer"]["organization"]
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "capture_operator_identities", []
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "capture_operator_identities",
                [candidate["reviewer"]["reviewer_identity"]],
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "capture_operator_identities", ["z@example.invalid", "a@example.invalid"]
            ),
            lambda evidence, candidate: evidence.__setitem__(
                "capture_operator_identities",
                ["capture@example.invalid", "capture@example.invalid"],
            ),
        )
        for mutate in mutations:
            self.assert_evidence_rejected(mutate)

    def test_evidence_id_and_binding_digest_mutations_fail(self):
        candidate, evidence = self.fixture()
        evidence["evidence_id"] = "independence-evidence:" + "0" * 64
        evidence_bytes = self.bind_evidence(candidate, evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)
        candidate, evidence = self.fixture()
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        candidate["independence_evidence"]["sha256"] = "0" * 64
        self.resign_candidate(candidate)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)
        candidate, evidence = self.fixture()
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        candidate["independence_evidence"]["size"] += 1
        self.resign_candidate(candidate)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)

    def test_authority_signature_mutations_fail_cryptographically(self):
        candidate, evidence = self.fixture()
        signature = evidence["authority_proof"]["signature"]
        evidence["authority_proof"]["signature"] = signature.replace("A", "B", 1)
        evidence_bytes = self.bind_evidence(candidate, evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)
        candidate, evidence = self.fixture()
        evidence["authority_proof"]["namespace"] = registry.POSSESSION_NAMESPACE
        evidence_bytes = self.bind_evidence(candidate, evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)
        candidate, evidence = self.fixture()
        evidence["authority_proof"]["payload_sha256"] = "0" * 64
        evidence_bytes = self.bind_evidence(candidate, evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)

    def test_independence_evidence_signed_by_wrong_key_fails(self):
        candidate, evidence = self.fixture()
        evidence["authority_proof"] = self.signature_record(
            self.reviewer_private,
            registry.evidence_signing_payload(evidence),
            registry.INDEPENDENCE_NAMESPACE,
        )
        evidence_bytes = self.bind_evidence(candidate, evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(candidate, evidence_bytes)

    def test_reviewer_possession_signature_mutations_fail_cryptographically(self):
        candidate, evidence = self.fixture()
        signature = candidate["proof_of_key_possession"]["signature"]
        candidate["proof_of_key_possession"]["signature"] = signature.replace("A", "B", 1)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(
                candidate, registry.canonical_json(evidence, newline=True)
            )
        candidate, evidence = self.fixture()
        candidate["proof_of_key_possession"]["namespace"] = registry.INDEPENDENCE_NAMESPACE
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_appointment_structure(candidate)
        candidate, evidence = self.fixture()
        candidate["proof_of_key_possession"]["payload_sha256"] = "0" * 64
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_appointment_structure(candidate)

    def test_signature_from_wrong_private_key_fails(self):
        candidate, evidence = self.fixture()
        payload = registry.appointment_signing_payload(candidate)
        candidate["proof_of_key_possession"] = self.signature_record(
            self.authority_private, payload, registry.POSSESSION_NAMESPACE
        )
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_candidate(
                candidate, registry.canonical_json(evidence, newline=True)
            )

    def test_possession_allowed_signers_popen_swap_cannot_accept_wrong_key(self):
        candidate, evidence = self.fixture()
        candidate["proof_of_key_possession"] = self.signature_record(
            self.authority_private,
            registry.appointment_signing_payload(candidate),
            registry.POSSESSION_NAMESPACE,
        )
        self.assert_allowed_signers_popen_swap_rejected(
            candidate,
            evidence,
            registry.POSSESSION_NAMESPACE,
            self.authority_public,
        )

    def test_independence_allowed_signers_popen_swap_cannot_accept_wrong_key(self):
        candidate, evidence = self.fixture()
        evidence["authority_proof"] = self.signature_record(
            self.reviewer_private,
            registry.evidence_signing_payload(evidence),
            registry.INDEPENDENCE_NAMESPACE,
        )
        self.bind_evidence(candidate, evidence)
        self.assert_allowed_signers_popen_swap_rejected(
            candidate,
            evidence,
            registry.INDEPENDENCE_NAMESPACE,
            self.reviewer_public,
        )

    def test_candidate_file_security_rejects_symlink_hardlink_and_write_bits(self):
        candidate, evidence = self.fixture()
        with tempfile.TemporaryDirectory(prefix="rk001-candidate-security-") as root:
            root_path = Path(root)
            candidate_path = self.write_fixture(root, candidate, evidence)
            symlink_path = root_path / "candidate-link.json"
            symlink_path.symlink_to(candidate_path.name)
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.load_and_validate_candidate(symlink_path)
            hardlink_path = root_path / "candidate-hard.json"
            os.link(str(candidate_path), str(hardlink_path))
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.load_and_validate_candidate(candidate_path)
            hardlink_path.unlink()
            os.chmod(str(candidate_path), 0o666)
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.load_and_validate_candidate(candidate_path)

    def test_evidence_file_security_rejects_symlink_and_hardlink(self):
        candidate, evidence = self.fixture()
        with tempfile.TemporaryDirectory(prefix="rk001-evidence-security-") as root:
            root_path = Path(root)
            target = root_path / "target.json"
            evidence_bytes = registry.canonical_json(evidence, newline=True)
            target.write_bytes(evidence_bytes)
            candidate["independence_evidence"].update(
                {
                    "path": "evidence-link.json",
                    "sha256": hashlib.sha256(evidence_bytes).hexdigest(),
                    "size": len(evidence_bytes),
                }
            )
            self.resign_candidate(candidate)
            candidate_path = root_path / "candidate.json"
            candidate_path.write_bytes(registry.canonical_json(candidate, newline=True))
            (root_path / "evidence-link.json").symlink_to(target.name)
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.load_and_validate_candidate(candidate_path)
            (root_path / "evidence-link.json").unlink()
            os.link(str(target), str(root_path / "evidence-link.json"))
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.load_and_validate_candidate(candidate_path)

    def test_repository_reader_rejects_symlink_and_unstable_inputs(self):
        with tempfile.TemporaryDirectory(prefix="rk001-repo-security-") as root:
            root_path = Path(root)
            (root_path / "real.json").write_bytes(b"{}\n")
            (root_path / "link.json").symlink_to("real.json")
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.read_secure_relative(root_path, "link.json", "fixture", 1024)
            os.chmod(str(root_path / "real.json"), 0o666)
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.read_secure_relative(root_path, "real.json", "fixture", 1024)
        with mock.patch.object(registry.os, "fstat", side_effect=OSError("fixture race")):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.read_secure_relative(REPO_ROOT, ASSIGNED_FILES[0], "fixture", 4096)

    def test_root_changed_from_0700_to_0777_before_descriptor_open_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rk001-root-open-race-") as root:
            root_path = Path(root)
            (root_path / "fixture.json").write_bytes(b"{}\n")
            os.chmod(str(root_path), 0o700)
            original_open = registry.os.open
            raced = [False]

            def open_after_mode_swap(path, flags, *args, **kwargs):
                if path == root_path.name and not raced[0]:
                    raced[0] = True
                    os.chmod(str(root_path), 0o777)
                return original_open(path, flags, *args, **kwargs)

            try:
                with mock.patch.object(
                    registry.os, "open", side_effect=open_after_mode_swap
                ):
                    with self.assertRaises(registry.ReviewerRegistryError):
                        registry.read_secure_relative(
                            root_path, "fixture.json", "race fixture", 1024
                        )
                self.assertTrue(raced[0])
            finally:
                os.chmod(str(root_path), 0o700)

    def test_root_mode_change_after_open_and_symlinked_ancestor_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rk001-root-replay-race-") as outer:
            outer_path = Path(outer)
            root_path = outer_path / "root"
            root_path.mkdir(mode=0o700)
            (root_path / "fixture.json").write_bytes(b"{}\n")
            original_read = registry._read_held_relative_pass

            def read_then_relax(context, label, cap):
                data = original_read(context, label, cap)
                os.chmod(str(root_path), 0o777)
                return data

            try:
                with mock.patch.object(
                    registry, "_read_held_relative_pass", side_effect=read_then_relax
                ):
                    with self.assertRaises(registry.ReviewerRegistryError):
                        registry.read_secure_relative(
                            root_path, "fixture.json", "replay fixture", 1024
                        )
            finally:
                os.chmod(str(root_path), 0o700)
            link_path = outer_path / "root-link"
            link_path.symlink_to(root_path.name)
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.read_secure_relative(
                    link_path, "fixture.json", "symlinked ancestor", 1024
                )

    def test_leaf_hardlink_and_mode_race_after_retained_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rk001-leaf-identity-race-") as root:
            root_path = Path(root)
            leaf = root_path / "fixture.json"
            alias = root_path / "fixture-hardlink.json"
            leaf.write_bytes(b"{}\n")
            original_read = registry._read_held_relative_pass
            raced = [False]

            def read_then_link_and_relax(context, label, cap):
                data = original_read(context, label, cap)
                if not raced[0]:
                    raced[0] = True
                    os.link(str(leaf), str(alias))
                    os.chmod(str(leaf), 0o666)
                return data

            with mock.patch.object(
                registry,
                "_read_held_relative_pass",
                side_effect=read_then_link_and_relax,
            ):
                with self.assertRaises(registry.ReviewerRegistryError):
                    registry.read_secure_relative(
                        root_path, leaf.name, "leaf race fixture", 1024
                    )
            self.assertTrue(raced[0])

    def test_candidate_preview_is_non_authorizing_pure_and_inclusive(self):
        candidate, evidence = self.fixture()
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        candidate_copy, evidence_copy = registry.validate_candidate(
            candidate, evidence_bytes
        )
        before = copy.deepcopy(candidate)
        candidate_copy["status"] = "revoked"
        evidence_copy["appointment_status"] = "revoked"
        with mock.patch.object(
            registry, "validate_candidate", wraps=registry.validate_candidate
        ) as full_validate:
            for packet, timestamp in (
                ("0001", "2026-08-02T00:00:00Z"),
                ("0219", "2027-08-02T00:00:00Z"),
                ("0100", "2027-01-01T00:00:00Z"),
            ):
                self.assertTrue(
                    registry.preview_candidate_activity(
                        candidate,
                        evidence_bytes,
                        candidate["reviewer"]["reviewer_identity"],
                        candidate["reviewer"]["ssh_fingerprint"],
                        packet,
                        timestamp,
                    )
                )
        self.assertEqual(full_validate.call_count, 3)
        self.assertEqual(candidate, before)
        self.assertEqual(candidate["status"], "active")
        self.assertEqual(evidence["appointment_status"], "active")

    def test_candidate_preview_returns_false_outside_identity_key_or_time(self):
        candidate, evidence = self.fixture()
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        queries = (
            ("other@example.invalid", self.reviewer_fingerprint, "0001", "2027-01-01T00:00:00Z"),
            ("reviewer@example.invalid", self.authority_fingerprint, "0001", "2027-01-01T00:00:00Z"),
            ("reviewer@example.invalid", self.reviewer_fingerprint, "0001", "2026-08-01T23:59:59Z"),
        )
        for query in queries:
            self.assertFalse(
                registry.preview_candidate_activity(
                    candidate, evidence_bytes, *query
                )
            )

    def test_candidate_preview_explicitly_skips_signed_revocation(self):
        candidate, evidence = self.fixture(status="revoked")
        self.assertFalse(
            registry.preview_candidate_activity(
                candidate,
                registry.canonical_json(evidence, newline=True),
                candidate["reviewer"]["reviewer_identity"],
                candidate["reviewer"]["ssh_fingerprint"],
                "0100",
                "2027-01-01T00:00:00Z",
            )
        )

    def test_candidate_preview_revalidates_and_rejects_forged_proofs(self):
        candidate, evidence = self.fixture()
        evidence_bytes = registry.canonical_json(evidence, newline=True)
        registry.validate_candidate(candidate, evidence_bytes)
        arguments = (
            candidate["reviewer"]["reviewer_identity"],
            candidate["reviewer"]["ssh_fingerprint"],
            "0100",
            "2027-01-01T00:00:00Z",
        )
        candidate["proof_of_key_possession"] = self.signature_record(
            self.authority_private,
            registry.appointment_signing_payload(candidate),
            registry.POSSESSION_NAMESPACE,
        )
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.preview_candidate_activity(
                candidate, evidence_bytes, *arguments
            )

        candidate, evidence = self.fixture()
        evidence["authority_proof"] = self.signature_record(
            self.reviewer_private,
            registry.evidence_signing_payload(evidence),
            registry.INDEPENDENCE_NAMESPACE,
        )
        evidence_bytes = self.bind_evidence(candidate, evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.preview_candidate_activity(
                candidate, evidence_bytes, *arguments
            )

    def test_authorization_reloads_exact_empty_authority_and_rejects_candidates(self):
        candidate, evidence = self.fixture()
        informational = registry.validate_candidate(
            candidate, registry.canonical_json(evidence, newline=True)
        )
        arguments = (
            candidate["reviewer"]["reviewer_identity"],
            candidate["reviewer"]["ssh_fingerprint"],
            "0100",
            "2027-01-01T00:00:00Z",
        )
        stale_snapshot, _campaign = registry.check_repository(REPO_ROOT)
        stale_snapshot["appointments"] = [
            {
                "appointment": candidate,
                "independence_evidence": evidence,
            }
        ]
        stale_snapshot["registration_status"] = "registered"
        self.assertIsNone(registry.find_active_appointment(REPO_ROOT, *arguments))
        for caller_supplied in (
            informational,
            candidate,
            [candidate],
            {"appointments": [candidate]},
            object(),
        ):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.find_active_appointment(caller_supplied, *arguments)

    def test_no_mint_or_python_secrecy_mechanism_can_feed_authorization(self):
        source = CHECKER.read_text(encoding="utf-8")
        lowered = source.lower()
        self.assertNotIn("hmac", lowered)
        self.assertNotIn("capability", lowered)
        self.assertNotIn("unforgeable", lowered)
        self.assertNotIn("_mint_validated", source)
        self.assertNotIn("_unseal_validated", source)
        self.assertFalse(hasattr(registry, "ValidatedAppointment"))
        self.assertFalse(hasattr(registry, "ValidatedProductionRegistry"))
        self.assertFalse(hasattr(registry, "_VALIDATION_TOKEN"))
        for name, value in vars(registry).items():
            if callable(value) and getattr(value, "__closure__", None):
                closure_values = tuple(cell.cell_contents for cell in value.__closure__)
                self.assertFalse(
                    any(type(item) is bytes and len(item) >= 16 for item in closure_values),
                    name,
                )

    def test_future_embedded_records_revalidate_both_proofs_and_status(self):
        active, active_evidence = self.fixture(status="active")
        revoked, revoked_evidence = self.fixture(status="revoked")
        active_copy, active_evidence_copy = (
            registry.validate_embedded_production_record(
                {
                    "appointment": active,
                    "independence_evidence": active_evidence,
                }
            )
        )
        revoked_copy, revoked_evidence_copy = (
            registry.validate_embedded_production_record(
                {
                    "appointment": revoked,
                    "independence_evidence": revoked_evidence,
                }
            )
        )
        self.assertEqual(active["appointment_id"], revoked["appointment_id"])
        self.assertEqual(active_copy["status"], "active")
        self.assertEqual(active_evidence_copy["appointment_status"], "active")
        self.assertEqual(revoked_copy["status"], "revoked")
        self.assertEqual(revoked_evidence_copy["appointment_status"], "revoked")
        forged_record = {
            "appointment": copy.deepcopy(active),
            "independence_evidence": copy.deepcopy(revoked_evidence),
        }
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_embedded_production_record(forged_record)

        wrong_possession, wrong_possession_evidence = self.fixture()
        wrong_possession["proof_of_key_possession"] = self.signature_record(
            self.authority_private,
            registry.appointment_signing_payload(wrong_possession),
            registry.POSSESSION_NAMESPACE,
        )
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_embedded_production_record(
                {
                    "appointment": wrong_possession,
                    "independence_evidence": wrong_possession_evidence,
                }
            )

        wrong_authority, wrong_authority_evidence = self.fixture()
        wrong_authority_evidence["authority_proof"] = self.signature_record(
            self.reviewer_private,
            registry.evidence_signing_payload(wrong_authority_evidence),
            registry.INDEPENDENCE_NAMESPACE,
        )
        self.bind_evidence(wrong_authority, wrong_authority_evidence)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.validate_embedded_production_record(
                {
                    "appointment": wrong_authority,
                    "independence_evidence": wrong_authority_evidence,
                }
            )

    def test_exact_authority_digest_governs_membership_not_valid_fixture_data(self):
        candidate, evidence = self.fixture()
        valid_record = {
            "appointment": candidate,
            "independence_evidence": evidence,
        }
        registry.validate_embedded_production_record(valid_record)
        forged_authority = copy.deepcopy(self.production_authority)
        forged_authority["appointments"] = [valid_record]
        forged_authority["registration_status"] = "registered"
        forged_bytes = registry.canonical_json(forged_authority, newline=True)
        original_read = registry.read_secure_relative

        def substitute_authority(root, relative, label, cap):
            if relative == registry.AUTHORITY_PATH.as_posix():
                return forged_bytes
            return original_read(root, relative, label, cap)

        with mock.patch.object(
            registry,
            "read_secure_relative",
            side_effect=substitute_authority,
        ):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.find_active_appointment(
                    REPO_ROOT,
                    candidate["reviewer"]["reviewer_identity"],
                    candidate["reviewer"]["ssh_fingerprint"],
                    "0100",
                    "2027-01-01T00:00:00Z",
                )

        same_size_mutation = self.production_bytes.replace(
            registry.REGISTRY_ID.encode("ascii"),
            registry.REGISTRY_ID.replace("ef58860e", "ff58860e").encode("ascii"),
            1,
        )
        self.assertEqual(len(same_size_mutation), registry.AUTHORITY_SIZE)

        def substitute_same_size(root, relative, label, cap):
            if relative == registry.AUTHORITY_PATH.as_posix():
                return same_size_mutation
            return original_read(root, relative, label, cap)

        with mock.patch.object(
            registry,
            "read_secure_relative",
            side_effect=substitute_same_size,
        ):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.find_active_appointment(
                    REPO_ROOT,
                    candidate["reviewer"]["reviewer_identity"],
                    candidate["reviewer"]["ssh_fingerprint"],
                    "0100",
                    "2027-01-01T00:00:00Z",
                )

    def test_stale_active_and_retagged_caller_objects_never_authorize(self):
        active, active_evidence = self.fixture(status="active")
        revoked, revoked_evidence = self.fixture(status="revoked")
        active_result = registry.validate_candidate(
            active, registry.canonical_json(active_evidence, newline=True)
        )
        revoked_result = registry.validate_candidate(
            revoked, registry.canonical_json(revoked_evidence, newline=True)
        )
        arguments = (
            active["reviewer"]["reviewer_identity"],
            active["reviewer"]["ssh_fingerprint"],
            "0100",
            "2027-01-01T00:00:00Z",
        )
        self.assertEqual(active["appointment_id"], revoked["appointment_id"])
        for stale_or_retagged in (
            active_result,
            revoked_result,
            {
                "source": "production-registry",
                "appointment": active_result[0],
                "independence_evidence": revoked_result[1],
            },
        ):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.find_active_appointment(stale_or_retagged, *arguments)
        self.assertIsNone(registry.find_active_appointment(REPO_ROOT, *arguments))

    def test_production_authorization_rejects_malformed_queries(self):
        candidate, _evidence = self.fixture()
        arguments = (
            candidate["reviewer"]["reviewer_identity"],
            candidate["reviewer"]["ssh_fingerprint"],
            "0100",
            "2027-01-01T00:00:00Z",
        )
        for values in (
            ("bad identity",) + arguments[1:],
            arguments[:1] + ("SHA256:wrong",) + arguments[2:],
            arguments[:1] + ("not-a-fingerprint",) + arguments[2:],
            arguments[:2] + ("0220",) + arguments[3:],
            arguments[:3] + ("not-a-time",),
        ):
            with self.assertRaises(registry.ReviewerRegistryError):
                registry.find_active_appointment(REPO_ROOT, *values)
        with self.assertRaises(registry.ReviewerRegistryError):
            registry.find_active_appointment(None, *arguments)

    def test_python_36_grammar_and_no_signing_or_private_key_material_in_checker(self):
        source = CHECKER.read_text(encoding="utf-8")
        ast.parse(source, filename=str(CHECKER), feature_version=(3, 6))
        self.assertNotIn('"-Y",\n            "sign"', source)
        self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", source)
        self.assertNotIn("write_text", source)
        self.assertEqual(
            set(ASSIGNED_FILES),
            {
                "host-kernel/rocky/evidence/rk001-license-reviewer-registry-ef58-v1.json",
                "scripts/rocky_kernel_license_reviewer_registry.py",
                "scripts/tests/test_rocky_kernel_license_reviewer_registry.py",
            },
        )


if __name__ == "__main__":
    unittest.main()
