#!/usr/bin/env python3
"""Adversarial tests for the bounded RK-005 config/build bridge review."""

from __future__ import print_function

import ast
import copy
import hashlib
import json
import os
import subprocess
import struct
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rocky_kernel_rk005_build_bridge_review as reviewer


MANIFEST = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk005-config-build-bridge-ef58-v1.json"
)
DEFAULT_CONFIG_ARTIFACT = Path(
    "/workspace/scratch/1962bd8160f6/ci-evidence/ef58860e/"
    "rk005-config-resolution-v2-32192198982-1.zip"
)
DEFAULT_BUILD_ARTIFACT = Path(
    "/workspace/scratch/1962bd8160f6/ci-evidence/ef58860e/"
    "native-rust-exact-build-32192199024-1.zip"
)


class Rk005ConfigBuildBridgeReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review_bytes = MANIFEST.read_bytes()
        cls.review = reviewer.read_canonical_json(cls.review_bytes, "checked review")

    def artifact_path(self, environment_name, default):
        configured = os.environ.get(environment_name)
        candidate = Path(configured) if configured else default
        if not candidate.is_file():
            self.skipTest("exact artifact is not materialized: {0}".format(candidate))
        return candidate

    def config_artifact_path(self):
        return self.artifact_path("MCKERNEL_RK005_CONFIG_V2_ARTIFACT", DEFAULT_CONFIG_ARTIFACT)

    def build_artifact_path(self):
        return self.artifact_path("MCKERNEL_RK007_V2_ARTIFACT", DEFAULT_BUILD_ARTIFACT)

    def exact_configs(self):
        with zipfile.ZipFile(str(self.config_artifact_path()), "r") as archive:
            policy = archive.read(reviewer.POLICY_CONFIG["path"])
        with zipfile.ZipFile(str(self.build_artifact_path()), "r") as archive:
            built = archive.read(reviewer.BUILD_CONFIG["path"])
        return policy, built

    def test_manifest_is_canonical_digest_locked_and_valid(self):
        self.assertEqual(
            hashlib.sha256(self.review_bytes).hexdigest(), reviewer.REVIEW_SHA256
        )
        self.assertEqual(self.review_bytes, reviewer.canonical_bytes(self.review))
        self.assertEqual(reviewer.validate_review(copy.deepcopy(self.review)), self.review)

    def test_nested_oracle_implementations_have_exact_checker_bindings(self):
        for name, (expected_size, expected_sha256) in sorted(
            reviewer.ORACLE_BINDINGS.items()
        ):
            with self.subTest(name=name):
                data = (SCRIPTS / name).read_bytes()
                self.assertEqual(len(data), expected_size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_sha256)
        self.assertEqual(
            reviewer.BUILD_ORACLE.REUSED_MODULE_SOURCES["kconfig_solver"],
            "git-blob:8211d19c56c56368718fe1420937fd5187530773",
        )
        self.assertEqual(
            reviewer.BUILD_ORACLE.REUSED_MODULE_SOURCES["link_closure"],
            "git-blob:8b571f2c122ae8a6102e8ed83129f584701feea2",
        )

    def test_every_credit_gate_durability_and_production_claim_is_false(self):
        for name, value in sorted(self.review["claims"].items()):
            if name == "gate_claims":
                for gate, gate_value in sorted(value.items()):
                    self.assertIs(gate_value, False, gate)
            else:
                self.assertIs(value, False, name)

    def test_every_claim_mutation_is_rejected(self):
        for name in sorted(set(reviewer.CLAIMS) - {"gate_claims"}):
            with self.subTest(claim=name):
                mutated = copy.deepcopy(self.review)
                mutated["claims"][name] = True
                with self.assertRaisesRegex(reviewer.BridgeReviewError, "claims"):
                    reviewer.validate_review(mutated)
        for gate in sorted(reviewer.CLAIMS["gate_claims"]):
            with self.subTest(gate=gate):
                mutated = copy.deepcopy(self.review)
                mutated["claims"]["gate_claims"][gate] = True
                with self.assertRaisesRegex(reviewer.BridgeReviewError, "claims"):
                    reviewer.validate_review(mutated)

    def test_unknown_keys_boolean_ids_and_retargeted_identity_are_rejected(self):
        mutations = []
        unknown = copy.deepcopy(self.review)
        unknown["unknown"] = False
        mutations.append(unknown)
        boolean_id = copy.deepcopy(self.review)
        boolean_id["source_artifacts"]["config_v2"]["id"] = True
        mutations.append(boolean_id)
        head = copy.deepcopy(self.review)
        head["runtime"]["head_sha"] = "1" * 40
        mutations.append(head)
        digest = copy.deepcopy(self.review)
        digest["source_artifacts"]["native_build"]["sha256"] = "1" * 64
        mutations.append(digest)
        for mutation in mutations:
            with self.assertRaises(reviewer.BridgeReviewError):
                reviewer.validate_review(mutation)

    def test_nested_bool_integer_coercions_are_rejected(self):
        mutations = (
            (("claims", "credit_eligible"), 0),
            (("claims", "gate_claims", "RK-003"), 0),
            (("verified_facts", "projection", "nonproject_drift_count"), False),
            (("verified_facts", "projection", "stripped_bytes_equal_policy"), 1),
        )
        for path, replacement in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                current = mutated
                for key in path[:-1]:
                    current = current[key]
                current[path[-1]] = replacement
                with self.assertRaises(reviewer.BridgeReviewError):
                    reviewer.validate_review(mutated)

    def test_nonfinite_json_and_ambiguous_zip_paths_are_rejected(self):
        with self.assertRaises(reviewer.BridgeReviewError):
            reviewer.read_canonical_json(b'{"x":NaN}\n', "nonfinite")
        for name in ("", "a/./b", "a//b", "a/../b", "a\\b", "a\x00b"):
            with self.subTest(name=repr(name)):
                with self.assertRaises(reviewer.BridgeReviewError):
                    reviewer.safe_zip_name(name)

    def test_prerequisites_order_and_projection_facts_are_immutable(self):
        mutations = []
        reordered = copy.deepcopy(self.review)
        reordered["remaining_prerequisites"].reverse()
        mutations.append(reordered)
        omitted = copy.deepcopy(self.review)
        omitted["remaining_prerequisites"].pop()
        mutations.append(omitted)
        offset = copy.deepcopy(self.review)
        offset["verified_facts"]["projection"]["insertion_offset"] += 1
        mutations.append(offset)
        project = copy.deepcopy(self.review)
        project["verified_facts"]["projection"]["project_symbols"][
            "CONFIG_MCKERNEL_IHK_RUST"
        ] = "y"
        mutations.append(project)
        for mutation in mutations:
            with self.assertRaises(reviewer.BridgeReviewError):
                reviewer.validate_review(mutation)

    def test_current_repository_fails_closed_when_nested_authority_is_stale(self):
        with self.assertRaises(
            (
                reviewer.CONFIG_ORACLE.ConfigReviewV2Error,
                reviewer.BUILD_ORACLE.BuildReviewV2Error,
                reviewer.BridgeReviewError,
            )
        ) as caught:
            reviewer.validate_repository(
                REPO_ROOT, reviewer.validate_review(copy.deepcopy(self.review))
            )
        self.assertRegex(str(caught.exception), r"(?:bound|committed) input")

    def test_repository_snapshot_rejects_disagreeing_nested_authority_head(self):
        with mock.patch.object(
            reviewer.CONFIG_ORACLE,
            "validate_repository",
            return_value=reviewer.RUNTIME_HEAD,
        ):
            with self.assertRaisesRegex(reviewer.BridgeReviewError, "snapshot"):
                reviewer.validate_repository(REPO_ROOT, copy.deepcopy(self.review))

    def test_repository_validation_ignores_hostile_git_redirection_environment(self):
        hostile = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_GLOBAL": "/tmp/mckernel-rk005-hostile-gitconfig",
            "GIT_CONFIG_KEY_0": "core.useReplaceRefs",
            "GIT_CONFIG_NOSYSTEM": "0",
            "GIT_CONFIG_VALUE_0": "true",
            "GIT_DIR": "/tmp/mckernel-rk005-definitely-absent-git-dir",
            "GIT_INDEX_FILE": "/tmp/mckernel-rk005-definitely-absent-index",
            "GIT_NO_REPLACE_OBJECTS": "0",
            "GIT_WORK_TREE": "/tmp/mckernel-rk005-definitely-absent-worktree",
            "LC_ALL": "C.UTF-8",
        }
        with mock.patch.dict(os.environ, hostile, clear=False):
            with self.assertRaises(
                (
                    reviewer.CONFIG_ORACLE.ConfigReviewV2Error,
                    reviewer.BUILD_ORACLE.BuildReviewV2Error,
                    reviewer.BridgeReviewError,
                )
            ) as caught:
                reviewer.validate_repository(REPO_ROOT, copy.deepcopy(self.review))
            for name, value in hostile.items():
                self.assertEqual(os.environ.get(name), value)
        self.assertRegex(str(caught.exception), r"(?:bound|committed) input")

    def test_config_authority_path_uses_repository_symlink_containment(self):
        with mock.patch.object(
            reviewer.CONFIG_ORACLE,
            "repository_file",
            wraps=reviewer.CONFIG_ORACLE.repository_file,
        ) as resolver:
            with self.assertRaises(
                (
                    reviewer.CONFIG_ORACLE.ConfigReviewV2Error,
                    reviewer.BUILD_ORACLE.BuildReviewV2Error,
                    reviewer.BridgeReviewError,
                )
            ):
                reviewer.validate_repository(REPO_ROOT, copy.deepcopy(self.review))
        self.assertGreaterEqual(resolver.call_count, 1)
        self.assertEqual(
            resolver.call_args_list[0],
            mock.call(
                REPO_ROOT.resolve(),
                reviewer.CONFIG_REVIEW_PATH.as_posix(),
                "config authority review",
            ),
        )

    def test_config_parser_accepts_reviewed_kconfig_grammar(self):
        parsed = reviewer.parse_config(
            b'CONFIG_A=y\nCONFIG_B=m\nCONFIG_C=42\nCONFIG_D=0x2a\n'
            b'CONFIG_E="quoted value"\n# CONFIG_F is not set\n',
            "fixture",
        )
        self.assertEqual(
            parsed,
            {
                "CONFIG_A": "y", "CONFIG_B": "m", "CONFIG_C": "42",
                "CONFIG_D": "0x2a", "CONFIG_E": '"quoted value"',
                "CONFIG_F": "n",
            },
        )

    def test_config_parser_rejects_malformed_noncanonical_and_duplicate_rows(self):
        mutations = (
            b"CONFIG_A=y",
            b"CONFIG_A=y\r\n",
            b"CONFIG_A=y # injection\n",
            b"# CONFIG_A is not sett\n",
            b"CONFIG_A=y\nCONFIG_A=m\n",
            b'CONFIG_A="x\x01y"\n',
            b"THIS IS NOT KCONFIG\n",
            b"# comment only\n",
        )
        for data in mutations:
            with self.subTest(data=repr(data)):
                with self.assertRaises(reviewer.BridgeReviewError):
                    reviewer.parse_config(data, "mutant")

    def test_exact_projection_is_byte_and_semantic_closed(self):
        policy, built = self.exact_configs()
        result = reviewer.verify_projection(policy, built, copy.deepcopy(self.review))
        self.assertEqual(result["project_symbol_count"], 3)
        self.assertEqual(result["policy_config_sha256"], reviewer.POLICY_CONFIG["sha256"])
        self.assertEqual(result["build_config_sha256"], reviewer.BUILD_CONFIG["sha256"])

    def test_projection_rejects_changed_moved_duplicate_and_extra_project_bytes(self):
        policy, built = self.exact_configs()
        block_start = reviewer.INSERTION_OFFSET
        block_end = block_start + len(reviewer.MCKERNEL_BLOCK)
        mutations = (
            built.replace(b"CONFIG_MCKERNEL_IHK_RUST=m", b"CONFIG_MCKERNEL_IHK_RUST=y", 1),
            policy + reviewer.MCKERNEL_BLOCK,
            built[:block_end] + reviewer.MCKERNEL_BLOCK + built[block_end:],
            built[:block_end] + b"CONFIG_MCKERNEL_EXTRA_RUST=m\n" + built[block_end:],
        )
        for mutation in mutations:
            with self.subTest(sha256=reviewer.sha256_bytes(mutation)):
                with self.assertRaises(reviewer.BridgeReviewError):
                    reviewer.verify_projection(policy, mutation, copy.deepcopy(self.review))

    def test_projection_rejects_nonproject_policy_drift(self):
        policy, built = self.exact_configs()
        mutated_policy = policy.replace(b"CONFIG_WERROR=y", b"# CONFIG_WERROR is not set", 1)
        with self.assertRaises(reviewer.BridgeReviewError):
            reviewer.verify_projection(mutated_policy, built, copy.deepcopy(self.review))

    def test_projection_public_helper_rejects_coherently_rebound_nonproject_inputs(self):
        policy, built = self.exact_configs()
        mutated_policy = policy.replace(
            b"CONFIG_PRINTK=y", b"CONFIG_PRINTK=m", 1
        )
        mutated_build = built.replace(
            b"CONFIG_PRINTK=y", b"CONFIG_PRINTK=m", 1
        )
        self.assertEqual(
            mutated_build,
            mutated_policy[:reviewer.INSERTION_OFFSET]
            + reviewer.MCKERNEL_BLOCK
            + mutated_policy[reviewer.INSERTION_OFFSET:],
        )
        with self.assertRaisesRegex(reviewer.BridgeReviewError, "policy config"):
            reviewer.verify_projection(
                mutated_policy, mutated_build, copy.deepcopy(self.review)
            )

    def test_exact_config_artifact_verifies(self):
        data = self.config_artifact_path().read_bytes()
        policy = reviewer.verify_config_artifact_bytes(data, copy.deepcopy(self.review))
        self.assertEqual(reviewer.sha256_bytes(policy), reviewer.POLICY_CONFIG["sha256"])

    def test_config_checkpoint_and_blocker_gate_promotions_reject_after_rehash(self):
        data = self.config_artifact_path().read_bytes()
        original = reviewer.read_zip(data, reviewer.CONFIG_PATHS, "exact config")

        def update_sum(files, name):
            suffix = "  " + name
            rows = files["capture/SHA256SUMS"].decode("ascii").splitlines()
            replacement = reviewer.sha256_bytes(files["capture/" + name]) + suffix
            rows = [replacement if row.endswith(suffix) else row for row in rows]
            files["capture/SHA256SUMS"] = ("\n".join(rows) + "\n").encode("ascii")

        checkpoint_files = dict(original)
        checkpoint = json.loads(checkpoint_files["capture/checkpoint.json"])
        checkpoint["gate_claims"]["RK-005"] = True
        checkpoint_files["capture/checkpoint.json"] = reviewer.canonical_bytes(checkpoint)
        update_sum(checkpoint_files, "checkpoint.json")

        blockers_files = dict(original)
        blockers = json.loads(blockers_files["capture/blockers.json"])
        blockers["gate_claims"]["RK-005"] = True
        blockers_files["capture/blockers.json"] = reviewer.canonical_bytes(blockers)
        checkpoint = json.loads(blockers_files["capture/checkpoint.json"])
        for row in checkpoint["manifests"]:
            if row["path"] == "blockers.json":
                row["sha256"] = reviewer.sha256_bytes(
                    blockers_files["capture/blockers.json"]
                )
                row["size"] = len(blockers_files["capture/blockers.json"])
        blockers_files["capture/checkpoint.json"] = reviewer.canonical_bytes(checkpoint)
        update_sum(blockers_files, "blockers.json")
        update_sum(blockers_files, "checkpoint.json")

        for files in (checkpoint_files, blockers_files):
            with mock.patch.object(reviewer, "read_zip", return_value=files):
                with self.assertRaisesRegex(reviewer.BridgeReviewError, "gates"):
                    reviewer.verify_config_artifact_bytes(
                        data, copy.deepcopy(self.review)
                    )

    def test_config_zip_public_parser_rejects_prefix_trailer_mode_and_local_time(self):
        data = self.config_artifact_path().read_bytes()
        self.assertEqual(
            set(reviewer.read_zip(data, reviewer.CONFIG_PATHS, "exact config")),
            set(reviewer.CONFIG_PATHS),
        )
        central_start = data.find(b"PK\x01\x02")
        self.assertGreaterEqual(central_start, 0)
        local_start = data.find(b"PK\x03\x04")
        self.assertEqual(local_start, 0)
        executable = bytearray(data)
        struct.pack_into("<I", executable, central_start + 38, 0x81ED0020)
        local_time = bytearray(data)
        local_time[local_start + 10] ^= 1
        mutations = (b"x" + data, data + b"x", bytes(executable), bytes(local_time))
        for mutation in mutations:
            with self.subTest(sha256=reviewer.sha256_bytes(mutation)):
                with self.assertRaises(reviewer.BridgeReviewError):
                    reviewer.read_zip(mutation, reviewer.CONFIG_PATHS, "mutant config")

    def test_exact_native_artifact_verifies(self):
        data = self.build_artifact_path().read_bytes()
        built = reviewer.verify_build_artifact_bytes(data, copy.deepcopy(self.review))
        self.assertEqual(reviewer.sha256_bytes(built), reviewer.BUILD_CONFIG["sha256"])

    def test_exact_artifact_pair_verifies(self):
        result = reviewer.verify_artifacts(
            self.config_artifact_path(), self.build_artifact_path(), copy.deepcopy(self.review)
        )
        self.assertEqual(result["project_symbol_count"], 3)

    def test_artifact_path_leaf_and_ancestor_symlinks_are_rejected(self):
        import tempfile

        config = self.config_artifact_path()
        build = self.build_artifact_path()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            leaf = root / "config.zip"
            leaf.symlink_to(config)
            alias = root / "alias"
            alias.symlink_to(build.parent, target_is_directory=True)
            with self.assertRaises(reviewer.CONFIG_ORACLE.ConfigReviewV2Error):
                reviewer.verify_artifacts(leaf, build, copy.deepcopy(self.review))
            with self.assertRaises(reviewer.CONFIG_ORACLE.ConfigReviewV2Error):
                reviewer.verify_artifacts(config, alias / build.name, copy.deepcopy(self.review))

    def test_cli_check_fails_closed_on_stale_repository_authority(self):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "rocky_kernel_rk005_build_bridge_review.py"),
                "--repo", str(REPO_ROOT),
                "--check",
            ],
            cwd=str(REPO_ROOT),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertRegex(completed.stderr, r"(?:bound|committed) input")

    def test_cli_artifact_request_fails_closed_on_stale_repository_authority(self):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "rocky_kernel_rk005_build_bridge_review.py"),
                "--check",
                "--verify-config-artifact", str(self.config_artifact_path()),
                "--verify-build-artifact", str(self.build_artifact_path()),
            ],
            cwd=str(REPO_ROOT),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertRegex(completed.stderr, r"(?:bound|committed) input")

    def test_checker_and_tests_parse_with_python_3_6_grammar(self):
        paths = (
            SCRIPTS / "rocky_kernel_rk005_build_bridge_review.py",
            Path(__file__),
        )
        for path in paths:
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=str(path))


if __name__ == "__main__":
    unittest.main()
