#!/usr/bin/env python3
"""Adversarial tests for bounded host-module failure-flow schema v2."""

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


class BoundedClaimTests(unittest.TestCase):
    def test_direct_cli_rejects_before_sibling_import_shadow(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "host_module_failure_flows_v2.py"
            script.write_bytes(
                (REPO_ROOT / "scripts/host_module_failure_flows_v2.py").read_bytes()
            )
            sentinel = root / "hashlib.executed"
            (root / "hashlib.py").write_text(
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
            self.assertIn(b"requires the isolated failure-site", completed.stderr)
            self.assertFalse(sentinel.exists())

    def test_main_requires_fresh_authority_but_preserves_historical_lane(self):
        arguments = [
            "--repo",
            str(REPO_ROOT),
            "--failure-sites",
            "hfs.json",
            "--failure-flows",
            "v1.json",
            "--output",
            "v2.json",
        ]
        capture = {
            "coverage": {
                "c_failure_site_resolved_count": 1,
                "c_failure_site_count": 1,
            }
        }
        with mock.patch.object(
            flows_v2, "build_capture", return_value=capture
        ) as build, mock.patch.object(flows_v2, "write_capture"):
            self.assertEqual(flows_v2.main(arguments), 1)
            build.assert_not_called()
            self.assertEqual(
                flows_v2.main(arguments, repository_authority={"fresh": True}),
                0,
            )
            self.assertEqual(flows_v2.main(arguments + ["--historical-ef58"]), 0)
        self.assertIsNotNone(build.call_args_list[-1])

    def test_every_completion_and_credit_claim_remains_false(self):
        for name, value in flows_v2.ANALYSIS_CLAIM.items():
            if isinstance(value, bool):
                self.assertFalse(value, name)
        self.assertEqual(flows_v2.ANALYSIS_CLAIM["fp_0006_status"], "IN_PROGRESS")
        self.assertIn(
            "semantic_error_domains_not_proven_for_all_integer_and_pointer_values",
            flows_v2.FIXED_BLOCKERS,
        )
        self.assertIn("rust_mir_and_cfg_not_captured", flows_v2.FIXED_BLOCKERS)
        self.assertIn(
            "macro_definition_to_expansion_dataflow_not_resolved",
            flows_v2.FIXED_BLOCKERS,
        )
        self.assertFalse(flows_v2.ANALYSIS_SCOPE["module_api_reachability_proven"])
        self.assertIn("not a module/API", flows_v2.ANALYSIS_SCOPE["external_root_definition"])

    def test_function_and_source_boundaries_are_stable_and_distinct(self):
        first = flows_v2.function_boundary("mcctrl", "demo.c", "demo")
        second = flows_v2.function_boundary("mcctrl", "demo.c", "demo")
        source = flows_v2.source_boundary("mcctrl", "demo.c")
        self.assertEqual(first, second)
        self.assertNotEqual(first["id"], source["id"])
        self.assertEqual(first["kind"], "translation_unit_function_boundary")
        self.assertEqual(source["kind"], "translation_unit_source_boundary")

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(flows_v2.FlowV2Error, "duplicate JSON key"):
                flows_v2.read_json(path, "duplicate")

    def test_nonfinite_json_and_canonical_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nonfinite.json"
            path.write_text('{"ignored_nonfinite":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(flows_v2.FlowV2Error, "non-finite"):
                flows_v2.read_json(path, "nonfinite")
        with self.assertRaises(ValueError):
            flows_v2.canonical_bytes({"ignored_nonfinite": float("nan")})
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                flows_v2.write_capture(
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
            with self.assertRaisesRegex(flows_v2.FlowV2Error, "symlink"):
                flows_v2.read_json(link, "symlink")

    def test_ancestor_directory_symlink_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target_dir = root / "target"
            target_dir.mkdir()
            (target_dir / "input.json").write_text("{}\n", encoding="utf-8")
            alias_dir = root / "alias"
            alias_dir.symlink_to(target_dir, target_is_directory=True)
            with self.assertRaisesRegex(flows_v2.FlowV2Error, "symlink"):
                flows_v2.read_json(alias_dir / "input.json", "ancestor symlink")

    def test_default_fresh_mode_replays_current_head_and_rejects_retargeting(self):
        current_head = flows_v2.sites.git_head(REPO_ROOT)
        hfs = {"provenance": {"repository_commit": current_head}}
        hfs_data = flows_v2.canonical_bytes(hfs)
        hfs_file = {
            "artifact_bytes": len(hfs_data),
            "artifact_sha256": flows_v2.sha256_bytes(hfs_data),
        }
        v1 = {
            "input_failure_sites": dict(hfs_file),
            "synthetic_current_head_replay": True,
        }
        v1_data = flows_v2.canonical_bytes(v1)
        v1_file = {
            "artifact_bytes": len(v1_data),
            "artifact_sha256": flows_v2.sha256_bytes(v1_data),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build_dir = root / "build"
            kernel_dir = root / "kernel"
            build_dir.mkdir()
            kernel_dir.mkdir()
            authority = {
                "main_head": current_head,
            }
            patches = (
                mock.patch.object(
                    flows_v2.sites,
                    "capture_repository_authority",
                    return_value=authority,
                ),
                mock.patch.object(
                    flows_v2.sites,
                    "recheck_repository_authority",
                    return_value=None,
                ),
                mock.patch.object(flows_v2.sites, "build_capture", return_value=hfs),
                mock.patch.object(flows_v2.v1_flows, "build_capture", return_value=v1),
                mock.patch.object(
                    flows_v2, "validate_exact_hfs_authority", return_value=None
                ),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                mode = flows_v2.validate_input_authority(
                    REPO_ROOT,
                    build_dir,
                    kernel_dir,
                    hfs,
                    hfs_file,
                    hfs_data,
                    v1,
                    v1_file,
                    False,
                )
            self.assertEqual(mode, flows_v2.FRESH_AUTHORITY_MODE)
            with self.assertRaisesRegex(
                flows_v2.FlowV2Error, "selector must be a boolean"
            ):
                flows_v2.validate_input_authority(
                    REPO_ROOT,
                    build_dir,
                    kernel_dir,
                    hfs,
                    hfs_file,
                    hfs_data,
                    v1,
                    v1_file,
                    1,
                )

            forged_hfs = copy.deepcopy(hfs)
            forged_hfs["provenance"]["repository_commit"] = "0" * 40
            forged_data = flows_v2.canonical_bytes(forged_hfs)
            forged_file = {
                "artifact_bytes": len(forged_data),
                "artifact_sha256": flows_v2.sha256_bytes(forged_data),
            }
            forged_v1 = copy.deepcopy(v1)
            forged_v1["input_failure_sites"] = dict(forged_file)
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                with self.assertRaisesRegex(
                    flows_v2.FlowV2Error, "fresh failure-site replay differs"
                ):
                    flows_v2.validate_input_authority(
                        REPO_ROOT,
                        build_dir,
                        kernel_dir,
                        forged_hfs,
                        forged_file,
                        forged_data,
                        forged_v1,
                        v1_file,
                        False,
                    )

    def test_workflow_uses_default_fresh_mode_with_replay_directories(self):
        workflow = (
            REPO_ROOT / ".github/workflows/rust-x86_64-validation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("--authority-target failure-flows-v2", workflow)
        self.assertIn("--authority-target failure-contract-review-v2", workflow)
        self.assertIn("--authority-target failure-flows-v1", workflow)
        self.assertIn("--authority-target failure-contract-gaps", workflow)
        self.assertIn("--check-repository-authority", workflow)
        self.assertIn("host-module-repository-authority.log", workflow)
        self.assertIn('PYTHONDONTWRITEBYTECODE: "1"', workflow)
        self.assertEqual(
            workflow.count("/usr/bin/python3 -I -S -B -c"), 6
        )
        self.assertNotIn("\n                python3 -I -S -B -c", workflow)
        self.assertEqual(
            workflow.count(
                "/usr/sbin/runuser -u validator -- /usr/bin/env -i"
            ),
            6,
        )
        self.assertEqual(
            workflow.count("/usr/bin/bash --noprofile --norc -c"), 6
        )
        self.assertGreaterEqual(workflow.count("/usr/bin/env -i"), 12)
        self.assertEqual(
            workflow.count("2>&1 | /usr/bin/tee evidence/host-module-"), 6
        )
        self.assertGreaterEqual(
            workflow.count(
                'expected_head+\\":scripts/host_module_failure_sites.py\\"'
            ),
            6,
        )
        self.assertGreaterEqual(
            workflow.count(
                'expected_head=os.environ.get(\\"FP_AUTHORITY_EXPECTED_HEAD\\",\\"\\")'
            ),
            6,
        )
        self.assertIn(
            "FP_AUTHORITY_EXPECTED_HEAD: ${{ github.event_name == "
            "'workflow_dispatch'",
            workflow,
        )
        self.assertGreaterEqual(
            workflow.count("if trusted_head() != expected_head:"), 6
        )
        self.assertGreaterEqual(workflow.count("before_head=trusted_head()"), 6)
        self.assertGreaterEqual(workflow.count("final_head=trusted_head()"), 6)
        self.assertGreaterEqual(workflow.count("trusted_fork=os.fork"), 6)
        self.assertGreaterEqual(workflow.count("trusted_type=type"), 6)
        self.assertGreaterEqual(
            workflow.count(
                "trusted_type(result) is not trusted_int_type"
            ),
            6,
        )
        self.assertNotIn("operator.index", workflow)
        self.assertGreaterEqual(
            workflow.count("expected_head=expected_head"), 6
        )
        self.assertNotIn("HEAD:scripts/host_module_failure_sites.py", workflow)
        self.assertGreaterEqual(workflow.count("core.fsmonitor"), 6)
        self.assertGreaterEqual(workflow.count("core.hooksPath"), 6)
        self.assertGreaterEqual(workflow.count("PATH\\\":\\\"/usr/bin:/bin"), 6)
        self.assertIn('\\"/usr/bin/git\\"', workflow)
        self.assertIn('\\"GIT_NO_REPLACE_OBJECTS\\":\\"1\\"', workflow)
        self.assertNotIn("python3 scripts/host_module_failure_", workflow)
        self.assertNotIn("runuser -u validator -- env \\\n", workflow)
        self.assertGreaterEqual(
            workflow.count("env -u PYTHONHOME -u PYTHONPATH"), 5
        )
        self.assertIn('--build-dir "$BUILD_DIR"', workflow)
        self.assertIn('--kernel-dir "$MCKERNEL_CI_KERNEL_DIR"', workflow)
        self.assertNotIn("--historical-ef58", workflow)

    def test_absolute_workflow_python_and_bash_ignore_path_wrappers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            python_sentinel = root / "fake-python.executed"
            python_wrapper = root / "python3"
            python_wrapper.write_text(
                "#!/usr/bin/bash\n"
                "printf executed > {0}\n".format(python_sentinel),
                encoding="utf-8",
            )
            python_wrapper.chmod(0o755)
            bash_sentinel = root / "fake-bash.executed"
            bash_wrapper = root / "bash"
            bash_wrapper.write_text(
                "#!/usr/bin/python3\n"
                "open({0!r}, 'w').write('executed')\n".format(
                    str(bash_sentinel)
                ),
                encoding="utf-8",
            )
            bash_wrapper.chmod(0o755)
            environment = {"PATH": str(root) + os.pathsep + "/usr/bin:/bin"}
            python_completed = subprocess.run(
                [
                    "/usr/bin/python3",
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    "raise SystemExit(0)",
                ],
                check=False,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            bash_completed = subprocess.run(
                [
                    "/usr/bin/bash",
                    "--noprofile",
                    "--norc",
                    "-c",
                    "exit 0",
                ],
                check=False,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(
                python_completed.returncode, 0, python_completed.stderr
            )
            self.assertEqual(bash_completed.returncode, 0, bash_completed.stderr)
            self.assertFalse(python_sentinel.exists())
            self.assertFalse(bash_sentinel.exists())


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
        cls.capture = flows_v2.build_capture(
            REPO_ROOT, cls.hfs_path, cls.v1_path, historical_ef58=True
        )

    def test_exact_artifact_closes_c_roots_without_closing_fp_0006(self):
        coverage = self.capture["coverage"]
        self.assertEqual(coverage["explicit_failure_site_input_count"], 971)
        self.assertEqual(coverage["explicit_failure_site_disposition_count"], 971)
        self.assertEqual(coverage["c_failure_site_count"], 551)
        self.assertEqual(coverage["c_failure_site_resolved_count"], 551)
        self.assertEqual(coverage["c_ambiguous_failure_site_count"], 0)
        self.assertEqual(coverage["c_external_root_unresolved_count"], 0)
        self.assertEqual(coverage["c_function_count"], 1186)
        self.assertEqual(coverage["c_function_boundary_root_count"], 1186)
        self.assertEqual(coverage["failure_flow_count"], 2602)
        self.assertEqual(coverage["c_macro_definition_site_count"], 2)
        self.assertEqual(coverage["rust_failure_site_count"], 420)
        self.assertEqual(coverage["rust_mir_unresolved_site_count"], 420)
        self.assertEqual(coverage["semantic_domain_unresolved_count"], 205)
        self.assertEqual(len(self.capture["unresolved_paths"]), 625)
        self.assertEqual(self.capture["analysis_claim"], flows_v2.ANALYSIS_CLAIM)
        self.assertEqual(self.capture["analysis_scope"], flows_v2.ANALYSIS_SCOPE)
        self.assertEqual(
            self.capture["authority_mode"], flows_v2.HISTORICAL_AUTHORITY_MODE
        )

    def test_historical_mode_pins_both_archived_input_files(self):
        _, hfs_file = flows_v2.read_json(self.hfs_path, "historical HFS")
        _, v1_file = flows_v2.read_json(self.v1_path, "historical v1")
        self.assertEqual(hfs_file, flows_v2.EXPECTED_HFS_ARTIFACT)
        self.assertEqual(v1_file, flows_v2.EXPECTED_V1_FLOW_ARTIFACT)

    def test_two_logical_macro_sites_bind_exact_physical_spellings(self):
        macro_rows = [
            item
            for item in self.capture["site_dispositions"]
            if item["kind"] == "logical_macro_definition"
        ]
        self.assertEqual(len(macro_rows), 2)
        self.assertEqual(
            {
                (
                    item["macro_name"],
                    item["physical_spelling"]["line"],
                    item["physical_spelling"]["column"],
                )
                for item in macro_rows
            },
            {
                ("MCCTRL_FUTEX_X86_ATOMIC_OP1", 79, 15),
                ("MCCTRL_FUTEX_X86_ATOMIC_OP2", 101, 28),
            },
        )
        for row in macro_rows:
            self.assertEqual(
                row["analysis_entry_roots"][0]["kind"],
                "translation_unit_source_boundary",
            )

    def test_v1_claim_escalation_is_rejected(self):
        value = json.loads(self.v1_path.read_text(encoding="utf-8"))
        value["analysis_claim"]["credit_eligible"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mutated-v1.json"
            path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(flows_v2.FlowV2Error, "archived ef58860e v1"):
                flows_v2.build_capture(
                    REPO_ROOT, self.hfs_path, path, historical_ef58=True
                )

    def test_v1_bool_to_integer_claim_and_coverage_mutations_are_rejected(self):
        original = json.loads(self.v1_path.read_text(encoding="utf-8"))
        mutations = (
            ("claim", ("analysis_claim", "credit_eligible"), 0, "bounded claim"),
            ("coverage", ("coverage", "c_source_count"), False, "coverage summary"),
        )
        for name, keys, replacement, message in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                value = copy.deepcopy(original)
                value[keys[0]][keys[1]] = replacement
                path = Path(temporary) / "mutated-v1.json"
                path.write_text(
                    json.dumps(value, sort_keys=True) + "\n", encoding="utf-8"
                )
                with self.assertRaisesRegex(
                    flows_v2.FlowV2Error, "archived ef58860e v1"
                ):
                    flows_v2.build_capture(
                        REPO_ROOT, self.hfs_path, path, historical_ef58=True
                    )

    def test_each_v2_flow_identity_commits_the_exact_v1_flow_payload(self):
        v1 = json.loads(self.v1_path.read_text(encoding="utf-8"))
        v1_by_id = {item["id"]: item for item in v1["failure_flows"]}
        self.assertEqual(len(v1_by_id), len(self.capture["failure_flows"]))
        for flow in self.capture["failure_flows"]:
            expected = flows_v2.sha256_bytes(
                flows_v2.canonical_bytes(v1_by_id[flow["v1_failure_flow_id"]])
            )
            self.assertEqual(flow["v1_failure_flow_sha256"], expected)

    def test_coherently_rebound_hfs_and_v1_with_nonfinite_value_are_rejected(self):
        hfs = json.loads(self.hfs_path.read_text(encoding="utf-8"))
        hfs["ignored_nonfinite"] = float("nan")
        hfs_bytes = (
            json.dumps(hfs, allow_nan=True, sort_keys=True) + "\n"
        ).encode("utf-8")
        v1 = json.loads(self.v1_path.read_text(encoding="utf-8"))
        v1["input_failure_sites"]["artifact_bytes"] = len(hfs_bytes)
        v1["input_failure_sites"]["artifact_sha256"] = flows_v2.sha256_bytes(
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
            with self.assertRaisesRegex(flows_v2.FlowV2Error, "non-finite"):
                flows_v2.build_capture(
                    REPO_ROOT, hfs_path, v1_path, historical_ef58=True
                )

    def test_all_coherently_rebound_hfs_authority_mutations_are_rejected(self):
        original_hfs = json.loads(self.hfs_path.read_text(encoding="utf-8"))
        original_v1 = json.loads(self.v1_path.read_text(encoding="utf-8"))

        def add_top_level(value):
            value["ignored_extra"] = "forged"

        def add_nested(value):
            value["sources"][0]["digests"]["ignored_extra"] = "forged"

        def change_expression(value):
            value["failure_sites"][0]["expression"] += "_FORGED"

        def change_line_digest(value):
            value["failure_sites"][0]["line_sha256"] = "0" * 64

        def change_compiler(value):
            value["sources"][0]["compile_argv"][0] = "/bin/forged-compiler"

        def change_inventory(value):
            value["provenance"]["frozen_inventory"]["sha256"] = "0" * 64

        def change_ihk_commit(value):
            value["provenance"]["ihk_commit"] = "0" * 40

        def change_repository_commit(value):
            value["provenance"]["repository_commit"] = "0" * 40

        mutations = (
            ("unknown top-level key", add_top_level),
            ("unknown nested key", add_nested),
            ("failure-site expression", change_expression),
            ("failure-site line digest", change_line_digest),
            ("compiler argv executable", change_compiler),
            ("inventory provenance", change_inventory),
            ("IHK commit", change_ihk_commit),
            ("repository commit", change_repository_commit),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                hfs = copy.deepcopy(original_hfs)
                mutate(hfs)
                hfs_bytes = (
                    json.dumps(hfs, allow_nan=False, sort_keys=True) + "\n"
                ).encode("utf-8")
                v1 = copy.deepcopy(original_v1)
                v1["input_failure_sites"]["artifact_bytes"] = len(hfs_bytes)
                v1["input_failure_sites"]["artifact_sha256"] = (
                    flows_v2.sha256_bytes(hfs_bytes)
                )
                root = Path(temporary)
                hfs_path = root / "rebound-hfs.json"
                v1_path = root / "rebound-v1.json"
                hfs_path.write_bytes(hfs_bytes)
                v1_path.write_text(
                    json.dumps(v1, allow_nan=False, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    flows_v2.FlowV2Error, "archived ef58860e HFS"
                ):
                    flows_v2.build_capture(
                        REPO_ROOT, hfs_path, v1_path, historical_ef58=True
                    )


if __name__ == "__main__":
    unittest.main()
