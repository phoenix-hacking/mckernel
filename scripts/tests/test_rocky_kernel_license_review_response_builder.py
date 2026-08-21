#!/usr/bin/env python3
"""Adversarial tests for the no-key-custody RK-001 response builder."""

from __future__ import print_function

import ast
import copy
import hashlib
import io
import json
import os
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS))

import rocky_kernel_license_review_response_builder as builder


AUTHORITY = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/"
    "rk001-license-review-response-builder-ef58-v1.json"
)
ASSIGNED_FILES = (
    "host-kernel/rocky/evidence/rk001-license-review-response-builder-ef58-v1.json",
    "scripts/rocky_kernel_license_review_response_builder.py",
    "scripts/tests/test_rocky_kernel_license_review_response_builder.py",
)


def sign_bytes(private_key, data, namespace):
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


def make_unit(response_module, group_id, content_sha, content_size):
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
        "spdx_expression": "GPL-2.0-only",
        "unresolved_reasons": ["independent-review-required"],
    }
    payload = {
        "basis": "exact-spdx-machine-classification-needs-independent-review",
        "candidate_directory_signal_id": None,
        "capture_review_status": "captured-unreviewed",
        "context_group_id": "context:" + "2" * 64,
        "decision": "machine-classified-exact-spdx",
        "evidence": evidence,
        "exact_content_group_id": group_id,
        "reason_cluster_id": "reason:" + "3" * 64,
        "review_state": "independent-review-required",
    }
    unit = dict(payload)
    unit["unit_id"] = response_module.stable_id("review-unit", payload)
    return unit


class ResponseBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = builder.load_authority(REPO_ROOT, AUTHORITY)
        cls.dependencies = builder.load_dependencies(REPO_ROOT, cls.authority)
        cls.response = cls.dependencies["response"]
        cls.production = cls.dependencies["response_authority"]
        cls.key_root = tempfile.TemporaryDirectory(prefix="rk001-builder-key-")
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
        public_parts = cls.private_key.with_suffix(".pub").read_text(
            encoding="ascii"
        ).strip().split()
        cls.public_key = " ".join(public_parts[:2])
        cls.fingerprint = cls.response._public_key_fingerprint(
            cls.public_key, "ssh-ed25519"
        )
        cls.registry = copy.deepcopy(cls.production)
        cls.registry["reviewer_authority_policy"] = {
            "independence_registration_required": True,
            "registered_reviewers": [
                {
                    "authority_id": "test-only-reviewer-appointment-v1",
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
        cls.response.validate_authority(copy.deepcopy(cls.registry))
        cls.reviewer = builder.active_appointment(
            cls.response,
            cls.registry,
            "test-only-reviewer-appointment-v1",
            "test-reviewer@example.invalid",
            "0002",
            "2026-08-19T12:00:00Z",
        )
        content = b"machine-classified fixture content\n"
        content_sha = hashlib.sha256(content).hexdigest()
        identity = {
            "entry_type": "regular",
            "sha256": content_sha,
            "size": len(content),
        }
        group_id = cls.response.stable_id("exact-content", identity)
        cls.groups = [
            {
                "decision_class": "machine-classified-exact-spdx",
                "group_id": group_id,
                "identity": identity,
                "path_count": 1,
                "path_set_sha256": "5" * 64,
                "review_state": "independent-review-required",
            }
        ]
        cls.units = [make_unit(cls.response, group_id, content_sha, len(content))]
        cls.campaign_sha = cls.authority["inputs"]["campaign_authority"]["sha256"]

    @classmethod
    def tearDownClass(cls):
        cls.key_root.cleanup()

    def template(self):
        return builder.emit_template_data(
            self.authority,
            self.response,
            self.registry,
            copy.deepcopy(self.groups),
            copy.deepcopy(self.units),
            "0002",
            copy.deepcopy(self.reviewer),
            "2026-08-19T12:00:00Z",
            self.campaign_sha,
        )

    def authored_draft(self):
        files = self.template()
        root = self.response.read_json_bytes(
            files["template-root.json"], "template root", canonical=True
        )
        root["reviewer_attestations"] = {
            "all_units_individually_reviewed": True,
            "archive_expansion_complete": False,
            "independent_from_capture": True,
        }
        files["template-root.json"] = self.response.canonical_json(root, newline=True)
        findings = self.response.parse_jsonl(
            files["content-findings.jsonl"], "template findings", 10
        )
        findings[0]["conclusion"] = "unresolved"
        findings[0]["spdx_expression_or_unresolved"] = "unresolved"
        files["content-findings.jsonl"] = self.response.canonical_stream(findings)
        decisions = self.response.parse_jsonl(
            files["unit-decisions.jsonl"], "template decisions", 10
        )
        for key in (
            "authorship_status",
            "license_status",
            "provenance_status",
            "redistribution_status",
            "resolved_or_unresolved",
        ):
            decisions[0][key] = "unresolved"
        files["unit-decisions.jsonl"] = self.response.canonical_stream(decisions)
        return files

    def prepare(self, files=None):
        return builder.prepare_signing_data(
            self.authority,
            self.response,
            self.registry,
            copy.deepcopy(self.groups),
            copy.deepcopy(self.units),
            "0002",
            copy.deepcopy(self.reviewer),
            "2026-08-19T12:00:00Z",
            self.campaign_sha,
            self.authored_draft() if files is None else files,
        )

    def test_exact_three_file_scope_and_python36_grammar(self):
        for relative in ASSIGNED_FILES:
            self.assertTrue((REPO_ROOT / relative).is_file(), relative)
        for relative in ASSIGNED_FILES[1:]:
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

    def test_authority_is_canonical_frozen_strict_and_all_claims_false(self):
        data = AUTHORITY.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), builder.AUTHORITY_SHA256)
        value = builder.read_json_bytes(data, "builder authority", canonical=True)
        builder.validate_authority(copy.deepcopy(value))
        self.assertTrue(value["claims"])
        self.assertTrue(all(item is False for item in value["claims"].values()))
        self.assertEqual(value["gate"], builder.EXPECTED_GATE)
        for key, record in value["inputs"].items():
            bound = REPO_ROOT / record["path"]
            self.assertEqual(len(bound.read_bytes()), record["size"], key)
            self.assertEqual(hashlib.sha256(bound.read_bytes()).hexdigest(), record["sha256"], key)

    def test_check_reports_empty_production_registry_and_no_credit(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(builder.main(["--check", "--repo", str(REPO_ROOT)]), 0)
        output = stdout.getvalue()
        self.assertIn("reviewers=0", output)
        self.assertIn("appointment=false", output)
        self.assertIn("key_custody=false", output)
        self.assertIn("points=0", output)
        self.assertIn("credit=false", output)

    def test_parser_has_no_private_key_argument_and_source_never_signs(self):
        source = (REPO_ROOT / ASSIGNED_FILES[1]).read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("ssh-keygen", source)
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                builder.parser(["--emit-template", "--private-key", "forbidden"])

    def test_production_command_line_modes_block_before_artifact_access(self):
        with tempfile.TemporaryDirectory(prefix="rk001-builder-block-") as directory:
            output = Path(directory) / "must-not-exist"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                status = builder.main(
                    [
                        "--emit-template",
                        "--repo",
                        str(REPO_ROOT),
                        "--artifact",
                        str(Path(directory) / "absent.zip"),
                        "--packet-id",
                        "0002",
                        "--packet-dir",
                        str(Path(directory) / "absent-packet"),
                        "--reviewer-authority-id",
                        "self-asserted",
                        "--reviewer-identity",
                        "self@example.invalid",
                        "--review-completed-at",
                        "2026-08-19T12:00:00Z",
                        "--output-dir",
                        str(output),
                    ]
                )
            self.assertEqual(status, 1)
            self.assertIn("no active production reviewer appointment", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_registry_injection_is_callable_validated_and_reviewer_only(self):
        loaded = builder.load_registry(
            self.response,
            self.production,
            registry_loader=lambda unused: copy.deepcopy(self.registry),
        )
        self.assertEqual(
            loaded["reviewer_authority_policy"]["registration_status"], "registered"
        )
        with self.assertRaises(builder.ResponseBuilderError):
            builder.load_registry(self.response, self.production, registry_loader={})

        def mutate_non_registry(unused):
            value = copy.deepcopy(self.registry)
            value["remaining_blockers"] = ["injected unrelated policy"]
            return value

        with self.assertRaises(builder.ResponseBuilderError):
            builder.load_registry(
                self.response, self.production, registry_loader=mutate_non_registry
            )

    def test_registry_loader_cannot_mutate_aliased_production_baseline(self):
        production = copy.deepcopy(self.production)

        def mutate_alias(unused):
            production["remaining_blockers"] = ["alias-mutated policy"]
            value = copy.deepcopy(self.registry)
            value["remaining_blockers"] = ["alias-mutated policy"]
            return value

        with self.assertRaises(builder.ResponseBuilderError):
            builder.load_registry(
                self.response, production, registry_loader=mutate_alias
            )

    def test_appointment_scope_and_time_are_enforced(self):
        with self.assertRaises(builder.ResponseBuilderError):
            builder.active_appointment(
                self.response,
                self.registry,
                self.reviewer["authority_id"],
                self.reviewer["reviewer_identity"],
                "0002",
                "2028-01-01T00:00:00Z",
            )
        with self.assertRaises(builder.ResponseBuilderError):
            builder.active_appointment(
                self.response,
                self.registry,
                "self-asserted",
                self.reviewer["reviewer_identity"],
                "0002",
                "2026-08-19T12:00:00Z",
            )

    def test_template_contains_null_decisions_not_machine_conclusions(self):
        files = self.template()
        findings = self.response.parse_jsonl(files["content-findings.jsonl"], "findings", 10)
        decisions = self.response.parse_jsonl(files["unit-decisions.jsonl"], "decisions", 10)
        self.assertIsNone(findings[0]["conclusion"])
        self.assertIsNone(findings[0]["spdx_expression_or_unresolved"])
        for key in (
            "authorship_status",
            "license_status",
            "provenance_status",
            "redistribution_status",
            "resolved_or_unresolved",
        ):
            self.assertIsNone(decisions[0][key])
        self.assertNotIn(b"GPL-2.0-only", files["content-findings.jsonl"])
        root = self.response.read_json_bytes(
            files["template-root.json"], "template root", canonical=True
        )
        self.assertTrue(all(value is False for value in root["claims"].values()))
        self.assertTrue(
            all(value is None for value in root["reviewer_attestations"].values())
        )

    def test_template_api_itself_rejects_unappointed_reviewer(self):
        with self.assertRaises(builder.ResponseBuilderError):
            builder.emit_template_data(
                self.authority,
                self.response,
                self.production,
                copy.deepcopy(self.groups),
                copy.deepcopy(self.units),
                "0002",
                copy.deepcopy(self.reviewer),
                "2026-08-19T12:00:00Z",
                self.campaign_sha,
            )

    def test_unedited_template_cannot_be_prepared(self):
        with self.assertRaises(builder.ResponseBuilderError):
            self.prepare(self.template())

    def test_prepare_derives_ids_and_root_but_does_not_sign(self):
        files = self.prepare()
        self.assertEqual(
            {name for name in files if not name.startswith("support/")},
            builder.PREPARED_TOP_LEVEL,
        )
        self.assertNotIn("response-root.sig", files)
        self.assertNotIn("SHA256SUMS", files)
        root = self.response.read_json_bytes(
            files["response-root.json"], "prepared root", canonical=True
        )
        decisions = self.response.parse_jsonl(
            files["unit-decisions.jsonl"], "prepared decisions", 10
        )
        findings = self.response.parse_jsonl(
            files["content-findings.jsonl"], "prepared findings", 10
        )
        self.assertTrue(root["signed_response_root"].startswith("rk001-response-root:"))
        self.assertEqual(decisions[0]["signed_response_root"], root["signed_response_root"])
        self.assertTrue(findings[0]["content_finding_id"].startswith("content-finding:"))
        self.assertEqual(root["attestations"]["credit_eligible"], False)
        self.assertEqual(root["attestations"]["tracker_credit"], False)

    def test_prepare_rejects_machine_status_autofill_and_false_attestation(self):
        files = self.authored_draft()
        decisions = self.response.parse_jsonl(
            files["unit-decisions.jsonl"], "draft decisions", 10
        )
        decisions[0]["license_status"] = "machine-classified-exact-spdx"
        files["unit-decisions.jsonl"] = self.response.canonical_stream(decisions)
        with self.assertRaises(builder.ResponseBuilderError):
            self.prepare(files)
        files = self.authored_draft()
        root = self.response.read_json_bytes(
            files["template-root.json"], "draft root", canonical=True
        )
        root["reviewer_attestations"]["independent_from_capture"] = False
        files["template-root.json"] = self.response.canonical_json(root, newline=True)
        with self.assertRaises(builder.ResponseBuilderError):
            self.prepare(files)

    def test_external_signature_finalizes_but_never_awards_credit(self):
        prepared = self.prepare()
        signature = sign_bytes(
            self.private_key,
            prepared["response-root.json"],
            self.response.SIGNATURE_NAMESPACE,
        )
        files, result = builder.finalize_data(
            self.response,
            self.registry,
            copy.deepcopy(self.groups),
            copy.deepcopy(self.units),
            "0002",
            self.campaign_sha,
            prepared,
            signature,
        )
        self.assertIn("response-root.sig", files)
        self.assertIn("SHA256SUMS", files)
        self.assertTrue(result["signature_valid"])
        self.assertFalse(result["campaign_complete"])
        self.assertFalse(result["credit_eligible"])
        self.assertFalse(result["durable_archive"])
        self.assertFalse(result["tracker_credit"])
        self.assertEqual(result["points_awarded"], 0)

    def test_finalize_rejects_wrong_or_empty_external_signature(self):
        prepared = self.prepare()
        for signature in (b"", b"not-an-sshsig\n"):
            with self.assertRaises(builder.ResponseBuilderError):
                builder.finalize_data(
                    self.response,
                    self.registry,
                    copy.deepcopy(self.groups),
                    copy.deepcopy(self.units),
                    "0002",
                    self.campaign_sha,
                    prepared,
                    signature,
                )

    def test_finalize_rejects_outer_packet_id_mismatch(self):
        prepared = self.prepare()
        signature = sign_bytes(
            self.private_key,
            prepared["response-root.json"],
            self.response.SIGNATURE_NAMESPACE,
        )
        with self.assertRaises(builder.ResponseBuilderError):
            builder.finalize_data(
                self.response,
                self.registry,
                copy.deepcopy(self.groups),
                copy.deepcopy(self.units),
                "0003",
                self.campaign_sha,
                prepared,
                signature,
            )

    def test_atomic_publication_is_read_only_unique_and_round_trips(self):
        files = self.template()
        with tempfile.TemporaryDirectory(prefix="rk001-builder-output-") as directory:
            output = Path(directory) / "template"
            builder.atomic_publish_tree(self.response, output, files)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o555)
            for path in output.iterdir():
                if path.is_file():
                    info = path.stat()
                    self.assertEqual(stat.S_IMODE(info.st_mode), 0o444)
                    self.assertEqual(info.st_nlink, 1)
            retained = builder.read_exact_tree(
                self.response, output, builder.TEMPLATE_TOP_LEVEL, "test template"
            )
            self.assertEqual(retained, files)
            with self.assertRaises(builder.ResponseBuilderError):
                builder.atomic_publish_tree(self.response, output, files)

    def test_exact_tree_routes_root_and_stream_byte_caps(self):
        files = self.template()
        with tempfile.TemporaryDirectory(prefix="rk001-builder-caps-") as directory:
            output = Path(directory) / "template"
            builder.atomic_publish_tree(self.response, output, files)
            observed = {}
            original_read = self.response._read_member

            def tracked_read(member, cap):
                observed[member["name"]] = cap
                return original_read(member, cap)

            with mock.patch.object(
                self.response, "_read_member", side_effect=tracked_read
            ):
                builder.read_exact_tree(
                    self.response, output, builder.TEMPLATE_TOP_LEVEL, "capped template"
                )
            self.assertEqual(
                observed["template-root.json"], self.response.MAX_ROOT_BYTES
            )
            self.assertEqual(
                observed["unit-decisions.jsonl"], self.response.MAX_STREAM_BYTES
            )

    def test_reader_rejects_symlink_and_hardlink_members(self):
        files = self.template()
        with tempfile.TemporaryDirectory(prefix="rk001-builder-links-") as directory:
            root = Path(directory)
            output = root / "template"
            builder.atomic_publish_tree(self.response, output, files)
            victim = output / "content-findings.jsonl"
            output_mode = output.stat().st_mode & 0o7777
            victim_mode = victim.stat().st_mode & 0o7777
            original = victim.read_bytes()
            try:
                output.chmod(output_mode | 0o200)
                victim.chmod(victim_mode | 0o200)
                victim.unlink()
                victim.symlink_to(output / "unit-decisions.jsonl")
                output.chmod(output_mode)
                with self.assertRaises(builder.ResponseBuilderError):
                    builder.read_exact_tree(
                        self.response, output, builder.TEMPLATE_TOP_LEVEL,
                        "symlink template",
                    )

                output.chmod(output_mode | 0o200)
                victim.unlink()
                victim.write_bytes(original)
                victim.chmod(victim_mode)
                hardlink = root / "second-link"
                os.link(str(victim), str(hardlink))
                output.chmod(output_mode)
                with self.assertRaises(builder.ResponseBuilderError):
                    builder.read_exact_tree(
                        self.response, output, builder.TEMPLATE_TOP_LEVEL,
                        "hardlink template",
                    )
            finally:
                if victim.exists() and not victim.is_symlink():
                    victim.chmod(victim_mode)
                output.chmod(output_mode)

    def test_atomic_publication_rejects_symlink_target_and_untrusted_parent(self):
        files = self.template()
        with tempfile.TemporaryDirectory(prefix="rk001-builder-target-") as directory:
            root = Path(directory)
            destination = root / "destination"
            destination.mkdir()
            target = root / "target"
            target.symlink_to(destination, target_is_directory=True)
            with self.assertRaises(builder.ResponseBuilderError):
                builder.atomic_publish_tree(self.response, target, files)
            open_parent = root / "open-parent"
            open_parent.mkdir(mode=0o777)
            open_parent.chmod(0o777)
            with self.assertRaises(builder.ResponseBuilderError):
                builder.atomic_publish_tree(
                    self.response, open_parent / "template", files
                )

    def test_publication_replays_and_retracts_pre_rename_byte_race(self):
        files = self.template()
        original_rename = builder._rename_directory_noreplace
        with tempfile.TemporaryDirectory(prefix="rk001-builder-byte-race-") as directory:
            root = Path(directory)
            output = root / "template"

            def raced_rename(parent_fd, source_name, target_name):
                if source_name.startswith(".rk001-builder-"):
                    victim = root / source_name / "content-findings.jsonl"
                    victim.chmod(0o644)
                    victim.write_bytes(b"tampered-after-final-preflight\n")
                    victim.chmod(0o444)
                return original_rename(parent_fd, source_name, target_name)

            with mock.patch.object(
                builder, "_rename_directory_noreplace", side_effect=raced_rename
            ):
                with self.assertRaises(builder.ResponseBuilderError):
                    builder.atomic_publish_tree(self.response, output, files)
            self.assertFalse(output.exists())

    def test_publication_replays_and_retracts_pre_rename_hardlink_race(self):
        files = self.template()
        original_rename = builder._rename_directory_noreplace
        with tempfile.TemporaryDirectory(prefix="rk001-builder-link-race-") as directory:
            root = Path(directory)
            output = root / "template"
            retained = root / "attacker-retained-link"

            def raced_rename(parent_fd, source_name, target_name):
                if source_name.startswith(".rk001-builder-"):
                    os.link(
                        str(root / source_name / "unit-decisions.jsonl"),
                        str(retained),
                    )
                return original_rename(parent_fd, source_name, target_name)

            with mock.patch.object(
                builder, "_rename_directory_noreplace", side_effect=raced_rename
            ):
                with self.assertRaises(builder.ResponseBuilderError):
                    builder.atomic_publish_tree(self.response, output, files)
            self.assertFalse(output.exists())
            self.assertTrue(retained.is_file())

    def test_duplicate_json_and_authority_mutations_fail_closed(self):
        with self.assertRaises(builder.ResponseBuilderError):
            builder.read_json_bytes(b'{"schema_version":1,"schema_version":1}\n', "duplicate")
        for mutation in (
            lambda value: value["claims"].update({"credit_eligible": True}),
            lambda value: value["gate"].update({"points_awarded": 1}),
            lambda value: value["key_policy"].update({"private_key_reads": True}),
            lambda value: value["template_policy"].update(
                {"machine_classification_auto_accepted": True}
            ),
            lambda value: value["inputs"]["response_checker"].update(
                {"sha256": "0" * 64}
            ),
        ):
            value = copy.deepcopy(self.authority)
            mutation(value)
            with self.assertRaises(builder.ResponseBuilderError):
                builder.validate_authority(value)


if __name__ == "__main__":
    unittest.main()
