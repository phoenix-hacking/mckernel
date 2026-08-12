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
        for name in ("Kbuild.in", "Kconfig"):
            shutil.copyfile(
                os.path.join(REPO_ROOT, "host-kernel", "kbuild", name),
                os.path.join(self.repo, "host-kernel", "kbuild", name),
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

    def test_repository_checkpoint_is_integrity_valid_but_never_ready(self):
        plan = staging.validate_manifest(
            REPO_ROOT, os.path.join(REPO_ROOT, staging.DEFAULT_MANIFEST)
        )
        self.assertFalse(plan["credit_eligible"])
        self.assertEqual(
            staging.MODULE_BLOCKERS + staging.READINESS_BLOCKERS,
            plan["blockers"],
        )
        self.assertEqual(staging.EXPECTED_TARGET, plan["manifest"]["target"])
        self.assertEqual(
            staging.EXPECTED_PARENT_INTEGRATION_REF,
            plan["manifest"]["parent_integration"],
        )
        self.assertEqual(
            "drivers/misc/Makefile",
            plan["manifest"]["destination"]["parent_kbuild_integration"],
        )

    def test_removing_blockers_and_adding_trivial_sources_cannot_claim_ready(self):
        self.manifest["readiness"] = {
            "blockers": [],
            "checkpoint": "ready",
            "credit_eligible": True,
        }
        os.makedirs(os.path.join(self.repo, "native"))
        for module in self.manifest["modules"]:
            module["blockers"] = []
            relative = os.path.join("native", module["source"]["destination"])
            absolute = os.path.join(self.repo, relative)
            with open(absolute, "w") as stream:
                stream.write("// not evidence\n")
            module["source"]["repository_path"] = relative
            module["source"]["sha256"] = digest(absolute)
        self.write_manifest()
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_integrity_only_schema_cannot_stage_even_with_mutated_plan(self):
        plan = self.plan()
        plan["blockers"] = []
        plan["credit_eligible"] = True
        kernel = os.path.join(self.temporary, "kernel")
        os.makedirs(os.path.join(kernel, "drivers", "misc"))
        with self.assertRaises(staging.ValidationError):
            staging.stage(plan, kernel)
        self.assertFalse(os.path.exists(os.path.join(kernel, "drivers", "misc", "mckernel")))

    def test_stage_lock_binds_selected_target_identity(self):
        lock = staging._stage_lock(self.plan())
        self.assertEqual(staging.EXPECTED_TARGET, lock["target"])
        self.assertIsNone(lock["target"]["resolved_config_sha256"])
        self.assertEqual(
            staging.EXPECTED_PARENT_INTEGRATION_REF["sha256"],
            lock["parent_integration"]["bundle_sha256"],
        )
        self.assertEqual(
            staging.EXPECTED_PARENT_PATCH["sha256"],
            lock["parent_integration"]["patch_sha256"],
        )

    def test_source_injection_is_rejected_even_when_hashed(self):
        os.makedirs(os.path.join(self.repo, "native"))
        path = os.path.join(self.repo, "native", "ihk.rs")
        with open(path, "w") as stream:
            stream.write("// not evidence\n")
        self.manifest["modules"][0]["source"]["repository_path"] = "native/ihk.rs"
        self.manifest["modules"][0]["source"]["sha256"] = digest(path)
        self.write_manifest()
        with self.assertRaises(staging.ValidationError):
            self.plan()

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

    def test_kconfig_extra_dependency_is_rejected_after_rehash(self):
        self.mutate_kconfig(
            '\ttristate "McKernel IHK core host module (Rust)"',
            '\ttristate "McKernel IHK core host module (Rust)"\n\tdepends on MODULES',
        )
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_kconfig_semantic_validator_independently_rejects_mutations(self):
        path = os.path.join(REPO_ROOT, "host-kernel", "kbuild", "Kconfig")
        with open(path, "r") as stream:
            original = stream.read()
        mutations = {
            "bool": original.replace(
                '\ttristate "McKernel IHK core host module (Rust)"',
                '\tbool "McKernel IHK core host module (Rust)"',
                1,
            ),
            "default": original.replace(
                '\ttristate "McKernel IHK core host module (Rust)"',
                '\ttristate "McKernel IHK core host module (Rust)"\n\tdefault y',
                1,
            ),
            "extra dependency": original.replace(
                '\ttristate "McKernel IHK core host module (Rust)"',
                '\ttristate "McKernel IHK core host module (Rust)"\n\tdepends on MODULES',
                1,
            ),
        }
        for label, text in mutations.items():
            with self.subTest(label=label):
                with self.assertRaises(staging.ValidationError):
                    staging._validate_kconfig(text)

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

    def test_module_blocker_cannot_be_removed(self):
        self.manifest["modules"][0]["blockers"] = []
        self.write_manifest()
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_parent_patch_drift_is_rejected(self):
        path = os.path.join(self.repo, staging.EXPECTED_PARENT_PATCH["repository_path"])
        with open(path, "a") as stream:
            stream.write("# drift\n")
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_parent_bundle_source_lock_drift_is_rejected(self):
        path = os.path.join(
            self.repo, staging.EXPECTED_PARENT_SOURCE["source_lock_repository_path"]
        )
        with open(path, "a") as stream:
            stream.write("\n")
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_parent_bundle_cannot_self_attest_a_postimage(self):
        path = os.path.join(self.repo, staging.EXPECTED_PARENT_INTEGRATION_REF["repository_path"])
        with open(path, "r") as stream:
            bundle = json.load(stream)
        bundle["parent_files"][0]["postimage_sha256"] = "0" * 64
        with open(path, "w") as stream:
            json.dump(bundle, stream, indent=2, sort_keys=True)
            stream.write("\n")
        self.manifest["parent_integration"]["sha256"] = digest(path)
        self.write_manifest()
        with self.assertRaises(staging.ValidationError):
            self.plan()

    def test_atomic_no_replace_rename_preserves_concurrent_destination(self):
        parent = os.path.join(self.temporary, "rename-parent")
        os.makedirs(parent)
        source = os.path.join(parent, "source")
        target = os.path.join(parent, "target")
        os.makedirs(source)
        staging._rename_directory_noreplace(parent, source, target)
        self.assertFalse(os.path.exists(source))
        self.assertTrue(os.path.isdir(target))

        second_source = os.path.join(parent, "second-source")
        occupied = os.path.join(parent, "occupied")
        os.makedirs(second_source)
        os.makedirs(occupied)
        with self.assertRaises(staging.ValidationError):
            staging._rename_directory_noreplace(parent, second_source, occupied)
        self.assertTrue(os.path.isdir(second_source))
        self.assertTrue(os.path.isdir(occupied))

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

    def test_symlinked_manifest_is_rejected(self):
        link = os.path.join(self.repo, "manifest-link.json")
        os.symlink(self.manifest_path, link)
        with self.assertRaises(staging.ValidationError):
            staging.validate_manifest(self.repo, link)


if __name__ == "__main__":
    unittest.main()
