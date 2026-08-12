#!/usr/bin/env python3
"""Fail-closed tests for the RS-001 exact Linux API evidence probe."""

from __future__ import print_function

import ast
import copy
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import linux_api_exact_probe as probe  # noqa: E402


class ProbeFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = probe.read_json(REPO_ROOT / probe.CONTRACT_PATH)
        cls.needs_manifest = probe.read_json(REPO_ROOT / probe.NEEDS_PATH)
        cls.needs = probe.validate_needs_manifest(cls.needs_manifest)

    def evidence_fixture(self):
        config_sha = "a" * 64
        rows = probe.per_need_rows(
            self.needs,
            {},
            {},
            set(),
            config_sha,
            (None, None, None),
            (False, False, False),
        )
        tools = []
        for probe_id, command in probe.TOOL_PROBES:
            tools.append(
                {
                    "id": probe_id,
                    "command": list(command),
                    "status": "captured",
                    "path": "/usr/bin/" + probe_id,
                    "sha256": "1" * 64,
                    "exit_code": 0,
                    "stdout_sha256": "2" * 64,
                    "stderr_sha256": "3" * 64,
                    "version_excerpt": "synthetic",
                    "rpm_owner": "synthetic-1.0-1.x86_64",
                    "rpm_owner_query_sha256": "4" * 64,
                }
            )
        source_patches = []
        for row in self.contract["source_patch_contract"]["patches"]:
            source_patches.append(
                {
                    "path": row["path"],
                    "bytes": row["size"],
                    "sha256": row["sha256"],
                    "applied": row["applied"],
                    "empty": row["empty"],
                }
            )
        assertions = [
            {"symbol": "CONFIG_RUST", "expected": "y", "actual": "y", "matches": True}
        ]
        evidence = {
            "schema_version": probe.SCHEMA_VERSION,
            "profile": probe.EVIDENCE_PROFILE,
            "contract_id": probe.CONTRACT_ID,
            "contract_sha256": self.contract["contract_sha256"],
            "capture_identity": {
                "repository_commit": "4" * 40,
                "github_repository": "synthetic/repo",
                "github_run_id": "1",
                "github_run_attempt": "1",
            },
            "target": self.contract["target"],
            "inputs": {
                "frozen_needs_file_sha256": self.contract["frozen_needs"]["file_sha256"],
                "frozen_needs_manifest_sha256": self.contract["frozen_needs"]["manifest_sha256"],
                "source_lock_sha256": self.contract["repository_inputs"]["source_lock"]["sha256"],
                "config_policy_sha256": self.contract["repository_inputs"]["config_policy"]["sha256"],
                "toolchain_lock_sha256": self.contract["repository_inputs"]["toolchain_lock"]["sha256"],
                "patch_series_sha256": self.contract["repository_inputs"]["patch_series"]["sha256"],
                "rust_target_compatibility_patch_sha256s": [
                    row["sha256"]
                    for row in self.contract["repository_inputs"][
                        "rust_target_compatibility_patches"
                    ]
                ],
            },
            "environment": {
                "architecture": "x86_64",
                "os_release": {"id": "rocky", "version_id": "10.2", "sha256": "5" * 64},
                "uname": {},
                "tools": tools,
            },
            "source": {
                "source_rpm": {
                    "bytes": self.contract["target"]["source_rpm_bytes"],
                    "sha256": self.contract["target"]["source_rpm_sha256"],
                    "filename": self.contract["target"]["source_rpm_filename"],
                },
                "source_archive": {
                    "bytes": self.contract["target"]["source_archive_bytes"],
                    "sha256": self.contract["target"]["source_archive_sha256"],
                    "filename": self.contract["target"]["source_archive_filename"],
                },
                "patches": source_patches,
                "patched_tree_file_count": 1,
                "patched_tree_manifest_sha256": "6" * 64,
                "exact_locked_replay": True,
            },
            "configuration": {
                "baseline": {"bytes": 1, "sha256": "7" * 64, "path_role": "locked Rocky baseline"},
                "fragment": {"bytes": 1, "sha256": "8" * 64, "path": "fragment"},
                "resolved": {"bytes": 1, "sha256": config_sha, "path_role": "first olddefconfig pass"},
                "second_pass": {"bytes": 1, "sha256": config_sha, "path_role": "second olddefconfig pass"},
                "changed_symbols": ["CONFIG_RUST"],
                "allowed_changed_symbols": ["CONFIG_RUST"],
                "unexpected_changed_symbols": [],
                "assertions": assertions,
                "idempotent": True,
                "exact_policy_match": True,
                "selected_config_sha256": config_sha,
            },
            "build_outputs": {
                "module_symvers": {"bytes": 1, "sha256": "9" * 64, "symbol_count": 1},
                "system_map": {"bytes": 1, "sha256": "a" * 64, "symbol_count": 1},
                "rust_bindings": {
                    "bytes": 1,
                    "sha256": "b" * 64,
                    "binding_count": 1,
                    "binding_set_sha256": "c" * 64,
                },
                "kernel_release": "6.12.0-synthetic",
            },
            "reviewed_maps": {
                "config_requirements": {"status": "missing", "sha256": None, "trusted": False},
                "consumer_contexts": {"status": "missing", "sha256": None, "trusted": False},
                "rust_abstractions": {"status": "missing", "sha256": None, "trusted": False},
            },
            "needs": rows,
            "coverage": {
                "need_count": len(rows),
                "need_ids_sha256": probe.sha256_bytes(
                    probe.canonical_bytes([row["id"] for row in rows])
                ),
                "by_status": {
                    "availability": dict(sorted(Counter(row["availability"]["status"] for row in rows).items())),
                    "export": dict(sorted(Counter(row["export"]["status"] for row in rows).items())),
                    "configuration": dict(sorted(Counter(row["configuration"]["status"] for row in rows).items())),
                    "rust_callable": dict(sorted(Counter(row["rust_callable"]["status"] for row in rows).items())),
                    "call_context": dict(sorted(Counter(row["call_context"]["status"] for row in rows).items())),
                },
            },
            "readiness": {
                "gate": "RS-001",
                "gate_status": "NOT_READY",
                "technical_complete": False,
                "credit_eligible": False,
                "review_required": True,
                "blockers": [
                    "independent RS-001 review and immutable evidence registration are required; this capture cannot award gate credit"
                ],
            },
        }
        evidence["evidence_sha256"] = probe.evidence_digest(evidence)
        return evidence

    def resign(self, evidence):
        evidence["evidence_sha256"] = probe.evidence_digest(evidence)


class ContractTests(ProbeFixture):
    def test_contract_is_complete_current_and_fail_closed_without_inputs(self):
        generated = probe.build_contract(REPO_ROOT)
        probe.validate_contract(generated, REPO_ROOT)
        self.assertEqual(generated, self.contract)
        self.assertEqual(generated["frozen_needs"]["need_count"], 268)
        self.assertFalse(generated["gate"]["credit_eligible"])
        self.assertTrue(generated["gate"]["self_attestation_forbidden"])
        self.assertEqual(
            generated["readiness_without_exact_capture"],
            {
                "gate_status": "NOT_READY",
                "technical_complete": False,
                "credit_eligible": False,
                "blocker": "exact compiler/source/build inputs and pinned reviewed maps are absent",
            },
        )
        self.assertEqual(
            generated["reviewed_map_pins"],
            {
                "config_requirements_sha256": None,
                "consumer_contexts_sha256": None,
                "rust_abstractions_sha256": None,
            },
        )
        compatibility = generated["repository_inputs"][
            "rust_target_compatibility_patches"
        ]
        self.assertEqual(
            [row["path"] for row in compatibility],
            [str(path) for path in probe.RUST_COMPAT_PATCH_PATHS],
        )
        self.assertEqual(
            [row["upstream_commit"] for row in compatibility],
            list(probe.RUST_COMPAT_UPSTREAM_COMMITS),
        )
        self.assertEqual(
            generated["repository_inputs"]["rust_target_generator_preimage"],
            {
                "path": str(probe.RUST_COMPAT_FIXTURE_PATH),
                "sha256": probe.RUST_COMPAT_FIXTURE_SHA256,
            },
        )
        self.assertEqual(
            generated["source_patch_contract"]["patches"][-2:],
            [
                {
                    "applied": True,
                    "empty": False,
                    "path": row["path"],
                    "sha256": row["sha256"],
                    "size": row["size"],
                }
                for row in compatibility
            ],
        )

    def test_workflow_is_exact_build_bound_and_never_edits_tracker(self):
        workflow = (REPO_ROOT / probe.WORKFLOW_PATH).read_text(encoding="utf-8")
        self.assertIn("rockylinux/rockylinux:10.2@sha256:", workflow)
        self.assertIn("vmlinux modules", workflow)
        self.assertIn("Module.symvers", workflow)
        self.assertIn("bindings_generated.rs", workflow)
        self.assertIn("capture", workflow)
        self.assertIn("verify-evidence", workflow)
        self.assertIn("actions/checkout@11d5960", workflow)
        self.assertIn("actions/upload-artifact@ea165f8", workflow)
        self.assertNotIn("final-push.txt", workflow)
        rocky_patch = '-i "$RS001_SOURCE_ASSETS/1000-debrand-some-messages.patch"'
        compatibility_patch = '-i "$compat_asset"'
        for path in probe.RUST_COMPAT_PATCH_PATHS:
            self.assertIn(path.name, workflow)
        self.assertLess(workflow.index(rocky_patch), workflow.index(compatibility_patch))
        self.assertLess(workflow.index(compatibility_patch), workflow.index("rustavailable"))
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[0].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[1].name),
        )

    def test_rust_compatibility_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[1]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in probe.RUST_COMPAT_PATCH_PATHS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((REPO_ROOT / relative).read_bytes())
            path = root / probe.RUST_COMPAT_PATCH_PATHS[1]
            path.write_text(
                original.replace(
                    "+        if cfg.rustc_version_atleast(1, 91, 0) {",
                    "+        if cfg.rustc_version_atleast(1, 90, 0) {",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_generator_and_tests_parse_as_python_3_6(self):
        for path in (Path(probe.__file__), Path(__file__)):
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=str(path), feature_version=6)
            self.assertIsNotNone(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                    self.assertNotIn("annotations", [item.name for item in node.names])
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, {"removeprefix", "removesuffix"})
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                    self.assertNotIn(node.value.id, {"dict", "list", "set", "tuple"})


class EvidenceMutationTests(ProbeFixture):
    def test_synthetic_268_row_evidence_is_valid_but_not_ready(self):
        evidence = self.evidence_fixture()
        probe.validate_evidence(evidence, self.contract, self.needs_manifest)
        self.assertEqual(len(evidence["needs"]), 268)
        self.assertEqual(evidence["readiness"]["gate_status"], "NOT_READY")
        self.assertFalse(evidence["readiness"]["technical_complete"])
        self.assertFalse(evidence["readiness"]["credit_eligible"])

    def test_missing_need_fails_after_recomputed_counts_and_digest(self):
        evidence = self.evidence_fixture()
        evidence["needs"].pop()
        evidence["coverage"]["need_count"] -= 1
        evidence["coverage"]["need_ids_sha256"] = probe.sha256_bytes(
            probe.canonical_bytes([row["id"] for row in evidence["needs"]])
        )
        for category, field in (
            ("availability", "availability"),
            ("export", "export"),
            ("configuration", "configuration"),
            ("rust_callable", "rust_callable"),
            ("call_context", "call_context"),
        ):
            evidence["coverage"]["by_status"][category] = dict(
                sorted(Counter(row[field]["status"] for row in evidence["needs"]).items())
            )
        self.resign(evidence)
        with self.assertRaises(probe.ProbeError):
            probe.validate_evidence(evidence, self.contract, self.needs_manifest)

    def test_export_symbol_mutation_fails_even_when_resigned(self):
        evidence = self.evidence_fixture()
        row = evidence["needs"][0]
        row["export"]["entries"] = [
            {
                "crc": "0x0",
                "symbol": "wrong_symbol",
                "provider": "vmlinux",
                "export_class": "EXPORT_SYMBOL",
                "namespace": "",
            }
        ]
        row["export"]["status"] = "unique"
        row["availability"]["status"] = "exported"
        evidence["coverage"]["by_status"]["availability"] = dict(
            sorted(Counter(item["availability"]["status"] for item in evidence["needs"]).items())
        )
        evidence["coverage"]["by_status"]["export"] = dict(
            sorted(Counter(item["export"]["status"] for item in evidence["needs"]).items())
        )
        self.resign(evidence)
        with self.assertRaises(probe.ProbeError):
            probe.validate_evidence(evidence, self.contract, self.needs_manifest)

    def test_source_hash_and_config_binding_mutations_fail_when_resigned(self):
        for mutation in ("source", "config"):
            evidence = self.evidence_fixture()
            if mutation == "source":
                evidence["source"]["source_archive"]["sha256"] = "0" * 64
            else:
                evidence["needs"][0]["configuration"]["selected_config_sha256"] = "0" * 64
            self.resign(evidence)
            with self.assertRaises(probe.ProbeError):
                probe.validate_evidence(evidence, self.contract, self.needs_manifest)

    def test_self_attested_pass_fails_even_when_resigned(self):
        evidence = self.evidence_fixture()
        evidence["readiness"].update(
            {
                "gate_status": "PASS",
                "technical_complete": True,
                "credit_eligible": True,
                "review_required": False,
            }
        )
        self.resign(evidence)
        with self.assertRaises(probe.ProbeError):
            probe.validate_evidence(evidence, self.contract, self.needs_manifest)

    def test_unpinned_review_map_cannot_resolve_context(self):
        evidence = self.evidence_fixture()
        evidence["needs"][0]["call_context"]["status"] = "reviewed_contexts_pinned"
        evidence["coverage"]["by_status"]["call_context"] = dict(
            sorted(Counter(item["call_context"]["status"] for item in evidence["needs"]).items())
        )
        self.resign(evidence)
        with self.assertRaises(probe.ProbeError):
            probe.validate_evidence(evidence, self.contract, self.needs_manifest)


class ExactInputTests(unittest.TestCase):
    def test_archive_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "source.tar.xz"
            with tarfile.open(str(archive), "w:xz") as stream:
                info = tarfile.TarInfo("linux/../../escape")
                payload = b"bad"
                info.size = len(payload)
                stream.addfile(info, io.BytesIO(payload))
            target = {
                "source_archive_filename": archive.name,
                "source_archive_bytes": archive.stat().st_size,
                "source_archive_sha256": probe.sha256_file(archive),
                "source_archive_root": "linux",
            }
            with self.assertRaises(probe.ProbeError):
                probe.validate_archive(archive, target)

    def test_small_source_tree_must_byte_match_locked_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "linux-demo.tar.xz"
            srpm = root / "kernel.src.rpm"
            srpm.write_bytes(b"srpm")
            with tarfile.open(str(archive), "w:xz") as stream:
                info = tarfile.TarInfo("linux-demo/Makefile")
                payload = b"VERSION = 1\n"
                info.size = len(payload)
                stream.addfile(info, io.BytesIO(payload))
            source_parent = root / "source"
            source_parent.mkdir()
            with tarfile.open(str(archive), "r:xz") as stream:
                stream.extractall(str(source_parent))
            source_root = source_parent / "linux-demo"
            contract = {
                "target": {
                    "source_rpm_filename": srpm.name,
                    "source_rpm_bytes": srpm.stat().st_size,
                    "source_rpm_sha256": probe.sha256_file(srpm),
                    "source_archive_filename": archive.name,
                    "source_archive_bytes": archive.stat().st_size,
                    "source_archive_sha256": probe.sha256_file(archive),
                    "source_archive_root": "linux-demo",
                },
                "source_patch_contract": {"patches": []},
            }
            captured = probe.source_capture(
                srpm, archive, source_root, root, contract
            )
            self.assertTrue(captured["exact_locked_replay"])
            (source_root / "Makefile").write_text("VERSION = 2\n", encoding="utf-8")
            with self.assertRaises(probe.ProbeError):
                probe.source_capture(srpm, archive, source_root, root, contract)

    def test_applied_repository_patch_is_part_of_exact_source_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "linux-demo.tar.xz"
            srpm = root / "kernel.src.rpm"
            patch_path = root / "compat.patch"
            srpm.write_bytes(b"srpm")
            with tarfile.open(str(archive), "w:xz") as stream:
                info = tarfile.TarInfo("linux-demo/value")
                payload = b"old\n"
                info.size = len(payload)
                stream.addfile(info, io.BytesIO(payload))
            patch_path.write_text(
                "--- a/value\n+++ b/value\n@@ -1 +1 @@\n-old\n+new\n",
                encoding="utf-8",
            )
            source_parent = root / "source"
            source_parent.mkdir()
            with tarfile.open(str(archive), "r:xz") as stream:
                stream.extractall(str(source_parent))
            source_root = source_parent / "linux-demo"
            contract = {
                "target": {
                    "source_rpm_filename": srpm.name,
                    "source_rpm_bytes": srpm.stat().st_size,
                    "source_rpm_sha256": probe.sha256_file(srpm),
                    "source_archive_filename": archive.name,
                    "source_archive_bytes": archive.stat().st_size,
                    "source_archive_sha256": probe.sha256_file(archive),
                    "source_archive_root": "linux-demo",
                },
                "source_patch_contract": {
                    "patches": [
                        {
                            "applied": True,
                            "empty": False,
                            "path": "repository/compat.patch",
                            "sha256": probe.sha256_file(patch_path),
                            "size": patch_path.stat().st_size,
                        }
                    ]
                },
            }
            probe.run_checked(
                ["patch", "-p1", "--batch", "--forward", "-i", str(patch_path)],
                source_root,
            )
            captured = probe.source_capture(
                srpm, archive, source_root, root, contract
            )
            self.assertTrue(captured["exact_locked_replay"])
            self.assertEqual(captured["patches"][0]["sha256"], probe.sha256_file(patch_path))
            (source_root / "value").write_text("old\n", encoding="utf-8")
            with self.assertRaises(probe.ProbeError):
                probe.source_capture(srpm, archive, source_root, root, contract)

    def test_capture_cli_requires_exact_inputs(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / probe.SCRIPT_PATH),
                "--repo",
                str(REPO_ROOT),
                "capture",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"required", completed.stderr)


if __name__ == "__main__":
    unittest.main()
