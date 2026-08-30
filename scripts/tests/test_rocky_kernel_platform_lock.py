#!/usr/bin/env python3
"""Fail-closed tests for the RK-003 and RK-005 Rocky platform locks."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_platform_lock_v2 as platform_lock  # noqa: E402


def write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


class PlatformLockFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.toolchain, _ = platform_lock.read_json(
            REPO_ROOT / platform_lock.TOOLCHAIN_LOCK_PATH
        )
        cls.legacy_config, _ = platform_lock.read_json(
            REPO_ROOT / platform_lock.CONFIG_POLICY_V1_PATH
        )
        cls.config, _ = platform_lock.read_json(
            REPO_ROOT / platform_lock.CONFIG_POLICY_V2_PATH
        )
        cls.fragment_bytes = (
            REPO_ROOT / platform_lock.CONFIG_FRAGMENT_PATH
        ).read_bytes()

    def validate_toolchain(self, value: Optional[dict] = None) -> List[str]:
        return platform_lock.validate_toolchain_lock(
            copy.deepcopy(self.toolchain if value is None else value), REPO_ROOT
        )

    def validate_config(
        self, value: Optional[dict] = None, fragment: Optional[bytes] = None
    ) -> List[str]:
        return platform_lock.validate_config_policy(
            copy.deepcopy(self.config if value is None else value),
            self.fragment_bytes if fragment is None else fragment,
            REPO_ROOT,
        )


class ManifestParserTests(PlatformLockFixture):
    def test_checker_and_tests_avoid_post_python_3_6_syntax_and_apis(self) -> None:
        forbidden_fragments = (
            "from __future__ import " + "annotations",
            ".is_relative" + "_to(",
            ".remove" + "prefix(",
            ".remove" + "suffix(",
            "capture_" + "output=",
            "missing_" + "ok=",
        )
        forbidden_annotation_patterns = (
            r"\b(?:list|dict|set|tuple)\[[^\]]",
            r"\s\|\sNone\b",
        )
        for relative_path in (
            "scripts/rocky_kernel_platform_lock_v2.py",
            "scripts/tests/test_rocky_kernel_platform_lock.py",
        ):
            source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, source, relative_path)
            for pattern in forbidden_annotation_patterns:
                self.assertNotRegex(source, pattern, relative_path)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                platform_lock.PlatformLockError, "duplicate JSON key"
            ):
                platform_lock.read_json(path)

    def test_authoritative_cli_inputs_must_be_repository_regular_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            directory = Path(temporary)
            authoritative_paths = [
                platform_lock.TOOLCHAIN_LOCK_PATH,
                platform_lock.CONFIG_POLICY_PATH,
                platform_lock.CONFIG_FRAGMENT_PATH,
            ]
            for index, authoritative_path in enumerate(authoritative_paths):
                link = directory / ("input-%d" % index)
                link.symlink_to(REPO_ROOT / authoritative_path)
                arguments = list(authoritative_paths)
                arguments[index] = link
                with self.subTest(authoritative_path=authoritative_path):
                    with self.assertRaises(platform_lock.PlatformLockError):
                        platform_lock.load_locks(REPO_ROOT, *arguments)

        with tempfile.TemporaryDirectory() as outside:
            outside_lock = Path(outside) / "outside.json"
            outside_lock.write_bytes(
                REPO_ROOT.joinpath(platform_lock.TOOLCHAIN_LOCK_PATH).read_bytes()
            )
            with self.assertRaises(platform_lock.PlatformLockError):
                platform_lock.load_locks(
                    REPO_ROOT,
                    outside_lock,
                    platform_lock.CONFIG_POLICY_PATH,
                    platform_lock.CONFIG_FRAGMENT_PATH,
                )


class ToolchainLockTests(PlatformLockFixture):
    def test_committed_metadata_is_valid_but_rk003_is_not_gate_ready(self) -> None:
        blockers = self.validate_toolchain()
        self.assertEqual(len(blockers), 8)
        self.assertFalse(self.toolchain["gate"]["credit_eligible"])
        self.assertTrue(any(item.startswith("direct_artifacts:") for item in blockers))
        self.assertTrue(any(item.startswith("closure:") for item in blockers))
        self.assertTrue(any(item.startswith("probe_evidence:") for item in blockers))
        self.assertTrue(any(item.startswith("rustavailable_evidence:") for item in blockers))

    def test_all_twenty_direct_artifacts_are_unverified_observations(self) -> None:
        artifacts = self.toolchain["direct_artifacts"]
        self.assertEqual(len(artifacts), 20)
        self.assertEqual(
            {item["role"] for item in artifacts},
            {
                "bindgen",
                "bpftool",
                "cargo",
                "clang",
                "clippy",
                "kernel-rpm-macros",
                "kmod",
                "libclang",
                "lld",
                "llvm",
                "llvm-libs",
                "pahole",
                "pesign",
                "rpm",
                "rpm-build",
                "rpm-macros",
                "rpm-sign",
                "rust-src",
                "rustc",
                "rustfmt",
            },
        )
        for item in artifacts:
            verification = item["verification"]
            self.assertFalse(verification["metadata_observed"])
            self.assertFalse(verification["archive_verified"])
            self.assertFalse(verification["signature_verified"])
            self.assertIsNone(verification["archive_path"])
            self.assertIsNone(verification["signer_fingerprint"])

    def test_observed_checksum_or_nevra_mutation_fails_closed(self) -> None:
        for field, replacement in (
            ("sha256", "0" * 64),
            ("nevra", "rust-0:1.93.0-1.el10.x86_64"),
            ("size", self.toolchain["direct_artifacts"][0]["size"] + 1),
            ("repository_location", "Packages/r/wrong.rpm"),
        ):
            with self.subTest(field=field):
                broken = copy.deepcopy(self.toolchain)
                broken["direct_artifacts"][0][field] = replacement
                with self.assertRaises(platform_lock.PlatformLockError):
                    self.validate_toolchain(broken)

    def test_metadata_cannot_be_promoted_to_archive_or_signature_proof(self) -> None:
        for field in ("archive_verified", "signature_verified"):
            with self.subTest(field=field):
                broken = copy.deepcopy(self.toolchain)
                broken["direct_artifacts"][0]["verification"][field] = True
                with self.assertRaises(platform_lock.PlatformLockError):
                    self.validate_toolchain(broken)

        broken = copy.deepcopy(self.toolchain)
        broken["direct_artifacts"][0]["verification"]["metadata_observed"] = True
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

    def test_full_closure_is_explicitly_unknown_and_required(self) -> None:
        closure = self.toolchain["closure"]
        self.assertEqual(closure["status"], "required-missing")
        self.assertIsNone(closure["package_count"])
        self.assertIsNone(closure["unresolved_dependencies"])
        self.assertFalse(closure["all_archives_verified"])
        self.assertFalse(closure["all_signatures_verified"])
        self.assertFalse(closure["offline_install_verified"])
        self.assertEqual(
            closure["direct_nevras"],
            sorted(item["nevra"] for item in self.toolchain["direct_artifacts"]),
        )

        broken = copy.deepcopy(self.toolchain)
        broken["closure"]["package_count"] = 20
        broken["closure"]["unresolved_dependencies"] = []
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

    def test_source_spec_rust_buildrequires_gap_is_locked(self) -> None:
        observation = self.toolchain["source_spec_observation"]
        self.assertFalse(observation["rocky_rust_buildrequires_effective"])
        self.assertEqual(observation["rust_buildrequires_condition"], "0%{?fedora}")

        broken = copy.deepcopy(self.toolchain)
        broken["source_spec_observation"]["rocky_rust_buildrequires_effective"] = True
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

    def test_required_minimums_and_probes_cover_the_locked_toolchain(self) -> None:
        minimums = {
            item["role"]: item["version"]
            for item in self.toolchain["kernel_requirements"]["minimum_versions"]
        }
        self.assertEqual(
            minimums,
            {"bindgen": "0.65.1", "llvm": "13.0.1", "pahole": "1.24", "rustc": "1.78.0"},
        )
        probe_ids = {item["id"] for item in self.toolchain["required_probes"]}
        self.assertIn("libclang-via-bindgen", probe_ids)
        self.assertIn("rust-src-core", probe_ids)
        self.assertIn("rpmbuild", probe_ids)
        self.assertEqual(
            self.toolchain["rustavailable_evidence"]["command"],
            ["make", "LLVM=1", "rustavailable"],
        )

        broken = copy.deepcopy(self.toolchain)
        broken["required_probes"][0]["command"] = ["true"]
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

        broken = copy.deepcopy(self.toolchain)
        broken["required_probes"][1]["required_file"] = "/tmp/core.rs"
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

        broken = copy.deepcopy(self.toolchain)
        broken["kernel_requirements"]["minimum_versions"][0]["reason"] = "assumed"
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

        broken = copy.deepcopy(self.toolchain)
        broken["kernel_requirements"]["extra"] = True
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

    def test_missing_evidence_or_gate_credit_claim_cannot_be_faked(self) -> None:
        for evidence_id in (
            "probe_evidence",
            "rpm_build_environment_evidence",
            "rustavailable_evidence",
        ):
            with self.subTest(evidence=evidence_id):
                broken = copy.deepcopy(self.toolchain)
                broken[evidence_id]["status"] = "verified"
                with self.assertRaises(platform_lock.PlatformLockError):
                    self.validate_toolchain(broken)

        broken = copy.deepcopy(self.toolchain)
        broken["probe_evidence"]["results"] = [{"rustc": "looks good"}]
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

        broken = copy.deepcopy(self.toolchain)
        broken["rustavailable_evidence"]["exit_code"] = 0
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)

        broken = copy.deepcopy(self.toolchain)
        broken["gate"]["credit_eligible"] = True
        with self.assertRaisesRegex(platform_lock.PlatformLockError, "credit_eligible"):
            self.validate_toolchain(broken)

    def test_unknown_toolchain_fields_are_rejected(self) -> None:
        broken = copy.deepcopy(self.toolchain)
        broken["metadata_is_good_enough"] = True
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_toolchain(broken)


class ConfigPolicyTests(PlatformLockFixture):
    def test_legacy_v1_policy_remains_valid_and_v2_is_the_default(self) -> None:
        blockers = platform_lock.validate_config_policy(
            copy.deepcopy(self.legacy_config), self.fragment_bytes, REPO_ROOT
        )
        self.assertEqual(len(blockers), 3)
        self.assertFalse(self.legacy_config["gate"]["credit_eligible"])
        _, loaded, _, loaded_blockers = platform_lock.load_locks(
            REPO_ROOT, config_path=platform_lock.CONFIG_POLICY_V1_PATH
        )
        self.assertEqual(
            loaded["lock_id"],
            f"{platform_lock.LOCK_ID_PREFIX}-config-policy-v1",
        )
        self.assertEqual(len(loaded_blockers), 3)
        _, current, _, current_blockers = platform_lock.load_locks(REPO_ROOT)
        self.assertEqual(
            current["lock_id"],
            f"{platform_lock.LOCK_ID_PREFIX}-config-policy-v2",
        )
        self.assertEqual(len(current_blockers), 4)

    def test_committed_policy_is_valid_but_rk005_is_not_gate_ready(self) -> None:
        blockers = self.validate_config()
        self.assertEqual(self.config["schema_version"], 2)
        self.assertEqual(len(blockers), 4)
        self.assertEqual(
            {item.split(":", 1)[0] for item in blockers},
            {
                "build_config",
                "dependency_assertions",
                "olddefconfig_delta",
                "resolution_review",
            },
        )
        self.assertFalse(self.config["gate"]["credit_eligible"])

        broken = copy.deepcopy(self.config)
        broken["schema_version"] = 1
        with self.assertRaisesRegex(
            platform_lock.PlatformLockError, "config policy.schema_version"
        ):
            self.validate_config(broken)

    def test_v2_policy_claims_and_missing_evidence_blockers_are_exact(self) -> None:
        claim_mutations = (
            lambda policy: policy["baseline"].update(
                {
                    "normalization": (
                        policy["baseline"]["normalization"]
                        + " Except that absent and explicit n may be equivalent."
                    )
                }
            ),
            lambda policy: policy["baseline"].update(
                {"normalization": ["CONFIG_NAME=value", "explicit n"]}
            ),
            lambda policy: policy["module_version_policy"].update(
                {"policy": "R1 and R2: credit and Rocky kABI claims are allowed."}
            ),
            lambda policy: policy["module_version_policy"].update(
                {"policy": False}
            ),
            lambda policy: policy["gate"].update(
                {"policy": "Credit is not forbidden; it is allowed."}
            ),
            lambda policy: policy["gate"].update(
                {"policy": ["forbidden", "allowed"]}
            ),
        )
        for index, mutation in enumerate(claim_mutations):
            with self.subTest(claim_mutation=index):
                broken = copy.deepcopy(self.config)
                mutation(broken)
                with self.assertRaises(platform_lock.PlatformLockError):
                    self.validate_config(broken)

        for evidence_id in platform_lock.EXPECTED_CONFIG_EVIDENCE_BLOCKERS_V2:
            for replacement in (
                "This arbitrary nonempty blocker erases the locked requirement.",
                ["six configs", "2882 rows"],
                False,
            ):
                with self.subTest(
                    evidence=evidence_id, replacement_type=type(replacement).__name__
                ):
                    broken = copy.deepcopy(self.config)
                    broken["verification_evidence"][evidence_id][
                        "blocker"
                    ] = replacement
                    with self.assertRaises(platform_lock.PlatformLockError):
                        self.validate_config(broken)

    def test_v2_preserve_record_order_is_canonical(self) -> None:
        self.assertEqual(
            self.config["preserve"], platform_lock.EXPECTED_PRESERVE_RECORDS_V2
        )
        broken = copy.deepcopy(self.config)
        broken["preserve"].reverse()
        with self.assertRaisesRegex(
            platform_lock.PlatformLockError, "preserve records changed"
        ):
            self.validate_config(broken)

    def test_all_rust_kconfig_dependencies_are_explicit(self) -> None:
        self.assertEqual(
            self.config["dependency_contract"]["requirements"],
            platform_lock.EXPECTED_DEPENDENCY_REQUIREMENTS_V2,
        )
        dependencies = {
            item["symbol"]: item["expected"]
            for item in self.config["dependency_contract"]["requirements"]
        }
        self.assertEqual(dependencies, platform_lock.EXPECTED_DEPENDENCIES)
        self.assertEqual(
            dependencies["CONFIG_CALL_PADDING"],
            "runtime-check-rustc-at-least-1.81.0-if-y",
        )
        self.assertEqual(dependencies["CONFIG_MITIGATION_RETHUNK"], "y")
        self.assertEqual(dependencies["CONFIG_KASAN"], "n")

    def test_dependency_requirement_duplicates_and_source_drift_fail_closed(self) -> None:
        duplicate = copy.deepcopy(self.config)
        duplicate["dependency_contract"]["requirements"].append(
            copy.deepcopy(
                duplicate["dependency_contract"]["requirements"][0]
            )
        )
        with self.assertRaisesRegex(
            platform_lock.PlatformLockError, "dependency requirements changed"
        ):
            self.validate_config(duplicate)

        source_drift = copy.deepcopy(self.config)
        source_drift["dependency_contract"]["requirements"][0][
            "source"
        ] = "looks plausible but is not bound"
        with self.assertRaisesRegex(
            platform_lock.PlatformLockError, "dependency requirements changed"
        ):
            self.validate_config(source_drift)

    def test_generated_olddefconfig_symbols_are_separate_from_requested_delta(self) -> None:
        evidence = self.config["verification_evidence"]["olddefconfig_delta"]
        self.assertEqual(
            evidence["generated_symbol_allowlist"],
            platform_lock.EXPECTED_GENERATED_CONFIG_SYMBOLS_V2,
        )
        self.assertIn(
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES",
            evidence["generated_symbol_allowlist"],
        )
        self.assertEqual(
            evidence["generated_symbol_rules"],
            platform_lock.EXPECTED_GENERATED_SYMBOL_RULES,
        )
        self.assertIsNone(evidence["generated_symbol_results"])
        self.assertIn("control-to-resolved", evidence["blocker"])

        broken = copy.deepcopy(self.config)
        broken["verification_evidence"]["olddefconfig_delta"][
            "generated_symbol_allowlist"
        ].append("CONFIG_SAMPLE_RUST_MINIMAL")
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)

        broken = copy.deepcopy(self.config)
        broken["verification_evidence"]["olddefconfig_delta"][
            "generated_symbol_allowlist"
        ].remove("CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES")
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)

        broken = copy.deepcopy(self.config)
        broken["verification_evidence"]["olddefconfig_delta"][
            "generated_symbol_rules"
        ]["CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"]["expected"] = "n"
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)

    def test_staged_classification_and_llvm_owner_policy_are_exact(self) -> None:
        self.assertEqual(
            self.config["resolution_classification"],
            platform_lock.EXPECTED_RESOLUTION_CLASSIFICATION,
        )
        self.assertEqual(
            self.config["tool_owner_policy"]["llvm_config"],
            platform_lock.EXPECTED_LLVM_CONFIG_OWNER_POLICY,
        )
        for path, value in (
            (("resolution_classification", "complete_partition_required"), False),
            (
                (
                    "tool_owner_policy",
                    "llvm_config",
                    "expected_package_nevra",
                ),
                "llvm-0:21.1.8-1.el10.x86_64",
            ),
        ):
            with self.subTest(path=path):
                broken = copy.deepcopy(self.config)
                cursor = broken
                for key in path[:-1]:
                    cursor = cursor[key]
                cursor[path[-1]] = value
                with self.assertRaises(platform_lock.PlatformLockError):
                    self.validate_config(broken)

    def test_fragment_and_allowlist_are_exactly_two_changes(self) -> None:
        self.assertEqual(
            platform_lock.parse_kconfig(
                self.fragment_bytes.decode("utf-8"), "fragment"
            ),
            {"CONFIG_RUST": "y", "CONFIG_MODVERSIONS": "n"},
        )
        self.assertEqual(
            self.config["delta"]["allowed_symbols"],
            ["CONFIG_MODVERSIONS", "CONFIG_RUST"],
        )
        self.assertTrue(self.config["delta"]["unexpected_changes_forbidden"])

        mutated = self.fragment_bytes + b"CONFIG_SAMPLE_RUST_MINIMAL=m\n"
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(fragment=mutated)

    def test_btf_debug_info_and_module_signing_are_preserved(self) -> None:
        preserve = {item["symbol"]: item["value"] for item in self.config["preserve"]}
        expected = {
            "CONFIG_DEBUG_INFO": "y",
            "CONFIG_DEBUG_INFO_BTF": "y",
            "CONFIG_DEBUG_INFO_BTF_MODULES": "y",
            "CONFIG_MODULE_SIG": "y",
            "CONFIG_MODULE_SIG_ALL": "y",
            "CONFIG_MODULE_SIG_FORCE": "n",
            "CONFIG_MODULE_SIG_KEY": '"certs/signing_key.pem"',
            "CONFIG_MODULE_SIG_KEY_TYPE_RSA": "y",
            "CONFIG_MODULE_SIG_SHA512": "y",
        }
        for symbol, value in expected.items():
            self.assertEqual(preserve[symbol], value)
        self.assertEqual(preserve["CONFIG_WERROR"], "y")

    def test_unallowlisted_delta_or_weakened_preservation_fails_closed(self) -> None:
        broken = copy.deepcopy(self.config)
        broken["delta"]["allowed_symbols"].append("CONFIG_MODULE_SIG_FORCE")
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)

        broken = copy.deepcopy(self.config)
        entry = next(
            item for item in broken["preserve"] if item["symbol"] == "CONFIG_DEBUG_INFO_BTF"
        )
        entry["value"] = "n"
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)

        broken = copy.deepcopy(self.config)
        broken["preserve"] = [
            item for item in broken["preserve"] if item["symbol"] != "CONFIG_WERROR"
        ]
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)

    def test_modversions_policy_forbids_kabi_and_weak_updates(self) -> None:
        policy = self.config["module_version_policy"]
        self.assertEqual(policy["config_modversions"], "n")
        self.assertTrue(policy["exact_nvr_only"])
        self.assertTrue(policy["atomic_kernel_module_nvr_required"])
        self.assertTrue(policy["no_rocky_kabi_claim"])
        self.assertTrue(policy["weak_updates_forbidden"])

        for field in (
            "exact_nvr_only",
            "atomic_kernel_module_nvr_required",
            "no_rocky_kabi_claim",
            "weak_updates_forbidden",
        ):
            with self.subTest(field=field):
                broken = copy.deepcopy(self.config)
                broken["module_version_policy"][field] = False
                with self.assertRaises(platform_lock.PlatformLockError):
                    self.validate_config(broken)

    def test_exact_synthetic_resolved_delta_passes(self) -> None:
        baseline = dict(platform_lock.EXPECTED_PRESERVE_V2)
        baseline.update(
            {symbol: before for symbol, (before, _) in platform_lock.EXPECTED_CONFIG_CHANGES.items()}
        )
        resolved = dict(baseline)
        resolved.update(
            {symbol: after for symbol, (_, after) in platform_lock.EXPECTED_CONFIG_CHANGES.items()}
        )
        platform_lock.validate_resolved_config(baseline, resolved, self.config)

    def test_any_third_resolved_delta_or_preservation_drift_fails(self) -> None:
        baseline = dict(platform_lock.EXPECTED_PRESERVE_V2)
        baseline.update(
            {symbol: before for symbol, (before, _) in platform_lock.EXPECTED_CONFIG_CHANGES.items()}
        )
        resolved = dict(baseline)
        resolved.update(
            {symbol: after for symbol, (_, after) in platform_lock.EXPECTED_CONFIG_CHANGES.items()}
        )

        unexpected = dict(resolved)
        unexpected["CONFIG_MODULE_SIG_FORCE"] = "y"
        with self.assertRaisesRegex(platform_lock.PlatformLockError, "exactly allowlisted"):
            platform_lock.validate_resolved_config(baseline, unexpected, self.config)

        missing = dict(resolved)
        del missing["CONFIG_DEBUG_INFO_BTF_MODULES"]
        with self.assertRaises(platform_lock.PlatformLockError):
            platform_lock.validate_resolved_config(baseline, missing, self.config)

    def test_kconfig_parser_rejects_duplicates_and_ambiguous_n(self) -> None:
        with self.assertRaises(platform_lock.PlatformLockError):
            platform_lock.parse_kconfig(
                "CONFIG_RUST=y\nCONFIG_RUST=y\n", "duplicate"
            )
        with self.assertRaises(platform_lock.PlatformLockError):
            platform_lock.parse_kconfig("CONFIG_MODVERSIONS=n\n", "ambiguous")

    def test_missing_evidence_and_gate_credit_claim_cannot_be_faked(self) -> None:
        for evidence_id in (
            "build_config",
            "dependency_assertions",
            "olddefconfig_delta",
        ):
            with self.subTest(evidence=evidence_id):
                broken = copy.deepcopy(self.config)
                broken["verification_evidence"][evidence_id]["status"] = "verified"
                with self.assertRaises(platform_lock.PlatformLockError):
                    self.validate_config(broken)

        broken = copy.deepcopy(self.config)
        broken["verification_evidence"]["olddefconfig_delta"][
            "unexpected_symbols"
        ] = []
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)

        broken = copy.deepcopy(self.config)
        broken["gate"]["credit_eligible"] = True
        with self.assertRaisesRegex(platform_lock.PlatformLockError, "credit_eligible"):
            self.validate_config(broken)

    def test_unknown_config_policy_fields_are_rejected(self) -> None:
        broken = copy.deepcopy(self.config)
        broken["olddefconfig_warnings_are_ok"] = True
        with self.assertRaises(platform_lock.PlatformLockError):
            self.validate_config(broken)


class VerifiedEvidenceTests(PlatformLockFixture):
    def completed_config(self, directory: Path) -> dict:
        completed = copy.deepcopy(self.config)
        evidence = completed["verification_evidence"]
        final_config_sha256 = "c" * 64

        for evidence_id in ("build_config", "dependency_assertions", "olddefconfig_delta"):
            path = directory / f"{evidence_id}.json"
            digest = write_json(path, {"capture": evidence_id})
            evidence[evidence_id].update(
                {
                    "blocker": None,
                    "evidence_path": relative(path),
                    "evidence_sha256": digest,
                    "status": "verified",
                }
            )

        evidence["build_config"].update(
            {
                "build_id": "verified-build-id",
                "final_config_sha256": final_config_sha256,
                "kernel_nvr": "kernel-6.12.0-211.44.1.el10_2.mckernel1",
            }
        )
        evidence["dependency_assertions"]["results"] = copy.deepcopy(
            platform_lock.EXPECTED_DEPENDENCIES
        )
        evidence["dependency_assertions"]["preservation_results"] = copy.deepcopy(
            platform_lock.EXPECTED_PRESERVE_V2
        )
        generated = copy.deepcopy(
            platform_lock.EXPECTED_GENERATED_CONFIG_VALUES_V2
        )
        evidence["olddefconfig_delta"].update(
            {
                "baseline_config_sha256": completed["baseline"]["sha256"],
                "baseline_to_control_changes": [
                    {
                        "after": "109200",
                        "before": "n",
                        "symbol": "CONFIG_RUSTC_VERSION",
                    }
                ],
                "control_config_sha256": "3" * 64,
                "control_to_resolved_changes": [],
                "derived_changes": [
                    {
                        "after": "<absent>",
                        "before": "y",
                        "symbol": "CONFIG_ASM_MODVERSIONS",
                    }
                ],
                "requested_changes": [
                    {
                        "after": "n",
                        "before": "y",
                        "symbol": "CONFIG_MODVERSIONS",
                    },
                    {
                        "after": "y",
                        "before": "<absent>",
                        "symbol": "CONFIG_RUST",
                    },
                ],
                "requested_generated_symbols": [
                    {
                        "after": '"bindgen 0.72.1"',
                        "before": "<absent>",
                        "symbol": "CONFIG_BINDGEN_VERSION_TEXT",
                    },
                    {
                        "after": platform_lock.EXPECTED_GENERATED_CONFIG_VALUES_V2[
                            "CONFIG_RUSTC_VERSION_TEXT"
                        ],
                        "before": "<absent>",
                        "symbol": "CONFIG_RUSTC_VERSION_TEXT",
                    }
                ],
                "representation_changes": [
                    {"after": "n", "before": "<absent>", "symbol": symbol}
                    for symbol in (
                        "CONFIG_BLK_DEV_RUST_NULL",
                        "CONFIG_DRM_NOVA",
                        "CONFIG_RUST_BUILD_ASSERT_ALLOW",
                        "CONFIG_RUST_DEBUG_ASSERTIONS",
                        "CONFIG_RUST_FW_LOADER_ABSTRACTIONS",
                        "CONFIG_RUST_OVERFLOW_CHECKS",
                        "CONFIG_RUST_PHYLIB_ABSTRACTIONS",
                        "CONFIG_SAMPLES_RUST",
                    )
                ],
                "command_manifest_sha256": "1" * 64,
                "environment_manifest_sha256": "2" * 64,
                "generated_symbol_results": generated,
                "resolved_config_sha256": final_config_sha256,
                "second_control_config_sha256": "3" * 64,
                "second_pass_config_sha256": final_config_sha256,
                "unexpected_symbols": [],
            }
        )
        olddefconfig = evidence["olddefconfig_delta"]
        olddefconfig["control_to_resolved_changes"] = sorted(
            olddefconfig["requested_changes"]
            + olddefconfig["derived_changes"]
            + olddefconfig["requested_generated_symbols"]
            + olddefconfig["representation_changes"],
            key=lambda row: row["symbol"],
        )
        completed["gate"]["credit_eligible"] = False
        return completed

    def completed_toolchain(
        self, directory: Path
    ) -> Tuple[dict, Dict[Path, Tuple[int, str]]]:
        completed = copy.deepcopy(self.toolchain)
        digest_overrides: Dict[Path, Tuple[int, str]] = {}
        signature_paths: Dict[str, Path] = {}
        archive_paths: Dict[str, Path] = {}

        def signature_evidence(nevra: str, rpm_sha256: str, name: str) -> Path:
            path = directory / "signatures" / f"{name}.json"
            write_json(
                path,
                {
                    "command": ["rpmkeys", "--checksig", name],
                    "result": "PASS",
                    "rpm_sha256": rpm_sha256,
                    "schema_version": 1,
                    "signature_algorithm": "RSA/SHA256",
                    "signer_fingerprint": platform_lock.EXPECTED_RELEASE_KEY[
                        "fingerprint"
                    ],
                    "stderr_sha256": "3" * 64,
                    "stdout_sha256": "4" * 64,
                    "subject_nevra": nevra,
                    "verification_tool": "rpmkeys --checksig --verbose",
                },
            )
            return path

        for artifact in completed["direct_artifacts"]:
            archive = directory / "rpms" / artifact["repository_location"].split("/")[-1]
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(b"placeholder")
            digest_overrides[archive.resolve()] = (
                artifact["size"],
                artifact["sha256"],
            )
            signature = signature_evidence(
                artifact["nevra"], artifact["sha256"], artifact["name"]
            )
            signature_digest = hashlib.sha256(signature.read_bytes()).hexdigest()
            artifact["verification"].update(
                {
                    "archive_path": relative(archive),
                    "archive_verified": True,
                    "blocker": None,
                    "metadata_observed": True,
                    "signature_algorithm": "RSA/SHA256",
                    "signature_evidence_path": relative(signature),
                    "signature_evidence_sha256": signature_digest,
                    "signature_verified": True,
                    "signer_fingerprint": platform_lock.EXPECTED_RELEASE_KEY[
                        "fingerprint"
                    ],
                }
            )
            signature_paths[artifact["nevra"]] = signature
            archive_paths[artifact["nevra"]] = archive

        for repository in completed["repositories"]:
            retained = directory / "repositories" / repository["id"]
            files = []
            role_paths: Dict[str, Path] = {}
            for role in ("release-key", "repomd", "repomd-signature", "primary"):
                path = retained / role
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"{repository['id']} {role}\n".encode())
                role_paths[role] = path
                size = path.stat().st_size
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if role == "release-key":
                    digest = platform_lock.EXPECTED_RELEASE_KEY["sha256"]
                    digest_overrides[path.resolve()] = (size, digest)
                files.append(
                    {
                        "path": relative(path),
                        "role": role,
                        "sha256": digest,
                        "size": size,
                    }
                )
            repomd_sha256 = files[1]["sha256"]
            primary_sha256 = files[3]["sha256"]
            snapshot = retained / "snapshot.json"
            snapshot_digest = write_json(
                snapshot,
                {
                    "base_url": repository["base_url"],
                    "files": files,
                    "primary_metadata_sha256": primary_sha256,
                    "release_key_fingerprint": platform_lock.EXPECTED_RELEASE_KEY[
                        "fingerprint"
                    ],
                    "repomd_sha256": repomd_sha256,
                    "repository_id": repository["id"],
                    "schema_version": 1,
                    "signature_verified": True,
                    "verification_tool": "gpg --verify",
                },
            )
            repository.update(
                {
                    "blocker": None,
                    "metadata_observed": True,
                    "primary_metadata_sha256": primary_sha256,
                    "repomd_sha256": repomd_sha256,
                    "repomd_signature_verified": True,
                    "snapshot_evidence_path": relative(snapshot),
                    "snapshot_evidence_sha256": snapshot_digest,
                }
            )

        closure_packages = []
        rpm_rows = []
        for artifact in completed["direct_artifacts"]:
            closure_packages.append(
                {
                    "archive_path": relative(archive_paths[artifact["nevra"]]),
                    "arch": artifact["arch"],
                    "nevra": artifact["nevra"],
                    "sha256": artifact["sha256"],
                    "signature_algorithm": "RSA/SHA256",
                    "signature_evidence_path": relative(
                        signature_paths[artifact["nevra"]]
                    ),
                    "signature_evidence_sha256": hashlib.sha256(
                        signature_paths[artifact["nevra"]].read_bytes()
                    ).hexdigest(),
                    "signature_verified": True,
                    "signer_fingerprint": platform_lock.EXPECTED_RELEASE_KEY[
                        "fingerprint"
                    ],
                    "size": artifact["size"],
                }
            )
            rpm_rows.append(f"{artifact['nevra']}\t{artifact['sha256']}\n")

        dependency_nevra = "dependency-0:1-1.el10.x86_64"
        dependency_archive = directory / "rpms" / "dependency.rpm"
        dependency_archive.write_bytes(b"dependency-rpm")
        dependency_sha256 = hashlib.sha256(dependency_archive.read_bytes()).hexdigest()
        dependency_signature = signature_evidence(
            dependency_nevra, dependency_sha256, "dependency"
        )
        closure_packages.append(
            {
                "archive_path": relative(dependency_archive),
                "arch": "x86_64",
                "nevra": dependency_nevra,
                "sha256": dependency_sha256,
                "signature_algorithm": "RSA/SHA256",
                "signature_evidence_path": relative(dependency_signature),
                "signature_evidence_sha256": hashlib.sha256(
                    dependency_signature.read_bytes()
                ).hexdigest(),
                "signature_verified": True,
                "signer_fingerprint": platform_lock.EXPECTED_RELEASE_KEY[
                    "fingerprint"
                ],
                "size": dependency_archive.stat().st_size,
            }
        )
        rpm_rows.append(f"{dependency_nevra}\t{dependency_sha256}\n")
        rpm_set_sha256 = hashlib.sha256("".join(sorted(rpm_rows)).encode()).hexdigest()
        environment_sha256 = "2" * 64
        closure_manifest = directory / "closure.json"
        closure_manifest_sha256 = write_json(
            closure_manifest,
            {
                "environment_manifest_sha256": environment_sha256,
                "offline_install_result": "PASS",
                "package_count": len(closure_packages),
                "packages": closure_packages,
                "requested_direct_nevras": completed["closure"]["direct_nevras"],
                "resolution_scope": completed["closure"]["resolution_scope"],
                "rpm_set_sha256": rpm_set_sha256,
                "schema_version": 1,
                "source_spec_sha256": completed["source_spec_observation"]["sha256"],
                "unresolved_dependencies": [],
            },
        )
        completed["closure"].update(
            {
                "all_archives_verified": True,
                "all_signatures_verified": True,
                "blocker": None,
                "manifest_path": relative(closure_manifest),
                "manifest_sha256": closure_manifest_sha256,
                "offline_install_verified": True,
                "package_count": len(closure_packages),
                "rpm_set_sha256": rpm_set_sha256,
                "status": "verified",
                "unresolved_dependencies": [],
            }
        )

        probe_results = []
        artifact_by_name = {
            item["name"]: item for item in completed["direct_artifacts"]
        }
        for probe in platform_lock.expected_probe_records():
            result = {
                "binary_path": f"/usr/bin/{probe['command'][0]}",
                "binary_sha256": "5" * 64,
                "command": probe["command"],
                "exit_code": 0,
                "id": probe["id"],
                "loaded_library_path": None,
                "loaded_library_sha256": None,
                "package_nevra": artifact_by_name[probe["artifact"]]["nevra"],
                "parsed_version": probe["expected_version"],
                "required_file_path": None,
                "required_file_sha256": None,
                "stderr_sha256": "6" * 64,
                "stdout_sha256": "7" * 64,
            }
            if probe["id"] == "llvm":
                result.update(
                    {
                        "binary_path": "/usr/bin/llvm-config",
                        "package_nevra": platform_lock.EXPECTED_LLVM_CONFIG_OWNER_POLICY[
                            "expected_package_nevra"
                        ],
                    }
                )
            if probe["id"] == "rust-src-core":
                result.update(
                    {
                        "required_file_path": "/usr/lib/rustlib/src/rust/library/core/src/lib.rs",
                        "required_file_sha256": "8" * 64,
                    }
                )
            elif probe["id"] == "libclang-via-bindgen":
                result.update(
                    {
                        "loaded_library_path": "/usr/lib64/libclang.so.21.1",
                        "loaded_library_sha256": "9" * 64,
                    }
                )
            probe_results.append(result)
        probe_capture = directory / "probes.json"
        probe_capture_sha256 = write_json(probe_capture, {"results": probe_results})
        completed["probe_evidence"].update(
            {
                "blocker": None,
                "environment_manifest_sha256": environment_sha256,
                "evidence_path": relative(probe_capture),
                "evidence_sha256": probe_capture_sha256,
                "results": probe_results,
                "status": "verified",
            }
        )

        rpm_environment = directory / "rpm-environment.json"
        rpm_environment_sha256 = write_json(rpm_environment, {"result": "PASS"})
        completed["rpm_build_environment_evidence"].update(
            {
                "blocker": None,
                "buildroot_oci_digest": f"sha256:{'a' * 64}",
                "environment_manifest_sha256": environment_sha256,
                "evidence_path": relative(rpm_environment),
                "evidence_sha256": rpm_environment_sha256,
                "offline_transaction_verified": True,
                "repository_snapshot_manifest_sha256": "b" * 64,
                "rpm_macro_manifest_sha256": "d" * 64,
                "spec_rust_buildrequires_rocky_verified": True,
                "status": "verified",
            }
        )
        rustavailable = directory / "rustavailable.json"
        rustavailable_sha256 = write_json(rustavailable, {"result": "PASS"})
        completed["rustavailable_evidence"].update(
            {
                "blocker": None,
                "config_sha256": "c" * 64,
                "environment_manifest_sha256": environment_sha256,
                "evidence_path": relative(rustavailable),
                "evidence_sha256": rustavailable_sha256,
                "exit_code": 0,
                "status": "verified",
                "stderr_sha256": "e" * 64,
                "stdout_sha256": "f" * 64,
            }
        )
        completed["gate"]["credit_eligible"] = True
        return completed, digest_overrides

    def test_primary_config_evidence_cannot_bypass_independent_review(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            completed = self.completed_config(Path(temporary))
            blockers = platform_lock.validate_config_policy(
                completed, self.fragment_bytes, REPO_ROOT
            )
            self.assertEqual(len(blockers), 1)
            self.assertTrue(blockers[0].startswith("resolution_review:"))
            self.assertFalse(completed["gate"]["credit_eligible"])
            self.assertEqual(
                json.loads(
                    (
                        REPO_ROOT
                        / completed["verification_evidence"]["olddefconfig_delta"][
                            "evidence_path"
                        ]
                    ).read_text(encoding="utf-8")
                ),
                {"capture": "olddefconfig_delta"},
            )
            self.assertEqual(
                len(
                    completed["verification_evidence"]["olddefconfig_delta"][
                        "baseline_to_control_changes"
                    ]
                ),
                1,
            )
            promoted = copy.deepcopy(completed)
            promoted["verification_evidence"]["resolution_review"].update(
                {
                    "artifact_path": "arbitrary.zip",
                    "artifact_sha256": "a" * 64,
                    "blocker": None,
                    "command_manifest_sha256": "b" * 64,
                    "environment_manifest_sha256": "c" * 64,
                    "review_manifest_path": "arbitrary-review.json",
                    "review_manifest_sha256": "d" * 64,
                    "status": "verified",
                }
            )
            promoted["gate"]["credit_eligible"] = True
            with self.assertRaisesRegex(
                platform_lock.PlatformLockError,
                "schema-specific evidence validator",
            ):
                platform_lock.validate_config_policy(
                    promoted, self.fragment_bytes, REPO_ROOT
                )

    def test_verified_config_classification_owner_symbols_and_werror_fail_closed(self) -> None:
        mutations = (
            (
                "incomplete classification",
                lambda policy: policy["verification_evidence"][
                    "olddefconfig_delta"
                ]["control_to_resolved_changes"].pop(),
            ),
            (
                "transmute result",
                lambda policy: policy["verification_evidence"][
                    "olddefconfig_delta"
                ]["generated_symbol_results"].update(
                    {"CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES": "n"}
                ),
            ),
            *tuple(
                (
                    "generated value " + symbol,
                    lambda policy, name=symbol: policy["verification_evidence"][
                        "olddefconfig_delta"
                    ]["generated_symbol_results"].update({name: "verified"}),
                )
                for symbol in platform_lock.EXPECTED_GENERATED_CONFIG_SYMBOLS_V2
            ),
            (
                "WERROR preservation",
                lambda policy: policy["verification_evidence"][
                    "dependency_assertions"
                ]["preservation_results"].update({"CONFIG_WERROR": "n"}),
            ),
            (
                "control idempotence",
                lambda policy: policy["verification_evidence"][
                    "olddefconfig_delta"
                ].update({"second_control_config_sha256": "4" * 64}),
            ),
        )
        for label, mutation in mutations:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
                    completed = self.completed_config(Path(temporary))
                    mutation(completed)
                    with self.assertRaises(platform_lock.PlatformLockError):
                        platform_lock.validate_config_policy(
                            completed, self.fragment_bytes, REPO_ROOT
                        )

    def test_verified_evidence_paths_must_be_contained_regular_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            directory = Path(temporary)
            completed = self.completed_config(directory)
            evidence = completed["verification_evidence"]["dependency_assertions"]
            target = REPO_ROOT / evidence["evidence_path"]
            link = directory / "dependency-assertions-link.json"
            link.symlink_to(target)
            evidence["evidence_path"] = relative(link)
            with self.assertRaises(platform_lock.PlatformLockError):
                platform_lock.validate_config_policy(
                    completed, self.fragment_bytes, REPO_ROOT
                )

            completed = self.completed_config(directory)
            completed["verification_evidence"]["dependency_assertions"][
                "evidence_path"
            ] = "../outside-repository.json"
            with self.assertRaises(platform_lock.PlatformLockError):
                platform_lock.validate_config_policy(
                    completed, self.fragment_bytes, REPO_ROOT
                )

    def test_complete_primary_evidence_still_cannot_reach_gate_ready(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            directory = Path(temporary)
            toolchain, overrides = self.completed_toolchain(directory)
            config = self.completed_config(directory)
            toolchain_path = directory / "toolchain-lock.json"
            config_path = directory / "config-policy.json"
            write_json(toolchain_path, toolchain)
            write_json(config_path, config)
            original_sha256_file = platform_lock.sha256_file

            def synthetic_sha256(path: Path) -> Tuple[int, str]:
                return overrides.get(path.resolve(), original_sha256_file(path))

            with mock.patch.object(
                platform_lock, "sha256_file", side_effect=synthetic_sha256
            ):
                self.assertEqual(
                    platform_lock.main(
                        [
                            "--repo",
                            str(REPO_ROOT),
                            "--toolchain-lock",
                            str(toolchain_path),
                            "--config-policy",
                            str(config_path),
                            "--gate-ready",
                        ]
                    ),
                    1,
                )

    def test_llvm_probe_path_and_owner_are_exact(self) -> None:
        for field, value in (
            ("binary_path", "/usr/sbin/llvm-config"),
            ("package_nevra", "llvm-0:21.1.8-1.el10.x86_64"),
        ):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
                    toolchain, overrides = self.completed_toolchain(Path(temporary))
                    llvm = next(
                        row
                        for row in toolchain["probe_evidence"]["results"]
                        if row["id"] == "llvm"
                    )
                    llvm[field] = value
                    original_sha256_file = platform_lock.sha256_file

                    def synthetic_sha256(path: Path) -> Tuple[int, str]:
                        return overrides.get(
                            path.resolve(), original_sha256_file(path)
                        )

                    with mock.patch.object(
                        platform_lock,
                        "sha256_file",
                        side_effect=synthetic_sha256,
                    ):
                        with self.assertRaises(platform_lock.PlatformLockError):
                            platform_lock.validate_toolchain_lock(
                                toolchain, REPO_ROOT
                            )


class CommandLineTests(PlatformLockFixture):
    def test_check_succeeds_and_gate_ready_fails(self) -> None:
        self.assertEqual(
            platform_lock.main(["--repo", str(REPO_ROOT), "--check"]), 0
        )
        self.assertEqual(
            platform_lock.main(["--repo", str(REPO_ROOT), "--gate-ready"]), 1
        )


if __name__ == "__main__":
    unittest.main()
