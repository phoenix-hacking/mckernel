#!/usr/bin/env python3
"""Adversarial tests for the active, unbuilt RS-006 miscdevice follow-up."""

from __future__ import print_function

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import rs006_miscdevice_module_owner_followup as followup


def read_bytes(relative):
    with open(os.path.join(REPO_ROOT, *relative.split("/")), "rb") as stream:
        return stream.read()


def identity(data):
    return {"sha256": followup._sha256(data), "size": len(data)}


def build_postimage(active_patch_bytes=None, predecessor_overrides=None):
    active_patch_bytes = active_patch_bytes if active_patch_bytes is not None else read_bytes(
        followup.ACTIVE_PATCH_PATH)
    predecessor_overrides = predecessor_overrides or {}
    with tempfile.TemporaryDirectory(prefix="rs006-owner-test-postimage-") as temporary:
        tree = os.path.join(temporary, "tree")
        shutil.copytree(
            os.path.join(REPO_ROOT, *followup.REPLAY_FIXTURE_PATH.split("/")),
            tree,
            symlinks=True,
        )
        for relative in (
                "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
                "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch"):
            data = predecessor_overrides.get(relative, read_bytes(relative))
            followup._apply_patch(tree, data, relative)
        followup._apply_patch(tree, active_patch_bytes, "active patch")
        with open(os.path.join(tree, "rust", "kernel", "miscdevice.rs"), "rb") as stream:
            return stream.read()


def build_dependency_postimages(rows):
    with tempfile.TemporaryDirectory(prefix="rs006-owner-test-dependencies-") as temporary:
        tree = os.path.join(temporary, "tree")
        shutil.copytree(
            os.path.join(REPO_ROOT, *followup.REPLAY_FIXTURE_PATH.split("/")),
            tree,
            symlinks=True,
        )
        for relative in (
                "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
                "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch"):
            followup._apply_patch(tree, read_bytes(relative), relative)
        result = {}
        for row in rows:
            with open(os.path.join(tree, *row["path"].split("/")), "rb") as stream:
                result[row["path"]] = stream.read()
        return result


class Rs006MiscdeviceModuleOwnerFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_bytes = read_bytes(followup.CONTRACT_PATH)
        cls.contract = json.loads(cls.contract_bytes.decode("utf-8"))
        cls.active_patch_bytes = read_bytes(followup.ACTIVE_PATCH_PATH)
        cls.fixture_bytes = read_bytes(followup.COMPILE_FIXTURE_PATH)
        cls.postimage = build_postimage()
        fixture = cls.contract["predecessor"]["local_replay_fixture"]
        cls.replay_preimages = {
            row["path"]: read_bytes(fixture["path"] + "/" + row["path"])
            for row in fixture["inventory"]
        }
        cls.dependency_postimages = build_dependency_postimages(
            cls.contract["predecessor"]["post_0020_dependency_inventory"])
        cls.consumer_bytes = {
            row["path"]: read_bytes(row["path"])
            for row in cls.contract["integrated_consumer_inventory"]
        }

    def test_repository_check_is_integrated_but_build_runtime_and_credit_false(self):
        result = followup.check(REPO_ROOT, compile_fixture=False)
        self.assertEqual("ACTIVE_ORDERED_UNBUILT_NONCREDITING", result["status"])
        self.assertEqual("active-ordered-unbuilt", result["integration_status"])
        self.assertEqual("required-missing", result["review_status"])
        self.assertEqual("required-missing", result["runtime_status"])
        for claim in (
                "configured_kernel_compiled", "module_runtime_executed",
                "compat_runtime_executed", "independent_review_complete",
                "durable_evidence_archived", "gate_pass", "credit_eligible",
                "tracker_credit"):
            self.assertFalse(result["claims"][claim])
        self.assertTrue(result["claims"]["active_patch_integrated"])
        self.assertTrue(result["claims"]["workflow_applies_active_patch"])
        self.assertEqual(["rust/kernel/miscdevice.rs"], result["replay"]["changed_paths"])
        self.assertEqual(0, result["replay"]["strict_fuzz"])

    def test_contract_digest_canonical_form_and_exact_blockers(self):
        self.assertEqual(
            followup.EXPECTED_CONTRACT_SHA256,
            followup._sha256(self.contract_bytes),
        )
        canonical = (json.dumps(self.contract, sort_keys=True, indent=2) + "\n").encode("utf-8")
        self.assertEqual(canonical, self.contract_bytes)
        self.assertEqual(followup._expected_claims(), self.contract["claims"])
        self.assertEqual(followup._expected_blockers(), self.contract["blockers"])

    def test_contract_mutation_and_duplicate_keys_fail_closed(self):
        mutated = self.contract_bytes.replace(
            b'"gate_pass": false', b'"gate_pass": true', 1)
        with self.assertRaisesRegex(followup.ContractError, "contract digest changed"):
            followup.check(REPO_ROOT, contract_override=mutated, compile_fixture=False)
        duplicate = self.contract_bytes.replace(
            b'"schema_version": 1,',
            b'"schema_version": 1,\n  "schema_version": 1,',
            1,
        )
        with self.assertRaises(followup.ContractError):
            followup.check(REPO_ROOT, contract_override=duplicate, compile_fixture=False)

    def test_claim_types_blockers_and_result_status_are_exact(self):
        for mutation in ("bool-alias", "blockers", "result"):
            contract = copy.deepcopy(self.contract)
            if mutation == "bool-alias":
                contract["claims"]["gate_pass"] = 0
            elif mutation == "blockers":
                contract["blockers"] = contract["blockers"][:-1]
            else:
                contract["result_authority"]["integration_status"] = "present"
            with self.subTest(mutation=mutation):
                with self.assertRaises(followup.ContractError):
                    followup._validate_contract_object(contract)

    def test_consumer_path_type_crashes_are_normalized(self):
        for invalid in (False, 7, None):
            contract = copy.deepcopy(self.contract)
            contract["consumer_update_plan"]["ordered_build"][0] = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaises(followup.ContractError):
                    followup._validate_contract_object(contract)

    def test_replay_dependencies_bind_non_null_thismodule_and_opaque(self):
        followup._validate_replay_dependency_semantics(
            self.replay_preimages, self.dependency_postimages)
        mutated = dict(self.replay_preimages)
        mutated["rust/kernel/lib.rs"] = mutated["rust/kernel/lib.rs"].replace(
            b"        self.0\n",
            b"        core::ptr::null_mut()\n",
            1,
        )
        with self.assertRaisesRegex(followup.ContractError, "as_ptr|null"):
            followup._validate_replay_dependency_semantics(
                mutated, self.dependency_postimages)
        mutated = dict(self.dependency_postimages)
        mutated["rust/kernel/types.rs"] = mutated["rust/kernel/types.rs"].replace(
            b"pub fn try_ffi_init<E>(", b"pub fn removed_try_ffi_init<E>(", 1)
        with self.assertRaisesRegex(followup.ContractError, "Opaque"):
            followup._validate_replay_dependency_semantics(
                self.replay_preimages, mutated)

    def test_ordered_consumer_removing_active_patch_is_rejected(self):
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        fake = self.consumer_bytes[workflow].replace(
            os.path.basename(followup.ACTIVE_PATCH_PATH).encode("ascii"),
            b"0020a-removed-module-owner-patch.patch",
        )
        contract = copy.deepcopy(self.contract)
        for row in contract["integrated_consumer_inventory"]:
            if row["path"] == workflow:
                row.update(identity(fake))
        consumers = dict(self.consumer_bytes)
        consumers[workflow] = fake
        with self.assertRaisesRegex(followup.ContractError, "omits the active patch"):
            followup._validate_integrated_consumers(contract, consumers)

    def test_source_license_workflow_watches_all_patches_for_push_and_pr(self):
        workflow = ".github/workflows/rocky-kernel-source-evidence.yml"
        data = self.consumer_bytes[workflow]
        self.assertIn(
            workflow, self.contract["consumer_update_plan"]["source_and_license"])
        self.assertEqual(2, data.count(b"host-kernel/rocky/patches/**"))
        followup._validate_source_license_workflow(data)

    def test_source_license_workflow_missing_or_duplicate_patch_watch_is_rejected(self):
        workflow = ".github/workflows/rocky-kernel-source-evidence.yml"
        original = self.consumer_bytes[workflow]
        watch = b"      - host-kernel/rocky/patches/**\n"
        mutations = {
            "missing-push": original.replace(watch, b"", 1),
            "duplicate-push": original.replace(watch, watch + watch, 1),
            "comment-shadow": original.replace(
                watch, b"      # - host-kernel/rocky/patches/**\n", 1),
            "outside-paths": original.replace(watch, b"", 1) + watch,
        }
        for label, mutated in mutations.items():
            contract = copy.deepcopy(self.contract)
            for row in contract["integrated_consumer_inventory"]:
                if row["path"] == workflow:
                    row.update(identity(mutated))
            consumers = dict(self.consumer_bytes)
            consumers[workflow] = mutated
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                        followup.ContractError, "source evidence workflow"):
                    followup._validate_integrated_consumers(contract, consumers)

    def test_active_patch_close_hook_forged_after_read_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rs006-owner-close-race-") as temporary:
            relative = followup.ACTIVE_PATCH_PATH
            target = os.path.join(temporary, *relative.split("/"))
            os.makedirs(os.path.dirname(target))
            with open(target, "wb") as stream:
                stream.write(self.active_patch_bytes)
            snapshot = followup._AggregateSnapshot(temporary)
            snapshot.open_file(relative, "active patch", len(self.active_patch_bytes))
            active_descriptor = snapshot.descriptor_for(relative)
            real_close = followup.os.close
            triggered = [False]

            def close_and_forge(descriptor):
                real_close(descriptor)
                if descriptor == active_descriptor and not triggered[0]:
                    triggered[0] = True
                    with open(target, "wb") as stream:
                        stream.write(b"X" * len(self.active_patch_bytes))

            with mock.patch.object(followup.os, "close", side_effect=close_and_forge):
                with self.assertRaises(followup.ContractError):
                    snapshot.close()
            self.assertTrue(triggered[0])

    def test_later_directory_close_cannot_forge_captured_active_patch(self):
        with tempfile.TemporaryDirectory(prefix="rs006-owner-later-close-race-") as temporary:
            relative = followup.ACTIVE_PATCH_PATH
            target = os.path.join(temporary, *relative.split("/"))
            os.makedirs(os.path.dirname(target))
            with open(target, "wb") as stream:
                stream.write(self.active_patch_bytes)
            snapshot = followup._AggregateSnapshot(temporary)
            snapshot.open_file(relative, "active patch", len(self.active_patch_bytes))
            repository_descriptor = snapshot._repository_record["descriptor"]
            real_close = followup.os.close
            triggered = [False]

            def close_and_forge(descriptor):
                real_close(descriptor)
                if descriptor == repository_descriptor and not triggered[0]:
                    triggered[0] = True
                    with open(target, "wb") as stream:
                        stream.write(b"Y" * len(self.active_patch_bytes))

            with mock.patch.object(followup.os, "close", side_effect=close_and_forge):
                with self.assertRaises(followup.ContractError):
                    snapshot.close()
            self.assertTrue(triggered[0])

    def test_active_patch_identity_and_path_vector_fail_closed(self):
        mutated = self.active_patch_bytes + b"\n"
        with self.assertRaisesRegex(followup.ContractError, "active patch identity changed"):
            followup.check(
                REPO_ROOT,
                file_overrides={followup.ACTIVE_PATCH_PATH: mutated},
                compile_fixture=False,
            )
        expanded = self.active_patch_bytes.replace(
            b"diff --git a/rust/kernel/miscdevice.rs b/rust/kernel/miscdevice.rs",
            b"diff --git a/rust/kernel/other.rs b/rust/kernel/other.rs",
            1,
        )
        expected = dict(self.contract["active_patch"])
        expected.update(identity(expanded))
        with self.assertRaisesRegex(followup.ContractError, "path vector"):
            followup._validate_active_patch(expanded, expected)

    def test_active_patch_cannot_cross_into_ihk_policy(self):
        mutated = self.active_patch_bytes.replace(
            b"This repository-local compatibility patch",
            b"This IHK repository-local compatibility patch", 1)
        expected = dict(self.contract["active_patch"])
        expected.update(identity(mutated))
        with self.assertRaisesRegex(followup.ContractError, "generic-only"):
            followup._validate_active_patch(mutated, expected)

    def test_postimage_binds_static_thismodule_owner_exactly(self):
        for old, new in (
                (b"const MODULE: &'static ThisModule;", b"const MODULE: &ThisModule;        "),
                (b"owner: T::MODULE.as_ptr(),", b"owner: core::ptr::null_mut(),"),
                (b"const VTABLE: bindings::file_operations", b"static VTABLE: bindings::file_operations")):
            mutated = self.postimage.replace(old, new, 1)
            with self.subTest(old=old):
                with self.assertRaises(followup.ContractError):
                    followup._validate_postimage(mutated, identity(mutated))

    def test_postimage_forbids_implicit_compat_fallback(self):
        explicit = b"compat_ioctl: maybe_fn(T::HAS_COMPAT_IOCTL, fops_compat_ioctl::<T>),"
        mutations = (
            self.postimage.replace(explicit, b"compat_ioctl: Some(bindings::compat_ptr_ioctl),", 1),
            self.postimage.replace(explicit, b"compat_ioctl: None,", 1),
        )
        for mutated in mutations:
            with self.subTest(digest=followup._sha256(mutated)):
                with self.assertRaises(followup.ContractError):
                    followup._validate_postimage(mutated, identity(mutated))

    def test_postimage_preserves_pin_and_deregister_order(self):
        mutations = (
            self.postimage.replace(b"#[pin_data(PinnedDrop)]", b"#[repr(C)]             ", 1),
            self.postimage.replace(
                b"inner: Opaque<bindings::miscdevice>,",
                b"inner: bindings::miscdevice,        ",
                1,
            ),
            self.postimage.replace(b"bindings::misc_deregister", b"bindings::misc_register  ", 1),
        )
        for mutated in mutations:
            with self.subTest(digest=followup._sha256(mutated)):
                with self.assertRaises(followup.ContractError):
                    followup._validate_postimage(mutated, identity(mutated))

    def test_postimage_forbids_per_registration_file_operations(self):
        marker = b"    _t: PhantomData<T>,\n"
        mutated = self.postimage.replace(
            marker,
            marker + b"    fops: bindings::file_operations,\n",
            1,
        )
        with self.assertRaisesRegex(followup.ContractError, "per-registration"):
            followup._validate_postimage(mutated, identity(mutated))

    def test_compile_fixture_binds_intended_module_and_explicit_compat(self):
        binding = b"const MODULE: &'static ThisModule = &THIS_MODULE;"
        wrong_binding = b"const MODULE: &'static ThisModule = &OTHER_MODULE;"
        wrong_explicit_module = self.fixture_bytes.replace(
            binding,
            wrong_binding,
            1,
        )
        prefix, separator, remainder = self.fixture_bytes.partition(binding)
        self.assertTrue(separator)
        wrong_no_compat_module = prefix + separator + remainder.replace(
            binding,
            wrong_binding,
            1,
        )
        for wrong_module in (wrong_explicit_module, wrong_no_compat_module):
            with self.subTest(digest=followup._sha256(wrong_module)):
                with self.assertRaises(followup.ContractError):
                    followup._validate_compile_fixture(wrong_module, identity(wrong_module))
        wrong_flag = self.fixture_bytes.replace(
            b"const HAS_COMPAT_IOCTL: bool = true;",
            b"const HAS_COMPAT_IOCTL: bool = false;",
            1,
        )
        with self.assertRaises(followup.ContractError):
            followup._validate_compile_fixture(wrong_flag, identity(wrong_flag))
        fallback = self.fixture_bytes + b"\n// compat_ptr_ioctl\n"
        with self.assertRaisesRegex(followup.ContractError, "implicit compat fallback"):
            followup._validate_compile_fixture(fallback, identity(fallback))

    def test_compile_fixture_binds_pinned_drop_and_static_vtable_shape(self):
        mutations = (
            self.fixture_bytes.replace(
                b"inner: Pin<Box<RawMiscDevice>>",
                b"inner: Box<RawMiscDevice>     ",
                1,
            ),
            self.fixture_bytes.replace(
                b"    _t: PhantomData<T>,\n}\n\nimpl<T: MiscDevice> MiscDeviceRegistration<T>",
                b"    _t: PhantomData<T>,\n    local_fops: FileOperations,\n}\n\nimpl<T: MiscDevice> MiscDeviceRegistration<T>",
                1,
            ),
            self.fixture_bytes.replace(
                b"raw.registered = false;",
                b"raw.registered = true; ",
                1,
            ),
        )
        for mutated in mutations:
            with self.subTest(digest=followup._sha256(mutated)):
                with self.assertRaises(followup.ContractError):
                    followup._validate_compile_fixture(mutated, identity(mutated))

    def test_compile_shape_fixture_compiles_and_runs_when_rustc_exists(self):
        if shutil.which("rustc") is None:
            self.skipTest("rustc unavailable; checker records an honest skip")
        result = followup._compile_fixture(self.fixture_bytes, True)
        self.assertEqual("PASS", result["status"])

    def test_predecessor_patch_mutations_are_rejected(self):
        relative = "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch"
        mutated = read_bytes(relative) + b"\n"
        with self.assertRaisesRegex(followup.ContractError, "predecessor patch 0 identity changed"):
            followup.check(
                REPO_ROOT,
                file_overrides={relative: mutated},
                compile_fixture=False,
            )

    def test_override_surface_is_bounded(self):
        with self.assertRaisesRegex(followup.ContractError, "override keys"):
            followup.check(
                REPO_ROOT,
                file_overrides={"host-kernel/rocky/source-lock.json": b"{}\n"},
                compile_fixture=False,
            )
        with self.assertRaisesRegex(followup.ContractError, "compile controls"):
            followup.check(REPO_ROOT, compile_fixture=1)

    def test_integrated_consumers_bind_active_patch_and_preserve_history(self):
        for group, rows in self.contract["consumer_update_plan"].items():
            if group == "stage_manifest":
                rows = [rows["path"]]
            for relative in rows:
                self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, *relative.split("/"))))
        active_name = os.path.basename(followup.ACTIVE_PATCH_PATH).encode("ascii")
        for relative in (
                "host-kernel/rocky/source-lock.json",
                ".github/workflows/native-rust-host-modules-exact-build.yml",
                ".github/workflows/rs001-linux-api-exact-probe.yml"):
            self.assertIn(active_name, read_bytes(relative))
        for relative in (
                "host-kernel/rocky/patches/series.json",
                "host-kernel/kbuild/stage-manifest.json",
                "host-kernel/rocky/evidence/config-resolution-review-378d-v1.json",
                "host-kernel/rocky/evidence/config-resolution-review-bebf-v2.json",
                "host-kernel/rocky/evidence/rk007-native-build-review-bc60-v1.json",
                "host-kernel/rocky/evidence/rk007-native-build-review-ef58-v2.json"):
            self.assertNotIn(active_name, read_bytes(relative))

    def test_exact_build_authority_is_current_without_reclassifying_history(self):
        workflow_path = ".github/workflows/native-rust-host-modules-exact-build.yml"
        workflow = read_bytes(workflow_path)
        runtime_contract = json.loads(read_bytes(
            "host-kernel/contracts/native-rust-runtime-evidence-v1.json").decode("utf-8"))
        self.assertIn(os.path.basename(
            followup.ACTIVE_PATCH_PATH).encode("ascii"), workflow)
        workflow_identity = runtime_contract["repository_workflow_identities"][
            "build_workflow"]
        self.assertEqual(len(workflow), workflow_identity["size"])
        self.assertEqual(followup._sha256(workflow), workflow_identity["sha256"])
        self.assertEqual("required-missing", runtime_contract[
            "artifact_contract"]["capture_status"])
        self.assertFalse(runtime_contract["gate"]["capture_can_claim_pass"])
        self.assertFalse(runtime_contract["gate"]["credit_eligible"])
        for relative in (
                "host-kernel/rocky/evidence/rk007-native-build-review-bc60-v1.json",
                "host-kernel/rocky/evidence/rk007-native-build-review-ef58-v2.json"):
            review = json.loads(read_bytes(relative).decode("utf-8"))
            self.assertFalse(review["claims"]["credit_eligible"])
            self.assertFalse(review["claims"]["module_loadability_proven"])
            self.assertFalse(review["claims"]["runtime_behavior_proven"])
            self.assertFalse(review["claims"]["tracker_credit"])
            self.assertTrue(all(
                value is False
                for value in review["claims"]["gate_claims"].values()))

    def test_checker_and_tests_parse_as_python_3_6(self):
        for relative in (
                "scripts/rs006_miscdevice_module_owner_followup.py",
                "scripts/tests/test_rs006_miscdevice_module_owner_followup.py"):
            source = read_bytes(relative).decode("utf-8")
            try:
                ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=relative, feature_version=6)

    def test_cli_reports_integrated_but_unbuilt_noncrediting_claims(self):
        process = subprocess.Popen(
            [
                sys.executable,
                "scripts/rs006_miscdevice_module_owner_followup.py",
                "--repo",
                REPO_ROOT,
                "--skip-fixture-compile",
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        self.assertEqual(0, process.returncode, stderr.decode("utf-8", "replace"))
        result = json.loads(stdout.decode("utf-8"))
        self.assertEqual("ACTIVE_ORDERED_UNBUILT_NONCREDITING", result["status"])
        self.assertEqual("active-ordered-unbuilt", result["integration_status"])
        self.assertTrue(result["claims"]["active_patch_integrated"])
        self.assertTrue(result["claims"]["workflow_applies_active_patch"])
        for claim in (
                "configured_kernel_compiled", "module_runtime_executed",
                "compat_runtime_executed", "independent_review_complete",
                "durable_evidence_archived", "gate_pass", "credit_eligible",
                "tracker_credit"):
            self.assertFalse(result["claims"][claim])


if __name__ == "__main__":
    unittest.main()
