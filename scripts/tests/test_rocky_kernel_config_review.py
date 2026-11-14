#!/usr/bin/env python3
"""Fail-closed tests for the bounded RK-005 config artifact review."""

from __future__ import print_function

import copy
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/rocky_kernel_config_review.py"
SPEC = importlib.util.spec_from_file_location("rocky_kernel_config_review", str(MODULE_PATH))
reviewer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reviewer)


class ConfigReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review_path = reviewer.discover_review(REPO_ROOT)
        cls.review = reviewer.load_review(cls.review_path)

    def test_checked_in_review_is_bounded_and_valid(self):
        validated = reviewer.validate_review_object(copy.deepcopy(self.review))
        self.assertEqual(validated["claims"]["gate_claims"], reviewer.EXPECTED_GATE_CLAIMS)
        self.assertFalse(validated["claims"]["credit_eligible"])
        self.assertFalse(validated["claims"]["tracker_credit"])

    def test_review_is_canonical_and_byte_locked(self):
        data = self.review_path.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), reviewer.REVIEW_SHA256)
        self.assertEqual(data, reviewer.canonical_json_bytes(self.review))
        with tempfile.TemporaryDirectory() as temporary:
            mutated = copy.deepcopy(self.review)
            mutated["source_artifact"]["artifact"]["id"] = 1
            path = Path(temporary) / "mutated.json"
            path.write_bytes(reviewer.canonical_json_bytes(mutated))
            with self.assertRaisesRegex(reviewer.ConfigReviewError, "manifest digest"):
                reviewer.load_review(path)

    def test_historical_review_rejects_current_active_patch_inputs(self):
        review = reviewer.validate_review_object(copy.deepcopy(self.review))
        self.assertNotEqual(review["runtime_candidate"]["head_sha"], "")
        self.assertFalse(
            review["current_repository_input_policy"]["runtime_identity_claimed"]
        )
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "current HEAD blob differs"):
            reviewer.validate_repository(REPO_ROOT, review)

    def test_every_gate_or_credit_promotion_is_rejected(self):
        scalar_claims = (
            "credit_eligible",
            "network_isolation_claimed",
            "offline_toolchain_proven",
            "production_build_proven",
            "runtime_identity_claimed",
            "tracker_credit",
        )
        for claim in scalar_claims:
            with self.subTest(claim=claim):
                mutated = copy.deepcopy(self.review)
                mutated["claims"][claim] = True
                with self.assertRaisesRegex(reviewer.ConfigReviewError, "must remain false"):
                    reviewer.validate_review_object(mutated)
        for gate in sorted(reviewer.EXPECTED_GATE_CLAIMS):
            with self.subTest(gate=gate):
                mutated = copy.deepcopy(self.review)
                mutated["claims"]["gate_claims"][gate] = True
                with self.assertRaisesRegex(reviewer.ConfigReviewError, "gate claims"):
                    reviewer.validate_review_object(mutated)

    def test_current_runtime_identity_promotion_is_rejected(self):
        mutated = copy.deepcopy(self.review)
        mutated["current_repository_input_policy"]["runtime_identity_claimed"] = True
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "current runtime claim"):
            reviewer.validate_review_object(mutated)

    def test_durable_archive_overclaim_is_rejected(self):
        mutated = copy.deepcopy(self.review)
        mutated["source_artifact"]["durable_archive"] = True
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "durable archive claim"):
            reviewer.validate_review_object(mutated)

    def test_bound_input_count_and_order_are_enforced(self):
        mutated = copy.deepcopy(self.review)
        mutated["current_repository_input_policy"]["bound_input_count"] -= 1
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "bound input count"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"].reverse()
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "committed input paths"):
            reviewer.validate_review_object(mutated)

    def test_runtime_and_artifact_head_must_match(self):
        mutated = copy.deepcopy(self.review)
        mutated["source_artifact"]["github"]["runtime_head_sha"] = "0" * 40
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "runtime head"):
            reviewer.validate_review_object(mutated)

    def test_review_id_and_artifact_name_bind_head_and_run(self):
        mutated = copy.deepcopy(self.review)
        mutated["review_id"] = "rk-005-config-resolution-review-deadbeef-v1"
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "review id"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["source_artifact"]["artifact"]["name"] = (
            "rk005-config-resolution-1-1"
        )
        mutated["source_artifact"]["artifact"]["archive_file_name"] = (
            "rk005-config-resolution-1-1.zip"
        )
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "artifact name"):
            reviewer.validate_review_object(mutated)

    def test_exact_run_artifact_head_tree_and_config_identities_are_pinned(self):
        mutations = (
            (("source_artifact", "artifact", "id"), 1),
            (("source_artifact", "artifact", "name"), "rk005-config-resolution-1-1"),
            (("source_artifact", "artifact", "size"), 1),
            (("source_artifact", "artifact", "sha256"), "0" * 64),
            (("source_artifact", "expires_at"), "2099-01-01T00:00:00Z"),
            (("source_artifact", "github", "job_id"), 1),
            (("source_artifact", "github", "run_attempt"), 2),
            (("source_artifact", "github", "run_id"), 1),
            (("source_artifact", "github", "runtime_head_sha"), "0" * 40),
            (("runtime_candidate", "head_sha"), "0" * 40),
            (("runtime_candidate", "tree_sha"), "0" * 40),
            (("verified_facts", "configurations", "resolved", "sha256"), "0" * 64),
        )
        for path, value in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                cursor = mutated
                for key in path[:-1]:
                    cursor = cursor[key]
                cursor[path[-1]] = value
                with self.assertRaises(reviewer.ConfigReviewError):
                    reviewer.validate_review_object(mutated)

    def test_boolean_ids_open_nested_claims_and_probe_omissions_are_rejected(self):
        for path in (
            ("source_artifact", "artifact", "id"),
            ("source_artifact", "github", "job_id"),
            ("source_artifact", "github", "run_id"),
            ("verified_facts", "delta", "environment_generated_change_count"),
        ):
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                cursor = mutated
                for key in path[:-1]:
                    cursor = cursor[key]
                cursor[path[-1]] = True
                with self.assertRaises(reviewer.ConfigReviewError):
                    reviewer.validate_review_object(mutated)

        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["artifact_state"]["production_build_proven"] = True
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "artifact state"):
            reviewer.validate_review_object(mutated)

        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["tool_probes"].pop("rustc")
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "reviewed tool probes"):
            reviewer.validate_review_object(mutated)

    def test_patch_count_and_duplicates_are_rejected(self):
        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["patch_authority"]["count"] = 22
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "patch authority count"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        patches = mutated["verified_facts"]["patch_authority"]["patches"]
        patches[-1]["path"] = patches[0]["path"]
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "duplicated"):
            reviewer.validate_review_object(mutated)

    def test_prerequisites_cannot_drop_production_config_or_authority_blockers(self):
        phrases = (
            "Durably archive",
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
            "llvm-devel",
            "baseline-to-control-to-resolved",
            "RK-003",
            self.review["verified_facts"]["configurations"]["resolved"]["sha256"],
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                mutated = copy.deepcopy(self.review)
                mutated["remaining_prerequisites"] = [
                    row for row in mutated["remaining_prerequisites"] if phrase not in row
                ]
                with self.assertRaises(reviewer.ConfigReviewError):
                    reviewer.validate_review_object(mutated)

    def test_review_id_and_schema_fail_closed(self):
        mutated = copy.deepcopy(self.review)
        mutated["review_id"] = "latest"
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "review id"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["schema_version"] = 2
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "review schema"):
            reviewer.validate_review_object(mutated)

    def test_safe_relative_paths_reject_ambiguous_or_escaping_names(self):
        unsafe = (
            "/absolute",
            "../escape",
            "a/../escape",
            "a//b",
            "a\\b",
            "./a",
            "a/./b",
            "a\x00b",
            "",
        )
        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaises(reviewer.ConfigReviewError):
                    reviewer.safe_relative_path(value, "fixture")
        self.assertEqual(reviewer.safe_relative_path("capture/file", "fixture"), "capture/file")

    def test_repository_file_rejects_symlinked_ancestors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            normal = root / "normal"
            normal.write_bytes(b"bound\n")
            self.assertEqual(
                reviewer.repository_file(root, "normal", "fixture"), normal
            )
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (outside / "input").write_bytes(b"bound\n")
            os.symlink(str(outside), str(root / "linked"))
            with self.assertRaisesRegex(
                reviewer.ConfigReviewError,
                "escapes the repository|traverses a symlink",
            ):
                reviewer.repository_file(root, "linked/input", "fixture")

    def test_duplicate_json_keys_and_noncanonical_artifact_json_are_rejected(self):
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "duplicate JSON key"):
            reviewer.read_json_bytes(b'{"a":1,"a":2}\n', "fixture")
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "not canonical"):
            reviewer.read_json_bytes(b'{ "a": 1 }\n', "fixture", require_canonical=True)
        self.assertEqual(
            reviewer.read_json_bytes(b'{"a":1}\n', "fixture", require_canonical=True),
            {"a": 1},
        )

    def test_sha256sums_parser_requires_exact_order_and_unique_paths(self):
        digest = "0" * 64
        good = "".join(
            "{}  {}\n".format(digest, name)
            for name in reviewer.EXPECTED_CHECKSUM_NAMES
        ).encode("ascii")
        parsed = reviewer.parse_sha256sums(good)
        self.assertEqual(tuple(parsed), reviewer.EXPECTED_CHECKSUM_NAMES)
        duplicated = good + ("{}  {}\n".format(digest, reviewer.EXPECTED_CHECKSUM_NAMES[0])).encode(
            "ascii"
        )
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "duplicate"):
            reviewer.parse_sha256sums(duplicated)
        reversed_rows = b"".join(reversed(good.splitlines(keepends=True)))
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "checksum paths"):
            reviewer.parse_sha256sums(reversed_rows)

    def test_config_parser_and_semantic_delta_are_fail_closed(self):
        before = reviewer.parse_config(
            b"# CONFIG_RUST is not set\nCONFIG_MODVERSIONS=y\nCONFIG_WERROR=y\n",
            "before",
        )
        after = reviewer.parse_config(
            b"CONFIG_RUST=y\n# CONFIG_MODVERSIONS is not set\nCONFIG_WERROR=y\n",
            "after",
        )
        self.assertEqual(
            reviewer.changed_symbols(before, after), reviewer.EXPECTED_REQUESTED_CHANGES
        )
        self.assertEqual(reviewer.semantic_config_value("<absent>"), "n")
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "duplicates"):
            reviewer.parse_config(b"CONFIG_RUST=y\nCONFIG_RUST=n\n", "duplicate")
        with self.assertRaisesRegex(reviewer.ConfigReviewError, "contains no"):
            reviewer.parse_config(b"# ordinary comment\n", "empty")

    def test_zip_record_builder_rejects_unsafe_and_nonregular_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            good_path = Path(temporary) / "good.zip"
            with zipfile.ZipFile(str(good_path), "w", compression=zipfile.ZIP_STORED) as stream:
                info = zipfile.ZipInfo("capture/file")
                info.external_attr = (stat.S_IFREG | 0o400) << 16
                stream.writestr(info, b"data")
            with zipfile.ZipFile(str(good_path), "r") as stream:
                rows = reviewer.zip_entry_records(stream)
            self.assertEqual(rows[0]["path"], "capture/file")
            self.assertEqual(rows[0]["compression_method"], 0)

            unsafe_path = Path(temporary) / "unsafe.zip"
            with zipfile.ZipFile(str(unsafe_path), "w") as stream:
                info = zipfile.ZipInfo("../escape")
                info.external_attr = (stat.S_IFREG | 0o400) << 16
                stream.writestr(info, b"data")
            with zipfile.ZipFile(str(unsafe_path), "r") as stream:
                with self.assertRaises(reviewer.ConfigReviewError):
                    reviewer.zip_entry_records(stream)

            symlink_path = Path(temporary) / "symlink.zip"
            with zipfile.ZipFile(str(symlink_path), "w") as stream:
                info = zipfile.ZipInfo("capture/link")
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                stream.writestr(info, b"target")
            with zipfile.ZipFile(str(symlink_path), "r") as stream:
                with self.assertRaisesRegex(reviewer.ConfigReviewError, "not a regular"):
                    reviewer.zip_entry_records(stream)

    def test_zip_duplicate_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.zip"
            with zipfile.ZipFile(str(path), "w") as stream:
                for data in (b"first", b"second"):
                    info = zipfile.ZipInfo("capture/file")
                    info.external_attr = (stat.S_IFREG | 0o400) << 16
                    stream.writestr(info, data)
            with zipfile.ZipFile(str(path), "r") as stream:
                with self.assertRaisesRegex(reviewer.ConfigReviewError, "duplicate"):
                    reviewer.zip_entry_records(stream)

    def test_cli_check_fails_closed_for_historical_input_binding(self):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "--repo",
                str(REPO_ROOT),
                "--check",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual("", completed.stdout.decode("utf-8"))
        self.assertIn("current HEAD blob differs", completed.stderr.decode("utf-8"))

    def test_exact_artifact_when_supplied(self):
        artifact = os.environ.get("MCKERNEL_RK005_CONFIG_ARTIFACT")
        if not artifact:
            self.skipTest("MCKERNEL_RK005_CONFIG_ARTIFACT is not set")
        review = reviewer.validate_review_object(copy.deepcopy(self.review))
        reviewer.validate_repository(REPO_ROOT, review)
        result = reviewer.verify_artifact(Path(artifact), review)
        self.assertEqual(
            result["artifact_sha256"],
            review["source_artifact"]["artifact"]["sha256"],
        )
        self.assertEqual(
            result["resolved_config_sha256"],
            review["verified_facts"]["configurations"]["resolved"]["sha256"],
        )
        with zipfile.ZipFile(artifact, "r") as stream:
            environment = reviewer.read_json_bytes(
                stream.read("capture/environment.json"),
                "environment fixture",
                require_canonical=True,
            )
        identity = {
            "head_sha": reviewer.RUNTIME_HEAD_SHA,
            "repository": reviewer.GITHUB_REPOSITORY,
            "run_attempt": reviewer.GITHUB_RUN_ATTEMPT,
            "run_id": reviewer.GITHUB_RUN_ID,
        }
        reviewer.verify_environment_document(environment, review, identity)
        for label, mutate in (
            (
                "missing derived probe",
                lambda value: value["probes"].pop("derived"),
            ),
            (
                "missing rustc probe",
                lambda value: value["probes"].pop("rustc"),
            ),
            (
                "boolean derived version",
                lambda value: value["probes"]["derived"].__setitem__(
                    "rustc_version", True
                ),
            ),
            (
                "open fixed environment",
                lambda value: value["fixed_environment"].__setitem__(
                    "UNREVIEWED", "1"
                ),
            ),
        ):
            with self.subTest(label=label):
                mutated = copy.deepcopy(environment)
                mutate(mutated)
                with self.assertRaises(reviewer.ConfigReviewError):
                    reviewer.verify_environment_document(mutated, review, identity)


if __name__ == "__main__":
    unittest.main()
