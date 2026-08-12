#!/usr/bin/env python3
"""Fail-closed tests for the compiler-flow/behavior-contract gap bridge."""

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Tuple
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import host_module_failure_contract_gaps as gaps  # noqa: E402
import host_module_failure_flows as flows  # noqa: E402
import host_module_failure_sites as sites  # noqa: E402


class StrictInputTests(unittest.TestCase):
    def test_generator_and_tests_remain_python_3_6_compatible(self) -> None:
        paths = [Path(gaps.__file__), Path(__file__)]
        for path in paths:
            source = path.read_text(encoding="utf-8")
            if sys.version_info >= (3, 8):
                try:
                    tree = ast.parse(
                        source, filename=str(path), feature_version=(3, 6)
                    )
                except TypeError:
                    tree = ast.parse(source, filename=str(path), feature_version=6)
            else:
                tree = ast.parse(source, filename=str(path))
            self.assertIsNotNone(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                    self.assertNotIn(
                        "annotations", [alias.name for alias in node.names]
                    )
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, {"removeprefix", "removesuffix"})
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                    self.assertNotIn(node.value.id, {"dict", "list", "set", "tuple"})
                annotation = None
                if isinstance(node, ast.arg):
                    annotation = node.annotation
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    annotation = node.returns
                elif isinstance(node, ast.AnnAssign):
                    annotation = node.annotation
                if annotation is not None:
                    self.assertFalse(
                        any(
                            isinstance(part, ast.BinOp)
                            and isinstance(part.op, ast.BitOr)
                            for part in ast.walk(annotation)
                        ),
                        "PEP 604 annotation is not Python 3.6 compatible in {0}".format(
                            path
                        ),
                    )

        python36 = shutil.which("python3.6")
        if python36:
            completed = subprocess.run(
                [python36, str(Path(gaps.__file__)), "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())

    def test_duplicate_json_keys_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            with self.assertRaisesRegex(gaps.GapError, "duplicate JSON key"):
                gaps.read_json(path, "synthetic artifact")

    def test_completion_claim_is_immutably_false(self) -> None:
        self.assertEqual(
            gaps.ANALYSIS_CLAIM,
            {
                "credit_eligible": False,
                "executable_acceptance_coverage": False,
                "exhaustive": False,
                "fp_0006_status": "IN_PROGRESS",
                "reason": (
                    "this schema reports contract/compiler gaps and bounded flow mappings; "
                    "declared acceptance IDs are not executable test results"
                ),
                "test_mapped": False,
            },
        )

    def test_contract_regeneration_mutation_fails_closed(self) -> None:
        with mock.patch.object(gaps.contracts, "build_contract", return_value={}):
            with self.assertRaisesRegex(gaps.GapError, "contract validation failed"):
                gaps.validate_contract(REPO_ROOT)


class ProvenanceUnitTests(unittest.TestCase):
    def test_source_argv_resolves_dotdot_spelling_exactly(self) -> None:
        roots = (
            ("$REPO", Path("/__w/mckernel/mckernel")),
            ("$BUILD", Path("/tmp/mckernel-rocky-rust")),
            ("$KERNEL", Path("/usr/src/kernels/synthetic")),
        )
        record = {
            "source": "ihk/ikc/linux.c",
            "compile_argv": [
                "gcc",
                "-c",
                "/__w/mckernel/mckernel/ihk/linux/core/../../ikc/linux.c",
            ],
        }
        self.assertEqual(gaps.source_index(record, roots), 2)
        record["compile_argv"][-1] = "/__w/mckernel/mckernel/ihk/ikc/master.c"
        with self.assertRaisesRegex(gaps.GapError, "names the effective source 0 times"):
            gaps.source_index(record, roots)

    def test_configuration_aggregate_and_primary_are_bound(self) -> None:
        files = [
            {"bytes": 1, "path": ".config", "sha256": "a" * 64},
            {
                "bytes": 1,
                "path": "include/generated/autoconf.h",
                "sha256": "b" * 64,
            },
        ]
        value = {
            "files": files,
            "primary_sha256": "a" * 64,
            "sha256": gaps.sha256_bytes(gaps.canonical_bytes(files)),
        }
        gaps.validate_kernel_configuration(value)
        broken = copy.deepcopy(value)
        broken["files"][0]["bytes"] = 2
        with self.assertRaisesRegex(gaps.GapError, "aggregate digest is stale"):
            gaps.validate_kernel_configuration(broken)

    def test_compiler_provenance_digest_mutation_fails_closed(self) -> None:
        compiler = {
            "bytes": 1,
            "invoked_as": "gcc",
            "resolved_path": "/usr/bin/gcc",
            "sha256": "a" * 64,
            "version_first_line": "gcc synthetic",
            "version_stderr_sha256": "b" * 64,
            "version_stdout_sha256": "c" * 64,
        }
        gaps.validate_compiler_record(compiler, "synthetic")
        compiler["sha256"] = "not-a-digest"
        with self.assertRaisesRegex(gaps.GapError, "not a SHA-256"):
            gaps.validate_compiler_record(compiler, "synthetic")


class RelationshipUnitTests(unittest.TestCase):
    @staticmethod
    def fixture() -> Tuple[
        Dict[str, object], Dict[str, object], Dict[str, Dict[str, object]]
    ]:
        site = {
            "id": "HFS-" + "A" * 24,
            "errno": "EINVAL",
            "line": 10,
            "module": "ihk",
            "source": "demo.c",
        }
        extent = {
            "end_column": 20,
            "end_line": 12,
            "kind": "compiler_statement_extent",
            "start_column": 1,
            "start_line": 8,
        }
        function = {
            "name": "demo",
            "reachable_entry_roots": ["external:demo"],
            "statement_range": extent,
            "statement_sha256": "d" * 64,
        }
        source = {
            "active_compile_profile_sha256": "b" * 64,
            "module": "ihk",
            "provenance_sha256": "c" * 64,
            "source": "demo.c",
            "source_sha256": "a" * 64,
        }
        origin = {"errno": "EINVAL", "first_stage_site_ids": [site["id"]]}
        identity = {
            "active_compile_profile_sha256": source["active_compile_profile_sha256"],
            "expression_role": "errno_token_return_context",
            "function": "demo",
            "function_range": extent,
            "location": {"column": 4, "line": 10},
            "module": "ihk",
            "origin": origin,
            "provenance_sha256": source["provenance_sha256"],
            "reachable_entry_roots": function["reachable_entry_roots"],
            "source": "demo.c",
            "source_sha256": source["source_sha256"],
        }
        digest = gaps.sha256_bytes(gaps.canonical_bytes(identity))
        flow = {
            **identity,
            "expression": "return -EINVAL;",
            "id": "HFF-" + digest[:24].upper(),
            "identity_sha256": digest,
        }
        return site, flow, {"demo": function}

    def test_hff_identity_and_first_stage_binding_are_exact(self) -> None:
        site, flow, functions = self.fixture()
        source = {
            "active_compile_profile_sha256": "b" * 64,
            "module": "ihk",
            "provenance_sha256": "c" * 64,
            "source": "demo.c",
            "source_sha256": "a" * 64,
        }
        gaps.validate_flow(flow, source, functions, {site["id"]: site})
        broken = copy.deepcopy(flow)
        broken["identity_sha256"] = "0" * 64
        with self.assertRaisesRegex(gaps.GapError, "identity is stale"):
            gaps.validate_flow(broken, source, functions, {site["id"]: site})

    def test_unknown_unresolved_reason_and_hfs_mutation_fail_closed(self) -> None:
        site, _, functions = self.fixture()
        source_map = {"demo.c": {"language": "c", "source": "demo.c"}}
        record = {
            "errno": "EINVAL",
            "first_stage_site_ids": [site["id"]],
            "kind": "active_errno_token_has_no_unique_compiler_function",
            "line": 10,
            "source": "demo.c",
        }
        _, reason_id = gaps.validate_unresolved(
            record, source_map, {"demo.c": functions}, {site["id"]: site}
        )
        self.assertRegex(reason_id, r"^HUR-[0-9A-F]{24}$")
        broken = copy.deepcopy(record)
        broken["kind"] = "invented_complete_reason"
        with self.assertRaisesRegex(gaps.GapError, "unknown kind"):
            gaps.validate_unresolved(
                broken, source_map, {"demo.c": functions}, {site["id"]: site}
            )

    def test_every_hfs_id_has_one_exclusive_disposition(self) -> None:
        site_id = "HFS-" + "A" * 24
        gaps.validate_exact_site_dispositions(
            {site_id}, {site_id: ["HFF-" + "B" * 24]}, {}
        )
        with self.assertRaisesRegex(gaps.GapError, "exactly once"):
            gaps.validate_exact_site_dispositions(
                {site_id},
                {site_id: ["HFF-" + "B" * 24]},
                {site_id: ["HUR-" + "C" * 24]},
            )
        with self.assertRaisesRegex(gaps.GapError, "mapping closure differs"):
            gaps.validate_exact_site_dispositions({site_id}, {}, {})

    def test_acceptance_ids_are_labeled_declarative_not_executable(self) -> None:
        behavior = {
            "acceptance_test_ids": ["AT-IHK-LEGACY-ERRNO"],
            "id": "BHV-IHK-LEGACY-ERRNO",
            "legacy": {
                "column": 4,
                "errno": "EINVAL",
                "line": 10,
                "source": "demo.c",
            },
            "module": "ihk",
        }
        record = gaps.contract_site_record(behavior)
        self.assertEqual(
            record["acceptance_evidence"],
            "declarative_id_only_not_executed_or_verified",
        )
        self.assertEqual(
            record["classification"],
            "exact_identity_not_observed_in_compiler_active_capture",
        )
        self.assertNotIn("passed", json.dumps(record).lower())


class HeaderMutationTests(unittest.TestCase):
    @staticmethod
    def skeleton() -> Tuple[Dict[str, object], Dict[str, object], Dict[str, object]]:
        hfs_file = {"artifact_bytes": 10, "artifact_sha256": "a" * 64}
        hfs = {
            "failure_sites": [],
            "profile": sites.PROFILE,
            "provenance": {"repository_commit": "b" * 40},
        }
        capture = {
            "analysis_claim": dict(flows.ANALYSIS_CLAIM),
            "blockers": list(flows.FIXED_BLOCKERS),
            "coverage": {},
            "failure_flows": [],
            "generator": "scripts/host_module_failure_flows.py",
            "input_failure_sites": {
                "artifact_bytes": 10,
                "artifact_sha256": "a" * 64,
                "profile": sites.PROFILE,
                "repository_commit": "b" * 40,
            },
            "profile": flows.PROFILE,
            "schema_version": flows.SCHEMA_VERSION,
            "sources": [],
            "unresolved_paths": [],
        }
        return capture, hfs, hfs_file

    def test_flow_claim_escalation_fails_before_gap_generation(self) -> None:
        capture, hfs, hfs_file = self.skeleton()
        capture["analysis_claim"]["credit_eligible"] = True
        with self.assertRaisesRegex(gaps.GapError, "claim changed or escalated"):
            gaps.validate_flow_artifact(
                capture, {}, hfs, hfs_file, {}, ()
            )

    def test_flow_to_hfs_artifact_digest_mutation_fails_closed(self) -> None:
        capture, hfs, hfs_file = self.skeleton()
        capture["input_failure_sites"]["artifact_sha256"] = "c" * 64
        with self.assertRaisesRegex(gaps.GapError, "exact HFS bytes"):
            gaps.validate_flow_artifact(
                capture, {}, hfs, hfs_file, {}, ()
            )


@unittest.skipUnless(
    os.environ.get("MCKERNEL_REAL_FLOW_EVIDENCE_DIR"),
    "set MCKERNEL_REAL_FLOW_EVIDENCE_DIR for exact-head artifact integration",
)
class RealArtifactIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = Path(os.environ["MCKERNEL_REAL_FLOW_EVIDENCE_DIR"])
        cls.hfs, cls.hfs_file = gaps.read_json(
            cls.evidence / "host-module-failure-sites.json", "real HFS"
        )
        cls.flow, cls.flow_file = gaps.read_json(
            cls.evidence / "host-module-failure-flows.json", "real flows"
        )
        cls.contract, cls.contract_file = gaps.validate_contract(REPO_ROOT)
        cls.roots = (
            ("$REPO", Path(os.environ.get("MCKERNEL_EVIDENCE_REPO_ROOT", "/__w/mckernel/mckernel"))),
            ("$BUILD", Path(os.environ.get("MCKERNEL_EVIDENCE_BUILD_ROOT", "/tmp/mckernel-rocky-rust"))),
            ("$KERNEL", Path(os.environ.get("MCKERNEL_EVIDENCE_KERNEL_ROOT", "/usr/src/kernels/unknown"))),
        )
        cls.source_map = gaps.validate_hfs(
            cls.hfs,
            REPO_ROOT,
            Path("/tmp/mckernel-rocky-rust"),
            Path("/usr/src/kernels/unknown"),
            cls.roots,
            replay_environment=False,
        )

    def test_real_artifacts_emit_bounded_gap_counts_without_credit(self) -> None:
        index = gaps.validate_flow_artifact(
            self.flow,
            dict(self.flow_file),
            self.hfs,
            self.hfs_file,
            self.source_map,
            self.roots,
        )
        manifest = gaps.build_manifest(
            REPO_ROOT,
            self.contract,
            self.contract_file,
            self.hfs,
            self.hfs_file,
            self.flow,
            self.flow_file,
            index,
            self.roots,
        )
        self.assertEqual(manifest["coverage"]["compiler_active_failure_site_count"], 971)
        self.assertEqual(manifest["coverage"]["bounded_failure_flow_count"], 2602)
        self.assertEqual(manifest["coverage"]["unresolved_path_count"], 1813)
        self.assertEqual(manifest["coverage"]["compiler_active_missing_contract_count"], 4)
        self.assertEqual(manifest["coverage"]["conservative_stale_contract_count"], 19)
        self.assertEqual(manifest["analysis_claim"], gaps.ANALYSIS_CLAIM)
        self.assertEqual(
            manifest["contract_compiler_comparison"]["identity_fields"],
            ["module", "source", "line", "column", "errno"],
        )
        self.assertEqual(
            {
                item["classification"] for item in manifest["missing_contract_sites"]
            },
            {"exact_identity_absent_from_conservative_contract"},
        )

    def test_real_hff_identity_and_unresolved_kind_mutations_fail_closed(self) -> None:
        broken_flow = copy.deepcopy(self.flow)
        broken_flow["failure_flows"][0]["identity_sha256"] = "0" * 64
        with self.assertRaisesRegex(gaps.GapError, "identity is stale"):
            gaps.validate_flow_artifact(
                broken_flow,
                dict(self.flow_file),
                self.hfs,
                self.hfs_file,
                self.source_map,
                self.roots,
            )

        broken_reason = copy.deepcopy(self.flow)
        broken_reason["unresolved_paths"][0]["kind"] = "invented_complete_reason"
        with self.assertRaisesRegex(gaps.GapError, "unknown kind"):
            gaps.validate_flow_artifact(
                broken_reason,
                dict(self.flow_file),
                self.hfs,
                self.hfs_file,
                self.source_map,
                self.roots,
            )

    def test_real_config_compiler_and_argv_mutations_fail_closed(self) -> None:
        bad_config = copy.deepcopy(self.hfs)
        bad_config["sources"][0]["digests"]["config_sha256"] = "0" * 64
        with self.assertRaisesRegex(gaps.GapError, "configuration digest differs"):
            gaps.validate_source_records(bad_config, self.roots)

        bad_compiler = copy.deepcopy(self.hfs)
        bad_compiler["sources"][0]["preprocessor"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(gaps.GapError, "compiler digest differs"):
            gaps.validate_source_records(bad_compiler, self.roots)

        bad_argv = copy.deepcopy(self.hfs)
        bad_argv["sources"][0]["compile_argv"][-1] = "/outside/not-the-source.c"
        with self.assertRaisesRegex(gaps.GapError, "names the effective source 0 times"):
            gaps.validate_source_records(bad_argv, self.roots)


if __name__ == "__main__":
    unittest.main()
