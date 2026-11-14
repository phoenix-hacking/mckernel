#!/usr/bin/env python3
"""Fail-closed tests for committed RK-001 source evidence review."""

from __future__ import print_function

import copy
import json
import os
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import rocky_kernel_source_review as review  # noqa: E402


def scalar_leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            for result in scalar_leaves(child, path + (key,)):
                yield result
    elif isinstance(value, list):
        for index, child in enumerate(value):
            for result in scalar_leaves(child, path + (index,)):
                yield result
    else:
        yield path, value


def replace(value, path, replacement):
    target = value
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement


def changed(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return value + "-mutated"
    if value is None:
        return "not-null"
    raise TypeError("unsupported scalar: {0!r}".format(value))


class SourceEvidenceReviewTests(unittest.TestCase):
    @staticmethod
    def load(path):
        with open(path, "r") as stream:
            return json.load(stream)

    @staticmethod
    def write_text(path, value):
        with open(path, "w") as stream:
            stream.write(value)

    @staticmethod
    def write_bytes(path, value):
        with open(path, "wb") as stream:
            stream.write(value)

    def test_committed_capture_is_semantically_accepted_without_gate_credit(self):
        result = review.check(REPO_ROOT)
        self.assertFalse(result["gate_claim"])
        self.assertEqual(result["workflow"]["run_id"], 31563766469)
        self.assertEqual(result["artifact"]["id"], 9128694499)

    def test_cli_check_passes(self):
        self.assertEqual(review.main(["--repo", REPO_ROOT, "--check"]), 0)

    def test_every_capture_record_mutation_fails(self):
        manifest_path = os.path.join(REPO_ROOT, review.REVIEW)
        manifest = self.load(manifest_path)
        for evidence_id, item in manifest["files"].items():
            with self.subTest(evidence=evidence_id):
                source = os.path.join(REPO_ROOT, item["path"])
                value = self.load(source)
                broken = copy.deepcopy(value)
                broken["binding"]["github"]["run_id"] += 1
                with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
                    relative_root = os.path.relpath(temporary, REPO_ROOT)
                    broken_path = os.path.join(temporary, os.path.basename(source))
                    payload = review.canonical_bytes(broken)
                    self.write_bytes(broken_path, payload)
                    altered_manifest = copy.deepcopy(manifest)
                    altered_manifest["files"][evidence_id]["path"] = os.path.join(
                        relative_root, os.path.basename(source)
                    )
                    altered_manifest["files"][evidence_id]["sha256"] = review.sha256_bytes(payload)
                    manifest_copy = os.path.join(temporary, "review.json")
                    self.write_text(
                        manifest_copy,
                        json.dumps(altered_manifest, indent=2, sort_keys=True) + "\n"
                    )
                    original_review = review.REVIEW
                    review.REVIEW = os.path.relpath(manifest_copy, REPO_ROOT)
                    try:
                        with self.assertRaises(review.ReviewError):
                            review.check(REPO_ROOT)
                    finally:
                        review.REVIEW = original_review

    def test_every_binding_leaf_is_checked_not_just_the_run_id(self):
        manifest = self.load(os.path.join(REPO_ROOT, review.REVIEW))
        source = os.path.join(
            REPO_ROOT, manifest["files"]["acquisition_replay"]["path"]
        )
        record = self.load(source)
        tested = 0
        for path, original in scalar_leaves(review.EXPECTED_BINDING):
            with self.subTest(path=path):
                broken = copy.deepcopy(record)
                replace(broken["binding"], path, changed(original))
                with self.assertRaises(review.ReviewError):
                    review.binding(broken, review.EXPECTED_REVIEW, "fixture")
                tested += 1
        self.assertGreater(tested, 20)

    def test_every_semantic_result_leaf_is_checked(self):
        lock = self.load(os.path.join(REPO_ROOT, review.SOURCE_LOCK))
        series = self.load(os.path.join(REPO_ROOT, review.PATCH_SERIES))
        manifest = self.load(os.path.join(REPO_ROOT, review.REVIEW))
        verifiers = {
            "acquisition_replay": lambda record: review.verify_acquisition(record, lock),
            "dist_git_object_replay": lambda record: review.verify_dist_git(record, lock, series),
            "repository_metadata_signature_replay": lambda record: review.verify_repository(record, lock),
            "srpm_header_signature": lambda record: review.verify_srpm_signature(record, lock),
        }
        tested = 0
        for evidence_id, verifier in verifiers.items():
            record = self.load(
                os.path.join(REPO_ROOT, manifest["files"][evidence_id]["path"])
            )
            for path, original in scalar_leaves(record["result"]):
                with self.subTest(evidence=evidence_id, path=path):
                    broken = copy.deepcopy(record)
                    replace(broken["result"], path, changed(original))
                    with self.assertRaises(review.ReviewError):
                        verifier(broken)
                    tested += 1
        self.assertGreater(tested, 60)

    def test_duplicate_keys_and_rehashed_self_attestation_fail(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            duplicate = os.path.join(temporary, "duplicate.json")
            self.write_text(duplicate, '{"a":1,"a":2}\n')
            with self.assertRaises(review.ReviewError):
                review.read_json(duplicate)

        manifest = copy.deepcopy(review.EXPECTED_REVIEW)
        manifest["artifact"]["digest"] = "sha256:" + "0" * 64
        manifest["files"]["acquisition_replay"]["sha256"] = "0" * 64
        with self.assertRaises(review.ReviewError):
            review.require_exact(manifest, review.EXPECTED_REVIEW, "self-attested review")

    def test_every_review_manifest_leaf_is_immutable(self):
        tested = 0
        for path, original in scalar_leaves(review.EXPECTED_REVIEW):
            with self.subTest(path=path):
                broken = copy.deepcopy(review.EXPECTED_REVIEW)
                replace(broken, path, changed(original))
                with self.assertRaises(review.ReviewError):
                    review.require_exact(
                        broken, review.EXPECTED_REVIEW, "review manifest"
                    )
                tested += 1
        self.assertGreaterEqual(tested, 40)

    def test_digest_and_path_escape_fail_closed(self):
        manifest_path = os.path.join(REPO_ROOT, review.REVIEW)
        manifest = self.load(manifest_path)
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            for mutation in ("digest", "escape"):
                broken = copy.deepcopy(manifest)
                item = broken["files"]["acquisition_replay"]
                if mutation == "digest":
                    item["sha256"] = "0" * 64
                else:
                    item["path"] = "../outside.json"
                path = os.path.join(temporary, mutation + ".json")
                self.write_text(path, json.dumps(broken, indent=2, sort_keys=True) + "\n")
                original_review = review.REVIEW
                review.REVIEW = os.path.relpath(path, REPO_ROOT)
                try:
                    with self.assertRaises(review.ReviewError):
                        review.check(REPO_ROOT)
                finally:
                    review.REVIEW = original_review

    def test_review_cannot_claim_gate_completion(self):
        manifest_path = os.path.join(REPO_ROOT, review.REVIEW)
        manifest = self.load(manifest_path)
        manifest["gate_claim"] = True
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            path = os.path.join(temporary, "overclaim.json")
            self.write_text(path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            original_review = review.REVIEW
            review.REVIEW = os.path.relpath(path, REPO_ROOT)
            try:
                with self.assertRaises(review.ReviewError):
                    review.check(REPO_ROOT)
            finally:
                review.REVIEW = original_review

    def test_source_review_does_not_permanently_block_later_license_closure(self):
        lock = self.load(os.path.join(REPO_ROOT, review.SOURCE_LOCK))
        lock["gate"]["credit_eligible"] = True
        lock["licenses"]["inventory"]["complete"] = True
        result = review.check(REPO_ROOT, lock_override=lock)
        self.assertFalse(result["gate_claim"])


if __name__ == "__main__":
    unittest.main()
