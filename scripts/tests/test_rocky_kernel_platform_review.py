#!/usr/bin/env python3
"""Fail-closed tests for the historical dd6 platform evidence review."""

import ast
import copy
import hashlib
import io
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_platform_review as review  # noqa: E402


LIVE_ARTIFACT = Path(
    "/tmp/rk003-rk005-platform-evidence-31563271344-1.zip"
)


class RepositoryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.git_checked = review.check_repository(REPO_ROOT)
        cls.manifest_bytes = (REPO_ROOT / review.REVIEW_PATH).read_bytes()

    def test_review_is_canonical_byte_locked_and_no_credit(self):
        self.assertEqual(
            hashlib.sha256(self.manifest_bytes).hexdigest(),
            review.EXPECTED_REVIEW_SHA256,
        )
        self.assertEqual(
            self.manifest_bytes, review.canonical_json_bytes(self.manifest)
        )
        self.assertEqual(self.manifest["claims"], review.EXPECTED_CLAIMS)
        self.assertFalse(self.manifest["claims"]["credit_eligible"])
        self.assertFalse(self.manifest["claims"]["tracker_credit"])
        self.assertEqual(
            self.manifest["claims"]["gate_claims"],
            {"RK-003": False, "RK-005": False},
        )
        self.assertEqual(len(self.manifest["phase_blockers_at_capture"]), 7)

    def test_original_runtime_and_current_observation_are_distinct(self):
        artifact = self.manifest["source_artifact"]
        observation = self.manifest["current_head_blob_equivalence_observation"]
        self.assertEqual(
            artifact["github"]["runtime_head_sha"], review.RUNTIME_HEAD
        )
        self.assertEqual(observation["head_sha"], review.OBSERVED_HEAD)
        self.assertNotEqual(review.RUNTIME_HEAD, review.OBSERVED_HEAD)
        self.assertFalse(observation["runtime_identity_claimed"])
        self.assertFalse(self.manifest["claims"]["current_head_runtime_identity"])
        self.assertTrue(observation["all_bound_input_bytes_equal"])
        self.assertTrue(observation["all_bound_input_git_blobs_equal"])
        binding = self.manifest["current_repository_input_binding"]
        self.assertEqual(binding, review.EXPECTED_CURRENT_REPOSITORY_BINDING)
        self.assertEqual(binding["base_head_sha"], review.OBSERVED_HEAD)
        self.assertEqual(binding["current_override_count"], 2)
        self.assertFalse(binding["runtime_identity_claimed"])

    def test_artifact_and_full_zip_closure_are_exactly_pinned(self):
        artifact = self.manifest["source_artifact"]["artifact"]
        self.assertEqual(artifact["id"], 9128527159)
        self.assertEqual(artifact["size"], 193574223)
        self.assertEqual(artifact["sha256"], review.ARTIFACT_SHA256)
        closure = self.manifest["zip_closure"]
        self.assertEqual(closure, review.EXPECTED_ZIP_CLOSURE)
        self.assertEqual(closure["entry_count"], 166)
        self.assertEqual(
            [row["covered_entry_count"] for row in closure["checksum_manifests"]],
            [98, 66],
        )

    def test_exact_ten_runtime_inputs_and_current_tree_are_separately_bound(self):
        inputs = self.manifest["runtime_candidate"]["committed_inputs"]
        self.assertEqual(inputs, review.EXPECTED_INPUTS)
        self.assertEqual(len(inputs), 10)
        current = review.current_expected_inputs()
        self.assertEqual(len(current), 10)
        self.assertEqual(
            {row["path"] for row in review.CURRENT_INPUT_OVERRIDES},
            {
                "host-kernel/rocky/source-lock.json",
                "scripts/rocky_kernel_source_lock.py",
            },
        )
        self.assertNotEqual(current, inputs)
        review.validate_repository_inputs(REPO_ROOT)
        self.assertTrue(self.git_checked)

    def test_missing_published_base_fails_even_when_input_bytes_match(self):
        with tempfile.TemporaryDirectory(prefix="platform-review-shallow-") as text:
            root = Path(text)
            relative_paths = [review.REVIEW_PATH] + [
                Path(row["path"]) for row in review.current_expected_inputs()
            ]
            for relative in relative_paths:
                source = REPO_ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(target))

            resolved = str(root.resolve())
            subprocess.run(["git", "init", "-q", resolved], check=True)
            subprocess.run(
                [
                    "git", "-c", "safe.directory=" + resolved,
                    "-C", resolved, "add", ".",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "git", "-c", "safe.directory=" + resolved,
                    "-c", "user.name=platform-review-test",
                    "-c", "user.email=platform-review-test@example.invalid",
                    "-C", resolved, "commit", "-q", "-m", "shallow fixture",
                ],
                check=True,
            )

            self.assertFalse(review.git_commit_available(root, review.RUNTIME_HEAD))
            self.assertFalse(review.git_commit_available(root, review.OBSERVED_HEAD))
            self.assertFalse(
                review.git_commit_available(root, review.PUBLISHED_BASE_HEAD)
            )
            with self.assertRaisesRegex(review.ReviewError, "command failed"):
                review.check_repository(root)

    def test_connector_tree_port_is_exact_and_never_runtime_credit(self):
        port = self.manifest["connector_tree_port"]
        self.assertEqual(port, review.expected_connector_tree_port())
        self.assertEqual(port["binding_kind"], "exact-input-tree-port")
        self.assertEqual(port["published_base_head_sha"], review.PUBLISHED_BASE_HEAD)
        self.assertEqual(port["ported_input_count"], 10)
        self.assertEqual(port["changed_from_published_base_count"], 0)
        self.assertEqual(
            port["changed_from_published_base_paths"],
            review.PUBLISHED_BASE_CHANGED_PATHS,
        )
        self.assertEqual(port["unchanged_from_published_base_count"], 10)
        self.assertTrue(
            port["historical_review_preserved_by_exact_base_review_blob"]
        )
        self.assertFalse(
            port["historical_observation_fresh_git_reverification_claimed"]
        )
        self.assertFalse(
            port["historical_observation_git_object_required_for_tree_port"]
        )
        self.assertFalse(port["runtime_identity_claimed"])
        self.assertFalse(port["credit_eligible"])

    def test_connector_tree_port_published_base_review_anchor_is_exact(self):
        self.assertEqual(
            review.PUBLISHED_BASE_REVIEW,
            {
                "path": review.REVIEW_PATH.as_posix(),
                "size": 11208,
                "sha256": "14693e81bfa323eef3c509c8a075ebb2f7551e6bab0a4c2f03c22b6c0dbb7901",
                "git_blob_sha1": "6ea3fffd1983b38badee79098eb3e5c401b804ac",
            },
        )

    def test_connector_tree_port_changed_path_mutation_is_rejected(self):
        mutated = copy.deepcopy(self.manifest)
        port = mutated["connector_tree_port"]
        port["changed_from_published_base_count"] = 1
        port["changed_from_published_base_paths"] = [
            review.SOURCE_LOCK_PATH.as_posix()
        ]
        port["unchanged_from_published_base_count"] = 9
        with self.assertRaisesRegex(review.ReviewError, "connector tree port"):
            review.validate_review(mutated, self.manifest_bytes)

    def test_connector_tree_port_credit_and_identity_mutations_are_rejected(self):
        for key in ("runtime_identity_claimed", "credit_eligible"):
            mutated = copy.deepcopy(self.manifest)
            mutated["connector_tree_port"][key] = True
            with self.assertRaisesRegex(review.ReviewError, "connector tree port"):
                review.validate_review(mutated, self.manifest_bytes)

    def test_connector_parent_vector_rejects_merge_and_descendant(self):
        review.validate_connector_parent_vector([review.PUBLISHED_BASE_HEAD])
        for parents in (
            [review.PUBLISHED_BASE_HEAD, review.OBSERVED_HEAD],
            ["a" * 40],
        ):
            with self.assertRaisesRegex(review.ReviewError, "parent vector"):
                review.validate_connector_parent_vector(parents)

    def test_connector_input_rejects_dirty_index_mode_and_masked_head(self):
        expected = review.current_expected_inputs()[0]
        relative = expected["path"]
        data = (REPO_ROOT / relative).read_bytes()
        tree_entry = "100644 blob {}\t{}\0".format(
            expected["git_blob_sha1"], relative
        ).encode("utf-8")
        index_entry = "100644 {} 0\t{}\n".format(
            expected["git_blob_sha1"], relative
        ).encode("utf-8")
        review.validate_connector_input(
            expected, relative, data, data, tree_entry, index_entry
        )
        with self.assertRaisesRegex(review.ReviewError, "worktree input"):
            review.validate_connector_input(
                expected, relative, data + b"x", data, tree_entry, index_entry
            )
        with self.assertRaisesRegex(review.ReviewError, "index entry"):
            review.validate_connector_input(
                expected, relative, data, data, tree_entry, b""
            )
        with self.assertRaisesRegex(review.ReviewError, "HEAD tree entry"):
            review.validate_connector_input(
                expected,
                relative,
                data,
                data,
                tree_entry.replace(b"100644", b"120000"),
                index_entry,
            )

    def test_container_claim_boundary_is_not_escalated(self):
        container = self.manifest["runtime_candidate"]["container"]
        self.assertEqual(container["manifest_digest"], review.CONTAINER_MANIFEST)
        self.assertEqual(container["platform"], "linux/amd64")
        self.assertFalse(container["independent_in_container_oci_attestation"])
        self.assertFalse(self.manifest["claims"]["network_isolation_claimed"])
        self.assertIn("no independent", self.manifest["caveats"]["container_claim_boundary"])

    def test_verified_fact_counts_remain_bounded(self):
        facts = self.manifest["verified_facts"]
        self.assertEqual(facts["status"], "bounded-pass")
        self.assertEqual(facts["phase"], "repository-direct")
        self.assertEqual(
            (
                facts["bootstrap"]["base_package_count"],
                facts["bootstrap"]["added_package_count"],
                facts["bootstrap"]["after_package_count"],
            ),
            (138, 47, 185),
        )
        self.assertEqual(facts["signatures"]["rpm_archive_instance_count"], 67)
        self.assertEqual(facts["signatures"]["unique_rpm_count"], 65)
        self.assertEqual(facts["repositories"]["repomd_signature_count"], 3)
        self.assertEqual(facts["repositories"]["direct_archive_count"], 20)
        self.assertEqual(facts["build_requirements"]["rocky_effective_count"], 86)
        self.assertEqual(facts["build_requirements"]["reviewed_rocky_rust_count"], 3)
        self.assertEqual(facts["build_requirements"]["locked_direct_nevra_count"], 20)
        self.assertEqual(facts["build_requirements"]["resolution_root_count"], 109)
        self.assertFalse(facts["build_requirements"]["closure_complete"])

    def test_rehashed_review_mutation_is_rejected(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["claims"]["tracker_credit"] = True
        mutated_bytes = review.canonical_json_bytes(mutated)
        with self.assertRaisesRegex(review.ReviewError, "bytes changed"):
            review.validate_review(mutated, mutated_bytes)

    def test_semantic_credit_escalation_is_rejected_independent_of_byte_lock(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["claims"]["credit_eligible"] = True
        with self.assertRaisesRegex(review.ReviewError, "review claims"):
            review.validate_review(mutated, self.manifest_bytes)

    def test_runtime_identity_relabel_is_rejected(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["source_artifact"]["github"]["runtime_head_sha"] = review.OBSERVED_HEAD
        with self.assertRaisesRegex(review.ReviewError, "source artifact"):
            review.validate_review(mutated, self.manifest_bytes)

    def test_current_head_runtime_claim_is_rejected(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["current_head_blob_equivalence_observation"][
            "runtime_identity_claimed"
        ] = True
        with self.assertRaisesRegex(review.ReviewError, "blob-equivalence"):
            review.validate_review(mutated, self.manifest_bytes)

    def test_current_tree_runtime_claim_is_rejected(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["current_repository_input_binding"][
            "runtime_identity_claimed"
        ] = True
        with self.assertRaisesRegex(review.ReviewError, "bytes changed"):
            review.validate_review(mutated, review.canonical_json_bytes(mutated))

    def test_rehashed_current_source_lock_drift_is_rejected(self):
        mutated = copy.deepcopy(self.manifest)
        changed = (REPO_ROOT / review.SOURCE_LOCK_PATH).read_bytes() + b"\n"
        for row in mutated["current_repository_input_binding"]["current_overrides"]:
            if row["path"] == review.SOURCE_LOCK_PATH.as_posix():
                row["size"] = len(changed)
                row["sha256"] = review.sha256_bytes(changed)
                row["git_blob_sha1"] = review.git_blob_sha1(changed)
                break
        else:
            self.fail("current source-lock override is missing")
        with self.assertRaisesRegex(review.ReviewError, "bytes changed"):
            review.validate_review(mutated, review.canonical_json_bytes(mutated))

    def test_durable_archive_claim_is_rejected(self):
        mutated = copy.deepcopy(self.manifest)
        mutated["source_artifact"]["durable_archive"] = True
        with self.assertRaisesRegex(review.ReviewError, "source artifact"):
            review.validate_review(mutated, self.manifest_bytes)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(review.ReviewError, "duplicate JSON key"):
            review.strict_json_bytes(b'{"claims":{},"claims":{}}\n', "duplicate")

    def test_repository_input_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="platform-review-test-") as text:
            root = Path(text)
            for row in review.current_expected_inputs():
                source = REPO_ROOT / row["path"]
                target = root / row["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(target))
            target = root / review.current_expected_inputs()[0]["path"]
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(review.ReviewError, "size"):
                review.validate_repository_inputs(root)

    def test_current_source_lock_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="platform-review-lock-") as text:
            root = Path(text)
            for row in review.current_expected_inputs():
                source = REPO_ROOT / row["path"]
                target = root / row["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(target))
            target = root / review.SOURCE_LOCK_PATH
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(review.ReviewError, "size"):
                review.validate_repository_inputs(root)

    def test_checksum_manifest_rejects_reordering_and_traversal(self):
        digest_a = "a" * 64
        digest_b = "b" * 64
        with self.assertRaisesRegex(review.ReviewError, "sorted and unique"):
            review.parse_checksum_manifest(
                (digest_a + "  z\n" + digest_b + "  a\n").encode("ascii"),
                "unsorted",
            )
        with self.assertRaisesRegex(review.ReviewError, "normalized relative"):
            review.parse_checksum_manifest(
                (digest_a + "  ../escape\n").encode("ascii"), "traversal"
            )

    def test_zip_path_traversal_is_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory(prefix="platform-review-zip-") as text:
            path = Path(text) / "unsafe.zip"
            info = zipfile.ZipInfo("../escape")
            info.external_attr = (stat.S_IFREG | 0o400) << 16
            with zipfile.ZipFile(str(path), "w") as archive:
                archive.writestr(info, b"x")
            with zipfile.ZipFile(str(path), "r") as archive:
                with self.assertRaisesRegex(review.ReviewError, "normalized relative"):
                    review.validate_zip_infos(archive)

    def test_zip_duplicate_paths_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="platform-review-zip-") as text:
            path = Path(text) / "duplicate.zip"
            info = zipfile.ZipInfo("capture/file")
            info.external_attr = (stat.S_IFREG | 0o400) << 16
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(str(path), "w") as archive:
                    archive.writestr(info, b"a")
                    archive.writestr(info, b"b")
            with zipfile.ZipFile(str(path), "r") as archive:
                with self.assertRaisesRegex(review.ReviewError, "duplicate paths"):
                    review.validate_zip_infos(archive)

    def test_zip_symlink_entries_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="platform-review-zip-") as text:
            path = Path(text) / "symlink.zip"
            info = zipfile.ZipInfo("capture/link")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(str(path), "w") as archive:
                archive.writestr(info, b"target")
            with zipfile.ZipFile(str(path), "r") as archive:
                with self.assertRaisesRegex(review.ReviewError, "not a regular"):
                    review.validate_zip_infos(archive)

    def test_malformed_rpm_is_rejected(self):
        with self.assertRaisesRegex(review.ReviewError, "not an RPM"):
            review.rpm_signature_payload(b"not an rpm", "fake")

    def test_cli_check_succeeds(self):
        self.assertEqual(
            review.main(["--repo", str(REPO_ROOT), "--check"]), 0
        )

    def test_checker_and_tests_use_python_3_6_compatible_syntax(self):
        forbidden_fragments = (
            "from __future__ import " + "annotations",
            ".is_relative" + "_to(",
            ".remove" + "prefix(",
            ".remove" + "suffix(",
            "capture_" + "output=",
            "missing_" + "ok=",
            "dirs_exist_" + "ok=",
        )
        forbidden_patterns = (r"\b(?:list|dict|set|tuple)\[[^\]]", r"\s\|\sNone\b")
        for relative in (
            "scripts/rocky_kernel_platform_review.py",
            "scripts/tests/test_rocky_kernel_platform_review.py",
        ):
            path = REPO_ROOT / relative
            source = path.read_text(encoding="utf-8")
            if sys.version_info >= (3, 8):
                try:
                    tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
                except TypeError:
                    tree = ast.parse(source, filename=str(path), feature_version=6)
            else:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, source)
            for pattern in forbidden_patterns:
                self.assertNotRegex(source, pattern)

    @unittest.skipUnless(LIVE_ARTIFACT.is_file(), "pinned live artifact is unavailable")
    def test_live_pinned_artifact_when_available(self):
        summary = review.verify_artifact(LIVE_ARTIFACT, REPO_ROOT)
        self.assertEqual(
            summary,
            {
                "rpm_signature_instances": 67,
                "signed_primary_bindings": 65,
                "effective_buildrequires": 86,
                "resolution_roots": 109,
            },
        )


if __name__ == "__main__":
    unittest.main()
