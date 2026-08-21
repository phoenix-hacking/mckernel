#!/usr/bin/env python3
"""Adversarial tests for the candidate-only RS-006 miscdevice follow-up."""

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


def build_postimage(candidate_bytes=None, predecessor_overrides=None):
    candidate_bytes = candidate_bytes if candidate_bytes is not None else read_bytes(
        followup.CANDIDATE_PATH)
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
        followup._apply_patch(tree, candidate_bytes, "candidate")
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
        cls.candidate_bytes = read_bytes(followup.CANDIDATE_PATH)
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
            for row in cls.contract["deferred_consumer_inventory"]
        }

    def test_repository_check_is_candidate_only_and_all_claims_false(self):
        result = followup.check(REPO_ROOT, compile_fixture=False)
        self.assertEqual("CANDIDATE_VALIDATED_NONAUTHORITATIVE", result["status"])
        self.assertEqual("required-missing", result["integration_status"])
        self.assertEqual("required-missing", result["review_status"])
        self.assertEqual("required-missing", result["runtime_status"])
        self.assertTrue(result["claims"])
        self.assertTrue(all(value is False for value in result["claims"].values()))
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

    def test_deferred_consumer_fake_candidate_apply_is_rejected(self):
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        fake = self.consumer_bytes[workflow] + (
            b"\n# forged active candidate application\n"
            b"patch -p1 -i host-kernel/rocky/candidates/"
            b"0020-followup-rust-miscdevice-module-owner-v1.patch\n"
        )
        contract = copy.deepcopy(self.contract)
        for row in contract["deferred_consumer_inventory"]:
            if row["path"] == workflow:
                row.update(identity(fake))
        consumers = dict(self.consumer_bytes)
        consumers[workflow] = fake
        with self.assertRaisesRegex(followup.ContractError, "references or applies"):
            followup._validate_deferred_consumers(contract, consumers)

    def test_candidate_close_hook_forged_after_read_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="rs006-owner-close-race-") as temporary:
            relative = followup.CANDIDATE_PATH
            target = os.path.join(temporary, *relative.split("/"))
            os.makedirs(os.path.dirname(target))
            with open(target, "wb") as stream:
                stream.write(self.candidate_bytes)
            snapshot = followup._AggregateSnapshot(temporary)
            snapshot.open_file(relative, "candidate patch", len(self.candidate_bytes))
            candidate_descriptor = snapshot.descriptor_for(relative)
            real_close = followup.os.close
            triggered = [False]

            def close_and_forge(descriptor):
                real_close(descriptor)
                if descriptor == candidate_descriptor and not triggered[0]:
                    triggered[0] = True
                    with open(target, "wb") as stream:
                        stream.write(b"X" * len(self.candidate_bytes))

            with mock.patch.object(followup.os, "close", side_effect=close_and_forge):
                with self.assertRaises(followup.ContractError):
                    snapshot.close()
            self.assertTrue(triggered[0])

    def test_later_directory_close_cannot_forge_captured_candidate(self):
        with tempfile.TemporaryDirectory(prefix="rs006-owner-later-close-race-") as temporary:
            relative = followup.CANDIDATE_PATH
            target = os.path.join(temporary, *relative.split("/"))
            os.makedirs(os.path.dirname(target))
            with open(target, "wb") as stream:
                stream.write(self.candidate_bytes)
            snapshot = followup._AggregateSnapshot(temporary)
            snapshot.open_file(relative, "candidate patch", len(self.candidate_bytes))
            repository_descriptor = snapshot._repository_record["descriptor"]
            real_close = followup.os.close
            triggered = [False]

            def close_and_forge(descriptor):
                real_close(descriptor)
                if descriptor == repository_descriptor and not triggered[0]:
                    triggered[0] = True
                    with open(target, "wb") as stream:
                        stream.write(b"Y" * len(self.candidate_bytes))

            with mock.patch.object(followup.os, "close", side_effect=close_and_forge):
                with self.assertRaises(followup.ContractError):
                    snapshot.close()
            self.assertTrue(triggered[0])

    def test_candidate_patch_identity_and_path_vector_fail_closed(self):
        mutated = self.candidate_bytes + b"\n"
        with self.assertRaisesRegex(followup.ContractError, "candidate patch identity changed"):
            followup.check(
                REPO_ROOT,
                file_overrides={followup.CANDIDATE_PATH: mutated},
                compile_fixture=False,
            )
        expanded = self.candidate_bytes.replace(
            b"diff --git a/rust/kernel/miscdevice.rs b/rust/kernel/miscdevice.rs",
            b"diff --git a/rust/kernel/other.rs b/rust/kernel/other.rs",
            1,
        )
        expected = dict(self.contract["candidate"])
        expected.update(identity(expanded))
        with self.assertRaisesRegex(followup.ContractError, "path vector"):
            followup._validate_candidate_patch(expanded, expected)

    def test_candidate_patch_cannot_cross_into_ihk_policy(self):
        mutated = self.candidate_bytes.replace(
            b"This local follow-up", b"This IHK follow-up", 1)
        expected = dict(self.contract["candidate"])
        expected.update(identity(mutated))
        with self.assertRaisesRegex(followup.ContractError, "generic-only"):
            followup._validate_candidate_patch(mutated, expected)

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

    def test_deferred_consumers_are_present_but_candidate_is_not_integrated(self):
        for group, rows in self.contract["consumer_update_plan"].items():
            if group == "stage_manifest":
                rows = [rows["path"]]
            for relative in rows:
                self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, *relative.split("/"))))
        candidate_name = os.path.basename(followup.CANDIDATE_PATH).encode("ascii")
        for relative in (
                "host-kernel/rocky/source-lock.json",
                "host-kernel/rocky/patches/series.json",
                "host-kernel/kbuild/stage-manifest.json"):
            self.assertNotIn(candidate_name, read_bytes(relative))

    def test_checker_and_tests_parse_as_python_3_6(self):
        for relative in (
                "scripts/rs006_miscdevice_module_owner_followup.py",
                "scripts/tests/test_rs006_miscdevice_module_owner_followup.py"):
            source = read_bytes(relative).decode("utf-8")
            try:
                ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=relative, feature_version=6)

    def test_cli_reports_non_authoritative_false_claims(self):
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
        self.assertEqual("CANDIDATE_VALIDATED_NONAUTHORITATIVE", result["status"])
        self.assertTrue(all(value is False for value in result["claims"].values()))
        self.assertEqual("required-missing", result["integration_status"])


if __name__ == "__main__":
    unittest.main()
