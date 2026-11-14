#!/usr/bin/env python3
"""Fail-closed tests for the RS-001 exact Linux API evidence probe."""

from __future__ import print_function

import ast
import copy
import io
import json
import shutil
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

    def copy_rust_compatibility_inputs(self, root):
        for relative in list(probe.RUST_COMPAT_PATCH_PATHS) + [
            probe.RUST_COMPAT_FIXTURE_PATH
        ]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((REPO_ROOT / relative).read_bytes())
        shutil.copytree(
            str(REPO_ROOT / probe.RUST_CORE_COMPAT_FIXTURE_ROOT),
            str(root / probe.RUST_CORE_COMPAT_FIXTURE_ROOT),
        )

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
            [row["stable_commit"] for row in compatibility],
            list(probe.RUST_COMPAT_STABLE_COMMITS),
        )
        self.assertIsNone(compatibility[-1]["upstream_commit"])
        self.assertIsNone(compatibility[-1]["stable_commit"])
        self.assertEqual(
            compatibility[20],
            {
                "applied_after": str(probe.RUST_COMPAT_PATCH_PATHS[19]),
                "path": str(probe.RUST_COMPAT_PATCH_PATHS[20]),
                "sha256": probe.sha256_file(
                    REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[20]
                ),
                "size": (
                    REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[20]
                ).stat().st_size,
                "stable_commit": None,
                "upstream_commit": None,
                "integration_status": probe.MISCDEVICE_OWNER_INTEGRATION_STATUS,
                "license": probe.MISCDEVICE_OWNER_LICENSE,
                "local_origin": probe.MISCDEVICE_OWNER_LOCAL_ORIGIN,
                "rocky_base": probe.MISCDEVICE_OWNER_ROCKY_BASE,
            },
        )
        self.assertEqual(
            compatibility[-3]["preimage"]["sha256"],
            probe.RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S[0][1],
        )
        self.assertEqual(
            compatibility[-3]["postimage"]["sha256"],
            probe.RUST_OBJTOOL_NORETURN_POSTIMAGE_SHA256S[0][1],
        )
        self.assertEqual(
            compatibility[-3]["observed_failure"],
            probe.RUST_OBJTOOL_NORETURN_FAILURE_EVIDENCE,
        )
        self.assertEqual(
            compatibility[-2],
            {
                "applied_after": str(probe.RUST_COMPAT_PATCH_PATHS[-3]),
                "path": str(probe.RUST_COMPAT_PATCH_PATHS[-2]),
                "sha256": probe.sha256_file(
                    REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[-2]
                ),
                "size": (
                    REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[-2]
                ).stat().st_size,
                "stable_commit": None,
                "upstream_commit": None,
                "failure_evidence": dict(probe.PVH_OBJTOOL_FAILURE_EVIDENCE),
                "license": "GPL-2.0-only",
                "local_origin": probe.PVH_OBJTOOL_LOCAL_ORIGIN,
                "rocky_base": probe.PVH_OBJTOOL_ROCKY_BASE,
            },
        )
        self.assertEqual(
            compatibility[-1],
            {
                "applied_after": str(probe.RUST_COMPAT_PATCH_PATHS[-2]),
                "path": str(probe.RUST_COMPAT_PATCH_PATHS[-1]),
                "sha256": probe.sha256_file(
                    REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[-1]
                ),
                "size": (
                    REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[-1]
                ).stat().st_size,
                "stable_commit": None,
                "upstream_commit": None,
                "failure_evidence": dict(
                    probe.RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE
                ),
                "license": "GPL-2.0-only",
                "linux_reference": dict(
                    probe.RUST_ALLOC_SHIM_V2_LINUX_REFERENCE
                ),
                "local_origin": probe.RUST_ALLOC_SHIM_V2_LOCAL_ORIGIN,
                "postimages": [
                    dict(row) for row in probe.RUST_ALLOC_SHIM_V2_POSTIMAGES
                ],
                "preimages": [
                    dict(row) for row in probe.RUST_ALLOC_SHIM_V2_PREIMAGES
                ],
                "rocky_base": probe.RUST_ALLOC_SHIM_V2_ROCKY_BASE,
                "rust_reference": dict(
                    probe.RUST_ALLOC_SHIM_V2_RUST_REFERENCE
                ),
            },
        )
        self.assertEqual(
            generated["repository_inputs"]["rust_target_generator_preimage"],
            {
                "path": str(probe.RUST_COMPAT_FIXTURE_PATH),
                "sha256": probe.RUST_COMPAT_FIXTURE_SHA256,
            },
        )
        self.assertEqual(
            generated["source_patch_contract"]["patches"][-len(compatibility):],
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
        self.assertEqual(
            generated["repository_inputs"]["rust_core_build_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.RUST_CORE_COMPAT_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["rust_core_compatibility_failure_evidence"],
            [dict(row) for row in probe.RUST_CORE_COMPAT_FAILURE_EVIDENCE],
        )
        self.assertEqual(
            9129770822,
            generated["rust_core_compatibility_failure_evidence"][1][
                "artifact_id"
            ],
        )
        self.assertEqual(
            generated["repository_inputs"]["rust_bindings_build_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.RUST_BINDINGS_COMPAT_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["rust_uapi_compatibility_failure_evidence"],
            [dict(row) for row in probe.RUST_UAPI_COMPAT_FAILURE_EVIDENCE],
        )
        self.assertEqual(
            9130600533,
            generated["rust_uapi_compatibility_failure_evidence"][1][
                "artifact_id"
            ],
        )
        self.assertEqual(
            generated["repository_inputs"]["rust_1_89_build_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.RUST_1_89_COMPAT_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["repository_inputs"]["rust_1_92_reconciliation_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.RUST_1_92_RECONCILIATION_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["rust_kernel_1_92_reconciliation_failure_evidence"],
            [
                dict(row)
                for row in probe.RUST_KERNEL_1_92_RECONCILIATION_FAILURE_EVIDENCE
            ],
        )
        self.assertEqual(
            generated["repository_inputs"]["rust_objtool_noreturn_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["rust_objtool_noreturn_failure_evidence"],
            probe.RUST_OBJTOOL_NORETURN_FAILURE_EVIDENCE,
        )
        self.assertEqual(
            9131625436,
            generated["rust_kernel_1_92_reconciliation_failure_evidence"][1][
                "artifact_id"
            ],
        )
        self.assertEqual(
            generated["repository_inputs"]["clang_21_warning_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.CLANG_21_WARNING_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["clang_21_default_const_failure_evidence"],
            [dict(row) for row in probe.CLANG_21_DEFAULT_CONST_FAILURE_EVIDENCE],
        )
        self.assertEqual(
            9132598094,
            generated["clang_21_default_const_failure_evidence"][1]["artifact_id"],
        )
        self.assertEqual(
            generated["openssl_tool_closure_failure_evidence"],
            [dict(row) for row in probe.OPENSSL_TOOL_CLOSURE_FAILURE_EVIDENCE],
        )
        self.assertEqual(
            9133510114,
            generated["openssl_tool_closure_failure_evidence"][1]["artifact_id"],
        )
        self.assertEqual(
            generated["repository_inputs"]["clang_21_source_fix_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.CLANG_21_SOURCE_FIX_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["clang_21_source_failure_evidence"],
            [dict(row) for row in probe.CLANG_21_SOURCE_FAILURE_EVIDENCE],
        )
        self.assertEqual(
            "6059a00d15cd68b834ede0e9c28e28d934bdd071",
            generated["clang_21_source_failure_evidence"][0][
                "repository_commit"
            ],
        )
        self.assertEqual(
            9134206857,
            generated["clang_21_source_failure_evidence"][1]["artifact_id"],
        )
        self.assertEqual(
            generated["repository_inputs"]["pvh_objtool_compatibility_preimages"],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in probe.PVH_OBJTOOL_COMPAT_PREIMAGE_SHA256S
            ],
        )
        self.assertEqual(
            generated["repository_inputs"][
                "rust_alloc_shim_v2_fixture_preimages"
            ],
            [
                {
                    "path": str(probe.RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in (
                    probe.RUST_ALLOC_SHIM_V2_FIXTURE_PREIMAGE_SHA256S
                )
            ],
        )
        self.assertEqual(
            generated["rust_alloc_shim_v2_failure_evidence"],
            probe.RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE,
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
        self.assertIn("openssl openssl-devel", workflow)
        self.assertIn('openssl_path="$(command -v openssl)"', workflow)
        self.assertIn('test "$openssl_path" = /usr/bin/openssl', workflow)
        self.assertIn("rpm -qf --qf '%{NAME}\\n' \"$openssl_path\"", workflow)
        self.assertIn("openssl version", workflow)

        import yaml

        parsed = yaml.safe_load(workflow)
        for job in parsed["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run")
                if script:
                    completed = subprocess.run(
                        ["bash", "-n"],
                        input=script.encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        "{}: {}".format(
                            step.get("name", "unnamed step"),
                            completed.stderr.decode("utf-8", errors="replace"),
                        ),
                    )
        self.assertIn(
            ("openssl", ("openssl", "version")),
            probe.TOOL_PROBES,
        )
        rocky_patch = '-i "$RS001_SOURCE_ASSETS/1000-debrand-some-messages.patch"'
        compatibility_patch = '-i "$compat_asset"'
        self.assertIn("--fuzz=0 --no-backup-if-mismatch", workflow)
        for path in probe.RUST_COMPAT_PATCH_PATHS:
            self.assertIn(path.name, workflow)
        self.assertLess(workflow.index(rocky_patch), workflow.index(compatibility_patch))
        self.assertLess(workflow.index(compatibility_patch), workflow.index("rustavailable"))
        self.assertIn("scripts/rs006_miscdevice_substrate.py", workflow)
        self.assertIn("--require-source-replay", workflow)
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[0].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[1].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[1].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[2].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[2].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[3].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[3].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[4].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[4].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[5].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[5].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[6].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[6].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[7].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[7].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[8].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[8].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[9].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[9].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[10].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[10].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[11].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[11].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[12].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[12].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[13].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[13].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[14].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[14].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[15].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[15].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[16].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[16].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[17].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[17].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[18].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[18].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[19].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[19].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[20].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[20].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[21].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[21].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[22].name),
        )
        self.assertLess(
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[22].name),
            workflow.index(probe.RUST_COMPAT_PATCH_PATHS[23].name),
        )
        self.assertEqual(
            workflow.count(probe.RUST_COMPAT_PATCH_PATHS[20].name),
            2,
        )
        self.assertEqual(
            workflow.count(probe.RUST_COMPAT_PATCH_PATHS[21].name),
            2,
        )
        self.assertEqual(
            workflow.count(probe.RUST_COMPAT_PATCH_PATHS[22].name),
            2,
        )
        self.assertEqual(
            workflow.count(probe.RUST_COMPAT_PATCH_PATHS[23].name),
            2,
        )

    def test_rust_compatibility_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[3]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[3]
            path.write_text(
                original.replace(
                    "rustc-min-version,108700",
                    "rustc-min-version,108600",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_unnecessary_transmutes_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[4]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[4]
            path.write_text(
                original.replace(
                    "RUSTC_VERSION >= 108800",
                    "RUSTC_VERSION >= 108900",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_pin_data_dead_code_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[5]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[5]
            path.write_text(
                original.replace(
                    "+        #[allow(dead_code)]",
                    "+        #[allow(unused)]",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_used_compiler_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[6]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[6]
            path.write_text(
                original.replace(
                    "+rust_allowed_features := new_uninit,used_with_arg",
                    "+rust_allowed_features := new_uninit",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_receiver_reconciliation_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[7]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[7]
            path.write_text(
                original.replace(
                    "+#![feature(arbitrary_self_types)]",
                    "+#![feature(receiver_trait)]",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_block_reconciliation_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[8]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[8]
            path.write_text(
                original.replace(
                    "+                    flags: 0,",
                    "+                    flags: 1,",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_block_reconciliation_requires_exact_c_header_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            header = root / probe.RUST_CORE_COMPAT_FIXTURE_ROOT / "include/linux/blk-mq.h"
            header.write_bytes(header.read_bytes() + b"\n#define BLK_MQ_F_SHOULD_MERGE 1\n")
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_clang_21_warning_policy_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[9]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[9]
            path.write_text(
                original.replace(
                    "+KBUILD_CFLAGS += $(call cc-disable-warning, "
                    "default-const-init-unsafe)",
                    "+KBUILD_CFLAGS += -Wno-default-const-init-field-unsafe",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_clang_21_ksm_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[10]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[10]
            path.write_text(
                original.replace(
                    "+\telse\n+\t\toutput = \"[none] scan-time\";",
                    "+\telse if (ksm_advisor == KSM_ADVISOR_NONE)\n"
                    "+\t\toutput = \"[none] scan-time\";",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_clang_21_netfs_patch_shape_is_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[11]).read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[11]
            path.write_text(
                original.replace(" __nonstring = \"-PAEW\"", " = \"-PAEW\"", 1),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_stable_warning_policy_chain_shape_is_fail_closed(self):
        mutations = (
            (14, "-Wno-error=unterminated-string-initialization", "-Wno-error"),
            (15, "-Wno-unterminated-string-initialization", "-Wno-unused"),
            (16, "$(call cc-disable-warning, stringop-overflow)", "-Wno-stringop-overflow"),
            (17, "+KBUILD_CFLAGS += -Wextra", "+KBUILD_CFLAGS += -Wall"),
        )
        for index, old, new in mutations:
            with self.subTest(patch=probe.RUST_COMPAT_PATCH_PATHS[index].name):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.copy_rust_compatibility_inputs(root)
                    path = root / probe.RUST_COMPAT_PATCH_PATHS[index]
                    original = path.read_text(encoding="utf-8")
                    self.assertIn(old, original)
                    path.write_text(original.replace(old, new, 1), encoding="utf-8")
                    with self.assertRaises(probe.ProbeError):
                        probe.rust_compatibility_patch_records(root)

    def test_stable_warning_policy_provenance_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[14]
            original = path.read_text(encoding="utf-8")
            stable = probe.RUST_COMPAT_STABLE_COMMITS[14]
            self.assertEqual(2, original.count(stable))
            path.write_text(original.replace(stable, "0" * 40, 1), encoding="utf-8")
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_miscdevice_substrate_shape_is_fail_closed(self):
        mutations = (
            (18, "pub fn try_ffi_init<E>", "pub fn ffi_init<E>"),
            (
                19,
                "result.minor = bindings::MISC_DYNAMIC_MINOR as _;",
                "result.minor = 64;",
            ),
            (20, "owner: T::MODULE.as_ptr()", "owner: core::ptr::null_mut()"),
            (20, "active ordered Rocky compatibility patch", "candidate only"),
        )
        for index, old, new in mutations:
            with self.subTest(patch=probe.RUST_COMPAT_PATCH_PATHS[index].name):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.copy_rust_compatibility_inputs(root)
                    path = root / probe.RUST_COMPAT_PATCH_PATHS[index]
                    original = path.read_text(encoding="utf-8")
                    self.assertIn(old, original)
                    path.write_text(original.replace(old, new, 1), encoding="utf-8")
                    with self.assertRaises(probe.ProbeError):
                        probe.rust_compatibility_patch_records(root)

    def test_objtool_noreturn_shape_and_observed_provenance_are_fail_closed(self):
        original = (REPO_ROOT / probe.RUST_COMPAT_PATCH_PATHS[21]).read_text(
            encoding="utf-8"
        )
        for old, new in (
            ("panic_const23panic_const_", "panic_const22panic_const_"),
            ("Observed-Run-ID: 31644047766", "Observed-Run-ID: 1"),
            ("Observed-Rustc: 1.92.0", "Observed-Rustc: 1.91.0"),
        ):
            with self.subTest(field=old):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.copy_rust_compatibility_inputs(root)
                    path = root / probe.RUST_COMPAT_PATCH_PATHS[21]
                    path.write_text(original.replace(old, new, 1), encoding="utf-8")
                    with self.assertRaises(probe.ProbeError):
                        probe.rust_compatibility_patch_records(root)

    def test_pvh_objtool_patch_shape_and_provenance_are_fail_closed(self):
        mutations = (
            ("+\tANNOTATE_NOENDBR", "+\tENDBR"),
            ("Failure-Artifact: 9145918955", "Failure-Artifact: 0"),
            (
                "Failure-Log-SHA256: "
                "614f179c466c2721817fbc9b44c1dbaa9e45f4d638ed489e2b31c2c5beb69f6f",
                "Failure-Log-SHA256: " + "0" * 64,
            ),
            (
                "absolute relocation as part of a broader PVH cleanup",
                "annotation from upstream commit",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.copy_rust_compatibility_inputs(root)
                    path = root / probe.RUST_COMPAT_PATCH_PATHS[22]
                    original = path.read_text(encoding="utf-8")
                    self.assertIn(old, original)
                    path.write_text(original.replace(old, new, 1), encoding="utf-8")
                    with self.assertRaises(probe.ProbeError):
                        probe.rust_compatibility_patch_records(root)

    def test_pvh_objtool_fixture_digest_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            fixture = (
                root
                / probe.RUST_CORE_COMPAT_FIXTURE_ROOT
                / "arch/x86/platform/pvh/head.S"
            )
            fixture.write_bytes(fixture.read_bytes() + b"\n")
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_pvh_objtool_patch_replays_at_zero_fuzz_and_rejects_second_apply(self):
        records = probe.rust_compatibility_patch_records(REPO_ROOT)
        probe.verify_rust_compatibility_patch_replay(REPO_ROOT, records)

    def test_allocator_shim_patch_shape_and_provenance_are_fail_closed(self):
        mutations = (
            (
                "+fn __rust_no_alloc_shim_is_unstable_v2() {}",
                "+fn __rust_no_alloc_shim_is_unstable_v3() {}",
            ),
            (
                "+#![allow(internal_features)]",
                "+#![allow(warnings)]",
            ),
            ("Observed-Run-ID: 32082343363", "Observed-Run-ID: 1"),
            ("Rust-Reference-PR: 141061", "Rust-Reference-PR: 1"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.copy_rust_compatibility_inputs(root)
                    path = root / probe.RUST_COMPAT_PATCH_PATHS[23]
                    original = path.read_text(encoding="utf-8")
                    self.assertIn(old, original)
                    path.write_text(original.replace(old, new, 1), encoding="utf-8")
                    with self.assertRaises(probe.ProbeError):
                        probe.rust_compatibility_patch_records(root)

    def test_allocator_shim_fixture_digest_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            fixture = (
                root
                / probe.RUST_CORE_COMPAT_FIXTURE_ROOT
                / "rust/kernel/alloc/allocator.rs"
            )
            fixture.write_bytes(fixture.read_bytes() + b"\n")
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_stable_warning_policy_release_binding_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            path = root / probe.RUST_COMPAT_PATCH_PATHS[15]
            original = path.read_text(encoding="utf-8")
            path.write_text(
                original.replace("Stable-First-Release: v6.12.31", "v6.12.30", 1),
                encoding="utf-8",
            )
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_stable_warning_policy_fixture_digest_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            fixture = root / probe.RUST_CORE_COMPAT_FIXTURE_ROOT / "Makefile"
            fixture.write_bytes(fixture.read_bytes() + b"\n")
            with self.assertRaises(probe.ProbeError):
                probe.rust_compatibility_patch_records(root)

    def test_clang_21_source_fixture_digest_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_rust_compatibility_inputs(root)
            fixture = (
                root
                / probe.RUST_CORE_COMPAT_FIXTURE_ROOT
                / "fs/netfs/fscache_cookie.c"
            )
            fixture.write_bytes(fixture.read_bytes() + b"\n")
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

    def test_source_replay_rejects_a_patch_that_requires_fuzz(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "linux-demo.tar.xz"
            srpm = root / "kernel.src.rpm"
            patch_path = root / "fuzzy.patch"
            srpm.write_bytes(b"srpm")
            with tarfile.open(str(archive), "w:xz") as stream:
                info = tarfile.TarInfo("linux-demo/value")
                payload = b"context\nold\n"
                info.size = len(payload)
                stream.addfile(info, io.BytesIO(payload))
            patch_path.write_text(
                "--- a/value\n+++ b/value\n@@ -1,2 +1,2 @@\n-wrong-context\n-old\n+wrong-context\n+new\n",
                encoding="utf-8",
            )
            source_parent = root / "source"
            source_parent.mkdir()
            with tarfile.open(str(archive), "r:xz") as stream:
                stream.extractall(str(source_parent))
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
                            "path": "repository/fuzzy.patch",
                            "sha256": probe.sha256_file(patch_path),
                            "size": patch_path.stat().st_size,
                        }
                    ]
                },
            }
            with self.assertRaises(probe.ProbeError):
                probe.source_capture(
                    srpm,
                    archive,
                    source_parent / "linux-demo",
                    root,
                    contract,
                )

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
