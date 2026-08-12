import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import rocky_rust_staging as staging


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        value.update(stream.read())
    return value.hexdigest()


class RockyRustStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.mkdtemp(prefix="rocky-rust-stage-test-")
        self.repo = os.path.join(self.temporary, "repo")
        os.makedirs(os.path.join(self.repo, "host-kernel", "kbuild", "patches"))
        os.makedirs(os.path.join(self.repo, "host-kernel", "rocky"))
        os.makedirs(os.path.join(self.repo, "host-kernel", "native-rust"))
        for name in ("Kbuild.in", "Kconfig"):
            shutil.copyfile(
                os.path.join(REPO_ROOT, "host-kernel", "kbuild", name),
                os.path.join(self.repo, "host-kernel", "kbuild", name),
            )
        for module in staging.EXPECTED_MODULES:
            shutil.copyfile(
                os.path.join(REPO_ROOT, module["source_repository_path"]),
                os.path.join(self.repo, module["source_repository_path"]),
            )
        shutil.copyfile(
            os.path.join(REPO_ROOT, staging.EXPECTED_PARENT_INTEGRATION_REF["repository_path"]),
            os.path.join(self.repo, staging.EXPECTED_PARENT_INTEGRATION_REF["repository_path"]),
        )
        shutil.copyfile(
            os.path.join(REPO_ROOT, staging.EXPECTED_PARENT_PATCH["repository_path"]),
            os.path.join(self.repo, staging.EXPECTED_PARENT_PATCH["repository_path"]),
        )
        shutil.copyfile(
            os.path.join(REPO_ROOT, staging.EXPECTED_PARENT_SOURCE["source_lock_repository_path"]),
            os.path.join(self.repo, staging.EXPECTED_PARENT_SOURCE["source_lock_repository_path"]),
        )
        with open(os.path.join(REPO_ROOT, staging.DEFAULT_MANIFEST), "r") as stream:
            self.manifest = json.load(stream)
        self.manifest_path = os.path.join(self.repo, staging.DEFAULT_MANIFEST)
        self.write_manifest()

    def tearDown(self):
        shutil.rmtree(self.temporary)

    def write_manifest(self):
        with open(self.manifest_path, "w") as stream:
            json.dump(self.manifest, stream, indent=2, sort_keys=True)
            stream.write("\n")

    def plan(self):
        return staging.validate_manifest(self.repo, self.manifest_path)

    def rehash_input(self, index):
        item = self.manifest["inputs"][index]
        item["sha256"] = digest(os.path.join(self.repo, item["repository_path"]))
        self.write_manifest()

    def mutate_kconfig(self, old, new):
        path = os.path.join(self.repo, "host-kernel", "kbuild", "Kconfig")
        with open(path, "r") as stream:
            text = stream.read()
        self.assertIn(old, text)
        with open(path, "w") as stream:
            stream.write(text.replace(old, new, 1))
        self.rehash_input(1)

    def test_repository_checkpoint_has_bound_crate_roots_but_is_not_gate_ready(self):
        plan = staging.validate_manifest(
            REPO_ROOT, os.path.join(REPO_ROOT, staging.DEFAULT_MANIFEST)
        )
        self.assertFalse(plan["credit_eligible"])
        self.assertEqual(staging.READINESS_BLOCKERS, plan["blockers"])
        self.assertEqual("crate_roots_bound", plan["manifest"]["readiness"]["checkpoint"])
        self.assertEqual(staging.EXPECTED_TARGET, plan["manifest"]["target"])
        staged = {item["destination"] for item in plan["files"]}
        self.assertEqual(
            {"Kbuild", "Kconfig", "ihk.rs", "ihk_smp_x86_64.rs", "mcctrl.rs"}, staged
        )

    def test_crate_root_digest_drift_is_rejected(self):
        module = staging.EXPECTED_MODULES[0]
        path = os.path.join(self.repo, module["source_repository_path"])
        with open(path, "a") as stream:
            stream.write("// drift\n")
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_crate_root_path_injection_is_rejected_even_when_hashed(self):
        os.makedirs(os.path.join(self.repo, "native"))
        path = os.path.join(self.repo, "native", "ihk.rs")
        with open(path, "w") as stream:
            stream.write("use kernel::prelude::*;\nmodule! { type: X, name: \"x\", author: \"x\", description: \"x\", license: \"GPL\", }\nstruct X; impl kernel::Module for X { fn init(_: &'static ThisModule) -> Result<Self> { Ok(Self) } }\n")
        self.manifest["modules"][0]["source"]["repository_path"] = "native/ihk.rs"
        self.manifest["modules"][0]["source"]["sha256"] = digest(path)
        self.write_manifest()
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_unreviewed_extern_c_is_rejected(self):
        module = staging.EXPECTED_MODULES[0]
        path = os.path.join(self.repo, module["source_repository_path"])
        with open(path, "a") as stream:
            stream.write('extern "C" { fn legacy(); }\n')
        self.manifest["modules"][0]["source"]["sha256"] = digest(path)
        self.write_manifest()
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_readiness_cannot_be_self_attested(self):
        self.manifest["readiness"] = {
            "blockers": [],
            "checkpoint": "ready",
            "credit_eligible": True,
        }
        self.write_manifest()
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_schema_cannot_stage_without_build_evidence(self):
        plan = self.plan()
        plan["blockers"] = []
        plan["credit_eligible"] = True
        kernel = os.path.join(self.temporary, "kernel")
        os.makedirs(os.path.join(kernel, "drivers", "misc"))
        with self.assertRaises(staging.ValidationError):
            staging.stage(plan, kernel)
        self.assertFalse(os.path.exists(os.path.join(kernel, "drivers", "misc", "mckernel")))

    def test_stage_lock_binds_crate_roots_and_target_identity(self):
        plan = self.plan()
        lock = staging._stage_lock(plan)
        self.assertEqual(staging.EXPECTED_TARGET, lock["target"])
        paths = {item["path"] for item in lock["files"]}
        self.assertEqual(
            {"Kbuild", "Kconfig", "ihk.rs", "ihk_smp_x86_64.rs", "mcctrl.rs"}, paths
        )

    def test_kbuild_command_injection_is_rejected_after_rehash(self):
        path = os.path.join(self.repo, "host-kernel", "kbuild", "Kbuild.in")
        with open(path, "a") as stream:
            stream.write("obj-y += $(shell rustc --version)\n")
        self.rehash_input(0)
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_kconfig_bool_is_rejected_after_rehash(self):
        self.mutate_kconfig('\ttristate "McKernel IHK core host module (Rust)"', '\tbool "McKernel IHK core host module (Rust)"')
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_kconfig_default_is_rejected_after_rehash(self):
        self.mutate_kconfig(
            '\ttristate "McKernel IHK core host module (Rust)"',
            '\ttristate "McKernel IHK core host module (Rust)"\n\tdefault y',
        )
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_consumer_without_provider_dependency_is_rejected_after_rehash(self):
        self.mutate_kconfig("\tdepends on MCKERNEL_IHK_RUST\n", "")
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_target_identity_or_resolved_evidence_cannot_be_self_attested(self):
        for field, value in (
            ("release", "10.3"),
            ("resolved_config_sha256", "0" * 64),
            ("resolved_kernel_nvr", "invented"),
        ):
            broken = copy.deepcopy(self.manifest)
            broken["target"][field] = value
            self.manifest = broken
            self.write_manifest()
            with self.assertRaises(staging.ValidationError):
                self.plan()
            with open(os.path.join(REPO_ROOT, staging.DEFAULT_MANIFEST), "r") as stream:
                self.manifest = json.load(stream)

    def test_parent_patch_drift_is_rejected(self):
        path = os.path.join(self.repo, staging.EXPECTED_PARENT_PATCH["repository_path"])
        with open(path, "a") as stream:
            stream.write("# drift\n")
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_symlinked_locked_input_is_rejected(self):
        path = os.path.join(self.repo, "host-kernel", "kbuild", "Kconfig")
        outside = os.path.join(self.temporary, "outside-Kconfig")
        shutil.copyfile(path, outside)
        os.unlink(path)
        os.symlink(outside, path)
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_duplicate_json_keys_are_rejected(self):
        path = os.path.join(self.repo, "duplicate.json")
        with open(path, "w") as stream:
            stream.write('{"schema_version": 1, "schema_version": 1}\n')
        with self.assertRaises(staging.ValidationError):
            staging.load_json(path)

    def test_manifest_path_escape_is_rejected(self):
        outside = os.path.join(self.temporary, "outside.json")
        with open(outside, "w") as stream:
            json.dump(copy.deepcopy(self.manifest), stream)
        with self.assertRaises(staging.ValidationError):
            staging.validate_manifest(self.repo, outside)


if __name__ == "__main__":
    unittest.main()
