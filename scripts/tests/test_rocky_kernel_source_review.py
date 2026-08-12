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
        self.assertEqual(result["workflow"]["run_id"], 31560588350)
        self.assertEqual(result["artifact"]["id"], 9127584719)

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


if __name__ == "__main__":
    unittest.main()
