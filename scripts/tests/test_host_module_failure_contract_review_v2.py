#!/usr/bin/env python3
"""Tests for the bounded, non-crediting FP-0006 contract review v2."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import host_module_failure_contract_review_v2 as review_v2  # noqa: E402
import host_module_failure_flows_v2 as flows_v2  # noqa: E402


def has_exact_historical_evidence():
    root = os.environ.get("MCKERNEL_REAL_FLOW_EVIDENCE_DIR")
    if not root:
        return False
    path = Path(root) / "host-module-failure-sites.json"
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return {
        "artifact_bytes": len(data),
        "artifact_sha256": flows_v2.sha256_bytes(data),
    } == flows_v2.EXPECTED_HFS_ARTIFACT


class ClaimTests(unittest.TestCase):
    def test_direct_cli_rejects_before_sibling_import_shadow(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "host_module_failure_contract_review_v2.py"
            script.write_bytes(
                (
                    REPO_ROOT
                    / "scripts/host_module_failure_contract_review_v2.py"
                ).read_bytes()
            )
            sentinel = root / "json.executed"
            (root / "json.py").write_text(
                "open({0!r}, 'w').write('executed')\n"
                "__import__('os').unlink(__file__)\n".format(str(sentinel)),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=str(root),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn(b"requires the isolated", completed.stderr)
            self.assertFalse(sentinel.exists())

    def test_main_requires_fresh_authority_but_preserves_historical_lane(self):
        arguments = [
            "--repo",
            str(REPO_ROOT),
            "--failure-sites",
            "hfs.json",
            "--failure-flows-v1",
            "v1.json",
            "--failure-flows-v2",
            "v2.json",
            "--output",
            "review.json",
        ]
        review = {
            "coverage": {
                "compiler_active_mapped_count": 1,
                "compiler_active_failure_site_count": 1,
                "stale_conservative_contract_count": 0,
            }
        }
        with mock.patch.object(
            review_v2, "build_review", return_value=review
        ) as build, mock.patch.object(review_v2, "write_review"):
            self.assertEqual(review_v2.main(arguments), 1)
            build.assert_not_called()
            self.assertEqual(
                review_v2.main(
                    arguments, repository_authority={"fresh": True}
                ),
                0,
            )
            self.assertEqual(
                review_v2.main(arguments + ["--historical-ef58"]), 0
            )

    def test_every_completion_and_credit_claim_is_false(self):
        for name, value in review_v2.ANALYSIS_CLAIM.items():
            if isinstance(value, bool):
                self.assertFalse(value, name)
        self.assertEqual(review_v2.ANALYSIS_CLAIM["fp_0006_status"], "IN_PROGRESS")

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"profile":"a","profile":"b"}\n', encoding="utf-8")
            with self.assertRaisesRegex(review_v2.ReviewV2Error, "duplicate JSON key"):
                review_v2.read_json(path, "duplicate")

    def test_nonfinite_json_and_canonical_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nonfinite.json"
            path.write_text('{"ignored_nonfinite":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(review_v2.ReviewV2Error, "non-finite"):
                review_v2.read_json(path, "nonfinite")
        with self.assertRaises(ValueError):
            review_v2.canonical_bytes({"ignored_nonfinite": float("nan")})
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                review_v2.write_review(
                    Path(temporary) / "output.json",
                    {"ignored_nonfinite": float("nan")},
                )

    def test_symlink_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.json"
            target.write_text("{}\n", encoding="utf-8")
            link = root / "input.json"
            link.symlink_to(target)
            with self.assertRaisesRegex(review_v2.ReviewV2Error, "symlink"):
                review_v2.read_json(link, "symlink")

    def test_ancestor_directory_symlink_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target_dir = root / "target"
            target_dir.mkdir()
            (target_dir / "input.json").write_text("{}\n", encoding="utf-8")
            alias_dir = root / "alias"
            alias_dir.symlink_to(target_dir, target_is_directory=True)
            with self.assertRaisesRegex(review_v2.ReviewV2Error, "symlink"):
                review_v2.read_json(alias_dir / "input.json", "ancestor symlink")

    def test_open_descriptor_binds_bytes_when_path_is_swapped(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "authority.json"
            replacement = root / "replacement.json"
            original_bytes = b'{"authority":"A"}\n'
            path.write_bytes(original_bytes)
            replacement.write_bytes(b'{"authority":"B"}\n')
            real_fstat = review_v2.os.fstat

            def swap_after_open(descriptor):
                review_v2.os.replace(replacement, path)
                return real_fstat(descriptor)

            with mock.patch.object(
                review_v2.os, "fstat", side_effect=swap_after_open
            ):
                value, record = review_v2.read_json(path, "swapped authority")
            self.assertEqual(value, {"authority": "A"})
            self.assertEqual(record["artifact_bytes"], len(original_bytes))
            self.assertEqual(
                record["artifact_sha256"], review_v2.sha256_bytes(original_bytes)
            )
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")), {"authority": "B"}
            )


@unittest.skipUnless(
    has_exact_historical_evidence(),
    "set MCKERNEL_REAL_FLOW_EVIDENCE_DIR to the exact ef58860e evidence",
)
class RealArtifactIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = Path(os.environ["MCKERNEL_REAL_FLOW_EVIDENCE_DIR"])
        cls.hfs_path = cls.evidence / "host-module-failure-sites.json"
        cls.v1_path = cls.evidence / "host-module-failure-flows.json"
        cls.temporary = tempfile.TemporaryDirectory()
        cls.v2_path = Path(cls.temporary.name) / "host-module-failure-flows-v2.json"
        cls.flow_capture = flows_v2.build_capture(
            REPO_ROOT, cls.hfs_path, cls.v1_path, historical_ef58=True
        )
        flows_v2.write_capture(cls.v2_path, cls.flow_capture)
        cls.review = review_v2.build_review(
            REPO_ROOT,
            cls.hfs_path,
            cls.v1_path,
            cls.v2_path,
            historical_ef58=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_exact_profile_maps_971_of_971_with_no_credit(self):
        coverage = self.review["coverage"]
        self.assertEqual(coverage["compiler_active_failure_site_count"], 971)
        self.assertEqual(coverage["compiler_active_mapped_count"], 971)
        self.assertEqual(coverage["compiler_active_missing_count"], 0)
        self.assertEqual(coverage["compiler_active_exact_contract_count"], 967)
        self.assertEqual(coverage["compiler_active_macro_alias_count"], 2)
        self.assertEqual(
            coverage["compiler_active_selected_profile_supplement_count"], 2
        )
        self.assertEqual(coverage["conservative_contract_failure_site_count"], 986)
        self.assertEqual(coverage["reviewed_contract_failure_site_count"], 988)
        self.assertEqual(coverage["c_ambiguous_failure_site_count"], 0)
        self.assertEqual(coverage["c_external_root_unresolved_count"], 0)
        self.assertEqual(coverage["rust_mir_unresolved_site_count"], 420)
        self.assertEqual(coverage["semantic_domain_unresolved_count"], 205)
        self.assertEqual(self.review["analysis_claim"], review_v2.ANALYSIS_CLAIM)
        self.assertEqual(
            self.review["c_flow_analysis_scope"], flows_v2.ANALYSIS_SCOPE
        )
        self.assertEqual(
            self.review["inputs"]["failure_flows_v1"],
            self.flow_capture["inputs"]["failure_flows_v1"],
        )
        self.assertEqual(
            self.review["authority_mode"], flows_v2.HISTORICAL_AUTHORITY_MODE
        )

    def test_all_19_exact_difference_rows_have_multi_profile_classifications(self):
        coverage = self.review["coverage"]
        self.assertEqual(coverage["stale_conservative_contract_count"], 19)
        self.assertEqual(
            coverage["stale_conservative_contract_count_by_classification"],
            {
                "alternate_profile_branch": 16,
                "physical_spelling_alias_of_active_logical_macro_site": 2,
                "version_guard_inactive": 1,
            },
        )
        rows = self.review["stale_conservative_contract_sites"]
        self.assertTrue(all(item["profile_reason"] for item in rows))
        aliases = [
            item
            for item in rows
            if item["classification"]
            == "physical_spelling_alias_of_active_logical_macro_site"
        ]
        self.assertEqual(len(aliases), 2)
        self.assertTrue(all(len(item["active_alias_hfs_ids"]) == 1 for item in aliases))

    def test_selected_profile_supplements_remain_rust_only_and_declarative(self):
        supplements = [
            item
            for item in self.review["active_site_mappings"]
            if item["contract_match_kind"]
            == "selected_compiler_profile_supplement"
        ]
        self.assertEqual(len(supplements), 2)
        self.assertEqual(
            {item["compiler_site"]["hfs_id"] for item in supplements},
            {
                "HFS-DC5B12F30906A4362FB28DBF",
                "HFS-D9B12133A20AA15053FA4715",
            },
        )
        for item in supplements:
            mapping = item["mapping"]
            self.assertEqual(
                mapping["acceptance_evidence"],
                "declarative_id_only_not_executed_or_verified",
            )
            self.assertFalse(
                mapping["rust_replacement"]["project_c_dispatch_permitted"]
            )

    def test_mapping_and_claim_mutations_fail_closed(self):
        hfs, hfs_file = review_v2.read_json(self.hfs_path, "HFS")
        escalated = copy.deepcopy(self.flow_capture)
        escalated["analysis_claim"]["credit_eligible"] = True
        with self.assertRaisesRegex(review_v2.ReviewV2Error, "exact derivation"):
            review_v2.validate_v2_capture(
                escalated, {}, hfs, hfs_file, self.flow_capture
            )

        macro_changed = copy.deepcopy(self.flow_capture)
        macro = next(
            item
            for item in macro_changed["site_dispositions"]
            if item["kind"] == "logical_macro_definition"
        )
        macro["conservative_physical_identity"]["line"] += 1
        macro["physical_spelling"]["line"] += 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mutated-v2.json"
            path.write_text(
                json.dumps(macro_changed, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(review_v2.ReviewV2Error, "exact derivation"):
                review_v2.build_review(
                    REPO_ROOT,
                    self.hfs_path,
                    self.v1_path,
                    path,
                    historical_ef58=True,
                )

    def test_exact_v1_derivation_rejects_semantic_deletion_retarget_and_type_confusion(self):
        mutations = []

        semantic_deleted = copy.deepcopy(self.flow_capture)
        semantic_deleted["unresolved_paths"] = [
            item
            for item in semantic_deleted["unresolved_paths"]
            if item["kind"] != "return_value_error_domain_unresolved"
        ]
        semantic_deleted["coverage"]["semantic_domain_unresolved_count"] = 0
        mutations.append(("semantic rows removed", semantic_deleted))

        v1_retargeted = copy.deepcopy(self.flow_capture)
        v1_retargeted["inputs"]["failure_flows_v1"]["artifact_sha256"] = "0" * 64
        mutations.append(("v1 digest retargeted", v1_retargeted))

        expression_retargeted = copy.deepcopy(self.flow_capture)
        expression_retargeted["failure_flows"][0]["expression"] += " /* retargeted */"
        mutations.append(("flow expression retargeted", expression_retargeted))

        location_retargeted = copy.deepcopy(self.flow_capture)
        location_retargeted["failure_flows"][0]["location"]["line"] += 1
        mutations.append(("flow location retargeted", location_retargeted))

        for section, field in (
            ("analysis_claim", "credit_eligible"),
            ("analysis_scope", "module_api_reachability_proven"),
        ):
            confused = copy.deepcopy(self.flow_capture)
            confused[section][field] = 0
            mutations.append((section + " bool/int confusion", confused))
        coverage_confused = copy.deepcopy(self.flow_capture)
        coverage_confused["coverage"]["c_ambiguous_failure_site_count"] = False
        mutations.append(("coverage bool/int confusion", coverage_confused))

        for name, mutated in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "mutated-v2.json"
                path.write_text(
                    json.dumps(mutated, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(review_v2.ReviewV2Error, "exact derivation"):
                    review_v2.build_review(
                        REPO_ROOT,
                        self.hfs_path,
                        self.v1_path,
                        path,
                        historical_ef58=True,
                    )

    def test_stale_classification_rejects_same_source_retargeting(self):
        contract, _ = review_v2.validate_contract(REPO_ROOT)
        behaviors = {
            review_v2.contract_identity(item["module"], item["legacy"]): item
            for item in contract["behaviors"]
            if item["kind"] == "legacy_errno"
        }
        cases = (
            (
                next(iter(review_v2.EXPECTED_ALTERNATE_PROFILE_CONTRACT_IDENTITIES)),
                [],
            ),
            (
                next(iter(review_v2.EXPECTED_VERSION_GUARD_CONTRACT_IDENTITIES)),
                [],
            ),
            (
                next(iter(review_v2.EXPECTED_MACRO_ALIAS_CONTRACT_IDENTITIES)),
                ["HFS-5F66311F0E37247084F3027F"],
            ),
        )
        for identity, aliases in cases:
            with self.subTest(identity=identity):
                retargeted = copy.deepcopy(behaviors[identity])
                retargeted["legacy"]["line"] += 1
                with self.assertRaises(review_v2.ReviewV2Error):
                    review_v2.classify_stale_contract_row(retargeted, aliases)

    def test_review_rejects_coherently_rebound_hfs_provenance_before_derivation(self):
        hfs = json.loads(self.hfs_path.read_text(encoding="utf-8"))
        hfs["provenance"]["repository_commit"] = "0" * 40
        hfs_bytes = (
            json.dumps(hfs, allow_nan=False, sort_keys=True) + "\n"
        ).encode("utf-8")
        v1 = json.loads(self.v1_path.read_text(encoding="utf-8"))
        v1["input_failure_sites"]["artifact_bytes"] = len(hfs_bytes)
        v1["input_failure_sites"]["artifact_sha256"] = review_v2.sha256_bytes(
            hfs_bytes
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hfs_path = root / "rebound-hfs.json"
            v1_path = root / "rebound-v1.json"
            hfs_path.write_bytes(hfs_bytes)
            v1_path.write_text(
                json.dumps(v1, allow_nan=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                review_v2.ReviewV2Error, "archived ef58860e HFS"
            ):
                review_v2.build_review(
                    REPO_ROOT,
                    hfs_path,
                    v1_path,
                    self.v2_path,
                    historical_ef58=True,
                )


if __name__ == "__main__":
    unittest.main()
