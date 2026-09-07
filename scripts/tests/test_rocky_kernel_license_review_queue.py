#!/usr/bin/env python3
"""Adversarial tests for the non-crediting RK-001 review queue."""

from __future__ import print_function

import ast
import copy
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rocky_kernel_license_review_queue as queue


MANIFEST = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk001-license-review-queue-ef58-v1.json"
)
DECISION_MANIFEST = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk001-license-decisions-ef58-v1.json"
)
DECISION_CHECKER = REPO_ROOT / "scripts/rocky_kernel_license_decisions.py"
DEFAULT_ARTIFACT = Path(
    "/workspace/scratch/1962bd8160f6/ci-evidence/ef58860e/"
    "rk001-license-inventory-32192199002-1.zip"
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


def replace_leaf(value, path, replacement):
    current = value
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = replacement


def changed_leaf(value):
    if type(value) is bool:
        return not value
    if type(value) is int:
        return False
    if type(value) is str:
        return value + "-retargeted"
    raise AssertionError("unexpected authority leaf type: {0}".format(type(value)))


class LicenseReviewQueueTests(unittest.TestCase):
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
        cls.artifact = None
        for candidate in candidates:
            if candidate.is_file():
                cls.artifact = candidate
                break
        if cls.artifact is None:
            raise unittest.SkipTest(
                "exact ef58860e RK-001 inventory artifact is not materialized"
            )
        cls.manifest_bytes = MANIFEST.read_bytes()
        cls.authority = queue.load_authority(REPO_ROOT)
        (
            cls.decision_module,
            cls.decision_authority,
            cls.compressed,
            cls.decision_result,
        ) = queue.load_exact_inventory(REPO_ROOT, cls.artifact, cls.authority)
        cls.result, cls.records = queue.analyze_review_queue(
            cls.compressed, cls.decision_module, cls.decision_authority
        )
        queue.require_exact(
            cls.result,
            cls.authority["expected_result"],
            "test exact review-queue result",
        )

    def shallow_record_mutation(self, stream, index=0):
        records = dict(self.records)
        records[stream] = list(self.records[stream])
        records[stream][index] = copy.deepcopy(records[stream][index])
        return records, records[stream][index]

    def test_new_files_retain_python_3_6_grammar(self):
        for relative in (
            "scripts/rocky_kernel_license_review_queue.py",
            "scripts/tests/test_rocky_kernel_license_review_queue.py",
        ):
            path = REPO_ROOT / relative
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for fragment in (
                ".is_relative" + "_to(",
                ".remove" + "prefix(",
                ".remove" + "suffix(",
                "capture_" + "output=",
                "missing_" + "ok=",
            ):
                self.assertNotIn(fragment, source)

    def test_manifest_is_canonical_digest_locked_and_recursively_exact(self):
        self.assertEqual(
            hashlib.sha256(self.manifest_bytes).hexdigest(),
            queue.AUTHORITY_SHA256,
        )
        value = queue.read_json_bytes(
            self.manifest_bytes, "review-queue authority", canonical=True
        )
        self.assertEqual(queue.validate_authority(copy.deepcopy(value)), value)
        for path in leaf_paths(value):
            mutation = copy.deepcopy(value)
            current = mutation
            for key in path:
                current = current[key]
            replace_leaf(mutation, path, changed_leaf(current))
            with self.subTest(path=path):
                with self.assertRaises(queue.ReviewQueueError):
                    queue.validate_authority(mutation)
        extra = copy.deepcopy(value)
        extra["unknown"] = False
        with self.assertRaises(queue.ReviewQueueError):
            queue.validate_authority(extra)
        nested_extra = copy.deepcopy(value)
        nested_extra["claims"]["unknown"] = False
        with self.assertRaises(queue.ReviewQueueError):
            queue.validate_authority(nested_extra)

    def test_all_legal_provenance_durability_credit_and_gate_claims_stay_false(self):
        self.assertEqual(self.authority["claims"], queue.EXPECTED_CLAIMS)
        self.assertTrue(all(value is False for value in self.authority["claims"].values()))
        self.assertEqual(self.authority["gate"], queue.EXPECTED_GATE)
        self.assertEqual(self.authority["gate"]["status"], "TODO")
        self.assertEqual(self.authority["gate"]["points_awarded"], 0)
        policy = self.authority["queue_policy"]
        self.assertIs(policy["candidate_signal_auto_resolves"], False)
        self.assertIs(policy["candidate_signal_is_legal_conclusion"], False)
        self.assertIs(policy["candidate_signal_is_provenance_review"], False)

    def test_exact_frozen_input_bytes_and_decision_result_are_bound(self):
        inputs = self.authority["inputs"]
        self.assertEqual(
            hashlib.sha256(DECISION_CHECKER.read_bytes()).hexdigest(),
            inputs["decision_checker"]["sha256"],
        )
        self.assertEqual(DECISION_CHECKER.stat().st_size, 46167)
        self.assertEqual(
            hashlib.sha256(DECISION_MANIFEST.read_bytes()).hexdigest(),
            inputs["decision_authority"]["sha256"],
        )
        self.assertEqual(DECISION_MANIFEST.stat().st_size, 10012)
        self.assertEqual(
            hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
            inputs["artifact"]["sha256"],
        )
        self.assertEqual(self.artifact.stat().st_size, 6734527)
        self.assertEqual(
            self.decision_result, self.decision_authority["expected_result"]
        )
        self.assertEqual(self.decision_result["unresolved_count"], 42649)

    def test_exact_group_counts_and_stream_hashes_are_stable(self):
        self.assertEqual(self.result, queue.EXPECTED_RESULT)
        self.assertEqual(self.result["review_unit_count"], 42649)
        self.assertEqual(self.result["exact_content_path_count"], 42566)
        self.assertEqual(self.result["exact_content_group_count"], 38619)
        self.assertEqual(self.result["exact_content_duplicate_group_count"], 2214)
        self.assertEqual(self.result["exact_content_duplicate_path_count"], 6161)
        self.assertEqual(self.result["context_group_count"], 2607)
        self.assertEqual(self.result["reason_cluster_count"], 10)
        self.assertEqual(
            self.result["candidate_directory_signal_cluster_count"], 1653
        )
        self.assertEqual(
            self.result["candidate_directory_signal_path_count"], 11486
        )
        self.assertEqual(self.result["symlink_without_content_group_count"], 83)
        for key, value in self.result.items():
            if key.endswith("_sha256"):
                self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_record_schemas_order_and_cross_links_are_exactly_closed(self):
        self.assertIs(queue.validate_record_sets(self.records), self.records)
        paths = [row["evidence"]["path"] for row in self.records["review-units"]]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(
            len(self.records["exact-content-groups"]),
            self.result["exact_content_group_count"],
        )
        self.assertEqual(
            len(self.records["candidate-signals"]),
            self.result["candidate_directory_signal_cluster_count"],
        )

    def test_every_unit_remains_unresolved_and_independent_review_required(self):
        candidate_paths = 0
        symlinks = 0
        for unit in self.records["review-units"]:
            self.assertEqual(unit["decision"], "unresolved")
            self.assertEqual(unit["review_state"], "independent-review-required")
            self.assertEqual(unit["capture_review_status"], "captured-unreviewed")
            self.assertIn(
                "independent-review-required",
                unit["evidence"]["unresolved_reasons"],
            )
            if unit["candidate_directory_signal_id"] is not None:
                candidate_paths += 1
            if unit["evidence"]["entry_type"] == "symlink":
                symlinks += 1
                self.assertIsNone(unit["exact_content_group_id"])
            else:
                self.assertIsNotNone(unit["exact_content_group_id"])
        self.assertEqual(candidate_paths, 11486)
        self.assertEqual(symlinks, 83)

    def test_candidate_signals_are_nonconclusive_and_cannot_change_unit_state(self):
        for signal in self.records["candidate-signals"]:
            self.assertIs(signal["auto_resolution"], False)
            self.assertIs(signal["legal_conclusion"], False)
            self.assertIs(signal["provenance_review"], False)
            self.assertEqual(
                signal["signal_identity"]["evidence_class"],
                "candidate-only-machine-classified-same-directory-sibling",
            )
        for field in ("auto_resolution", "legal_conclusion", "provenance_review"):
            mutated, signal = self.shallow_record_mutation("candidate-signals")
            signal[field] = True
            with self.subTest(field=field):
                with self.assertRaises(queue.ReviewQueueError):
                    queue.validate_record_sets(mutated)
        for field, replacement in (
            ("decision", "machine-classified-exact-spdx"),
            ("review_state", "reviewed"),
        ):
            mutated, unit = self.shallow_record_mutation("review-units")
            unit[field] = replacement
            with self.subTest(field=field):
                with self.assertRaises(queue.ReviewQueueError):
                    queue.validate_record_sets(mutated)
        mutated, unit = self.shallow_record_mutation("review-units")
        unit["credit_eligible"] = True
        with self.assertRaises(queue.ReviewQueueError):
            queue.validate_record_sets(mutated)

    def test_group_and_candidate_cross_link_retargets_fail_closed(self):
        mutated, unit = self.shallow_record_mutation("review-units")
        unit["context_group_id"] = "context:" + "0" * 64
        with self.assertRaises(queue.ReviewQueueError):
            queue.validate_record_sets(mutated)
        candidate_unit_index = next(
            index
            for index, row in enumerate(self.records["review-units"])
            if row["candidate_directory_signal_id"] is not None
        )
        mutated, unit = self.shallow_record_mutation(
            "review-units", candidate_unit_index
        )
        unit["candidate_directory_signal_id"] = "candidate-directory:" + "0" * 64
        with self.assertRaises(queue.ReviewQueueError):
            queue.validate_record_sets(mutated)
        mutated, group = self.shallow_record_mutation("exact-content-groups")
        group["path_count"] += 1
        with self.assertRaises(queue.ReviewQueueError):
            queue.validate_record_sets(mutated)

    def test_source_identity_schema_and_types_are_recursively_closed(self):
        valid = (
            ({"archive_sha256": "1" * 64}, "linux"),
            ({"source_rpm_sha256": "2" * 64}, "srpm"),
            ({"git_blob_oid": "3" * 40, "git_commit": "4" * 40}, "repository"),
            ({"git_blob_oid": "5" * 40, "git_mode": "100644"}, "dist-git"),
        )
        for identity, namespace in valid:
            self.assertEqual(
                queue.validate_source_identity(identity, namespace, "test"), identity
            )
        invalid = (
            ({"archive_sha256": False}, "linux"),
            ({"source_rpm_sha256": "2" * 63}, "srpm"),
            ({"git_blob_oid": "3" * 40, "git_commit": False}, "repository"),
            ({"git_blob_oid": "5" * 40, "git_mode": 100644}, "dist-git"),
            ({"git_blob_oid": "5" * 40, "git_mode": "100644", "x": 0}, "dist-git"),
        )
        for identity, namespace in invalid:
            with self.subTest(identity=identity):
                with self.assertRaises(queue.ReviewQueueError):
                    queue.validate_source_identity(identity, namespace, "test")

    def test_deep_duplicate_nonfinite_json_gzip_and_spdx_fail_bounded(self):
        deep = b'{"x":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}\n"
        with self.assertRaises(queue.ReviewQueueError):
            queue.read_json_bytes(deep, "deep", canonical=True)
        with self.assertRaises(queue.ReviewQueueError):
            queue.read_json_bytes(b'{"x":NaN}\n', "nonfinite", canonical=True)
        with self.assertRaises(queue.ReviewQueueError):
            queue.read_json_bytes(b'{"x":Infinity}\n', "infinity")
        with self.assertRaises(queue.ReviewQueueError):
            queue.read_json_bytes(b'{"x":1.0}\n', "float")
        huge_integer = b'{"x":' + b"9" * 10000 + b"}\n"
        with self.assertRaises(queue.ReviewQueueError):
            queue.read_json_bytes(huge_integer, "huge integer")
        with self.assertRaisesRegex(queue.ReviewQueueError, "duplicate JSON key"):
            queue.read_json_bytes(b'{"x":0,"x":1}\n', "duplicate", canonical=True)
        oversized = gzip.compress(
            b"x" * (self.decision_module.MAX_LINE_BYTES + 1), compresslevel=9
        )
        with self.assertRaises(self.decision_module.DecisionError):
            list(self.decision_module.bounded_gzip_lines(oversized))
        corrupt = bytearray(gzip.compress(b'{"x":0}\n' * 1000))
        corrupt[10] ^= 0xff
        with self.assertRaises(self.decision_module.DecisionError):
            list(self.decision_module.bounded_gzip_lines(bytes(corrupt)))
        expression = "(" * 1500 + "GPL-2.0-only" + ")" * 1500
        with self.assertRaises(self.decision_module.DecisionError):
            self.decision_module.parse_spdx_expression(expression)

    def test_mutated_zip_and_symlink_inputs_fail_closed(self):
        data = bytearray(self.artifact.read_bytes())
        data[-1] ^= 1
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            changed = root / "changed.zip"
            changed.write_bytes(bytes(data))
            with self.assertRaises(self.decision_module.DecisionError):
                self.decision_module.read_artifact(
                    changed, self.decision_authority["artifact"]
                )
            linked = root / "linked.zip"
            linked.symlink_to(self.artifact)
            with self.assertRaises(self.decision_module.DecisionError):
                self.decision_module.read_artifact(
                    linked, self.decision_authority["artifact"]
                )

    def test_manifest_checker_authority_and_ancestor_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            linked = root / "authority.json"
            linked.symlink_to(MANIFEST)
            with self.assertRaisesRegex(queue.ReviewQueueError, "symlink"):
                queue.load_authority(REPO_ROOT, linked)

            real_parent = root / "real"
            real_parent.mkdir()
            regular = real_parent / "input"
            regular.write_bytes(b"bounded\n")
            alias = root / "alias"
            alias.symlink_to(real_parent, target_is_directory=True)
            with self.assertRaisesRegex(queue.ReviewQueueError, "symlink"):
                queue.read_regular_file_once(alias / "input", "ancestor", 1024)

    def test_checker_and_decision_authority_byte_retargets_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checker = root / queue.DECISION_CHECKER_RELATIVE
            authority = root / queue.DECISION_AUTHORITY_RELATIVE
            checker.parent.mkdir(parents=True)
            authority.parent.mkdir(parents=True)
            checker.write_bytes(DECISION_CHECKER.read_bytes() + b"\n")
            authority.write_bytes(DECISION_MANIFEST.read_bytes())
            with self.assertRaisesRegex(queue.ReviewQueueError, "checker bytes"):
                queue._load_frozen_checker(root, self.authority)
            checker.write_bytes(DECISION_CHECKER.read_bytes())
            authority.write_bytes(DECISION_MANIFEST.read_bytes() + b"\n")
            with self.assertRaisesRegex(queue.ReviewQueueError, "authority bytes"):
                queue._load_frozen_checker(root, self.authority)

        coherent = copy.deepcopy(self.authority)
        coherent["inputs"]["decision_checker"]["sha256"] = "0" * 64
        coherent["inputs"]["decision_checker"]["size"] = 1
        coherent["inputs"]["decision_authority"]["sha256"] = "1" * 64
        coherent["inputs"]["artifact"]["sha256"] = "2" * 64
        coherent["expected_result"]["review_unit_stream_sha256"] = "3" * 64
        with self.assertRaises(queue.ReviewQueueError):
            queue.validate_authority(coherent)

    def test_read_once_detects_a_toctou_identity_change(self):
        original = queue._stat_identity
        calls = [0]

        def shifting(info):
            value = original(info)
            calls[0] += 1
            if calls[0] == 4:
                return value[:-1] + (value[-1] + 1,)
            return value

        with mock.patch.object(queue, "_stat_identity", side_effect=shifting):
            with self.assertRaisesRegex(queue.ReviewQueueError, "changed while read"):
                queue.read_regular_file_once(MANIFEST, "TOCTOU authority", 1024 * 1024)

    def test_retargeted_manifest_bytes_fail_the_frozen_digest(self):
        changed = copy.deepcopy(self.authority)
        changed["gate"]["status"] = "PASS"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authority.json"
            path.write_bytes(queue.canonical_json(changed, newline=True))
            with self.assertRaisesRegex(queue.ReviewQueueError, "digest differs"):
                queue.load_authority(REPO_ROOT, path)

    def test_cli_json_reports_todo_zero_and_review_required(self):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "rocky_kernel_license_review_queue.py"),
                "--artifact",
                str(self.artifact),
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        output = json.loads(completed.stdout.decode("ascii"))
        self.assertEqual(output["gate"], queue.EXPECTED_GATE)
        self.assertTrue(all(value is False for value in output["claims"].values()))
        self.assertEqual(output["result"], queue.EXPECTED_RESULT)
        self.assertIn("independent-review-required", output["remaining_blockers"][0])

    def test_source_lock_and_tracker_remain_unmodified_and_uncredited(self):
        source_lock_path = REPO_ROOT / "host-kernel/rocky/source-lock.json"
        source_lock_text = source_lock_path.read_text(encoding="utf-8")
        self.assertNotIn(MANIFEST.name, source_lock_text)
        tracker = (REPO_ROOT / "final-push.txt").read_text(encoding="utf-8")
        self.assertIn("GATE|RK-001|WS10|75|TODO|-|", tracker)
        self.assertNotIn("GATE|RK-001|WS10|75|PASS|", tracker)


if __name__ == "__main__":
    unittest.main()
