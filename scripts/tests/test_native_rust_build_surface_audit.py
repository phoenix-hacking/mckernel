from __future__ import print_function

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

from scripts import native_rust_build_surface_audit as audit


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        value.update(stream.read())
    return value.hexdigest()


class NativeRustBuildSurfaceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.mkdtemp(prefix="native-rust-build-surface-")
        self.repo = os.path.join(self.temporary, "repo")
        os.makedirs(os.path.join(self.repo, "host-kernel", "kbuild"))
        os.makedirs(os.path.join(self.repo, "host-kernel", "native-rust"))
        for name in ("Kconfig", "Kbuild.in", "stage-manifest.json"):
            shutil.copyfile(
                os.path.join(REPO_ROOT, "host-kernel", "kbuild", name),
                os.path.join(self.repo, "host-kernel", "kbuild", name),
            )
        with open(os.path.join(REPO_ROOT, "host-kernel", "kbuild", "stage-manifest.json")) as stream:
            manifest = json.load(stream)
        relatives = [item["repository_path"] for item in manifest["inputs"]]
        relatives.extend(item["source"]["repository_path"] for item in manifest["modules"])
        for relative in relatives:
            destination = os.path.join(self.repo, *relative.split("/"))
            parent = os.path.dirname(destination)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            if not os.path.isfile(destination):
                shutil.copyfile(os.path.join(REPO_ROOT, *relative.split("/")), destination)
        with open(
            os.path.join(self.repo, "host-kernel", "native-rust", "README.md"), "w"
        ) as stream:
            stream.write("crate roots only\n")
        self.manifest_path = os.path.join(
            self.repo, "host-kernel", "kbuild", "stage-manifest.json"
        )

    def tearDown(self):
        shutil.rmtree(self.temporary)

    def load_manifest(self):
        with open(self.manifest_path, "r") as stream:
            return json.load(stream)

    def write_manifest(self, manifest):
        with open(self.manifest_path, "w") as stream:
            json.dump(manifest, stream, indent=2, sort_keys=True)
            stream.write("\n")

    def rehash(self, destination):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == destination:
                item["sha256"] = digest(
                    os.path.join(self.repo, *item["repository_path"].split("/"))
                )
                break
        else:
            self.fail("missing manifest destination " + destination)
        self.write_manifest(manifest)

    def mutate_authority(self, destination, old, new):
        relative = audit.AUTHORITATIVE_INPUTS[destination]
        path = os.path.join(self.repo, *relative.split("/"))
        with open(path, "r") as stream:
            text = stream.read()
        self.assertIn(old, text)
        with open(path, "w") as stream:
            stream.write(text.replace(old, new, 1))
        self.rehash(destination)

    def test_repository_has_one_authoritative_surface(self):
        result = audit.audit(REPO_ROOT)
        self.assertEqual(3, result["module_count"])
        self.assertEqual(
            (
                "host-kernel/kbuild/Kbuild.in",
                "host-kernel/kbuild/Kconfig",
            ),
            result["authoritative_inputs"],
        )

    def test_current_recursive_closure_is_exact_and_generated_bytes_are_excluded(self):
        closure = audit.discover_native_closure(self.repo)
        manifest = self.load_manifest()
        native_inputs = {item["destination"] for item in manifest["inputs"]
                         if item["destination"] not in audit.AUTHORITATIVE_INPUTS}
        self.assertEqual(closure - set(audit.CRATE_ROOTS), native_inputs)
        self.assertEqual(57, len(closure))
        self.assertIn("smp_trampoline.S", closure)
        self.assertIn("smp_startup_entry.S", closure)
        self.assertNotIn("ihk-compat-build-id.bin", closure)
        audit.audit(self.repo)

    def test_dependency_macro_alias_or_forwarding_fails_closed(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        cases = (
            'use core::include_str as read; const DATA: &str = read!("unbound.txt");',
            'macro_rules! forward { ($m:ident, $p:expr) => { $m!($p) }; }\n'
            'const DATA: &str = forward!(include_str, "unbound.txt");',
        )
        for addition in cases:
            with self.subTest(addition=addition):
                shutil.copyfile(os.path.join(REPO_ROOT, relative), path)
                with open(path, "a") as stream:
                    stream.write("\n" + addition + "\n")
                self.rehash("smp_service.rs")
                with self.assertRaisesRegex(audit.AuditError, "dependency macro identifier use"):
                    audit.audit(self.repo)

    def test_unrelated_macro_remains_permitted(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        with open(path, "a") as stream:
            stream.write("\nmacro_rules! answer { () => { 42 }; }\nconst ANSWER: u8 = answer!();\n")
        self.rehash("smp_service.rs")
        audit.audit(self.repo)

    def test_manifest_input_order_and_module_roots_are_exact(self):
        manifest = self.load_manifest()
        manifest["inputs"][2], manifest["inputs"][3] = manifest["inputs"][3], manifest["inputs"][2]
        self.write_manifest(manifest)
        with self.assertRaisesRegex(audit.AuditError, "input order differs"):
            audit.audit(self.repo)

        cases = (
            ("destination", "redirected.rs"),
            ("repository_path", "host-kernel/native-rust/mcctrl.rs"),
            ("sha256", "0" * 64),
        )
        for field, value in cases:
            with self.subTest(field=field):
                with open(os.path.join(REPO_ROOT, audit.MANIFEST)) as stream:
                    manifest = json.load(stream)
                manifest["modules"][0]["source"][field] = value
                self.write_manifest(manifest)
                with self.assertRaisesRegex(audit.AuditError, "module root binding differs"):
                    audit.audit(self.repo)

        with open(os.path.join(REPO_ROOT, audit.MANIFEST)) as stream:
            self.write_manifest(json.load(stream))
        root = os.path.join(self.repo, "host-kernel", "native-rust", "ihk.rs")
        with open(root, "a") as stream:
            stream.write("\n// root drift\n")
        with self.assertRaisesRegex(audit.AuditError, "module root digest drift"):
            audit.audit(self.repo)

    def test_nested_mod_and_explicit_path_require_new_manifest_inputs(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        with open(path, "a") as stream:
            stream.write("\nmod unexpected_nested;\n")
        nested = os.path.join(self.repo, "host-kernel/native-rust/smp_service")
        os.makedirs(nested)
        with open(os.path.join(nested, "unexpected_nested.rs"), "w") as stream:
            stream.write("pub const PRESENT: bool = true;\n")
        self.rehash("smp_service.rs")
        with self.assertRaisesRegex(audit.AuditError, "destinations differ"):
            audit.audit(self.repo)
        shutil.copyfile(os.path.join(REPO_ROOT, relative), path)
        with open(os.path.join(self.repo, "host-kernel/native-rust/explicit_nested.rs"), "w") as stream:
            stream.write("pub const PRESENT: bool = true;\n")
        with open(path, "a") as stream:
            stream.write('\n#[path = "explicit_nested.rs"] mod redirected;\n')
        self.rehash("smp_service.rs")
        with self.assertRaisesRegex(audit.AuditError, "destinations differ"):
            audit.audit(self.repo)

    def test_embedded_assembly_omission_redirect_and_drift_fail_closed(self):
        manifest = self.load_manifest()
        manifest["inputs"] = [item for item in manifest["inputs"]
                              if item["destination"] != "smp_trampoline.S"]
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)
        shutil.copyfile(os.path.join(REPO_ROOT, audit.MANIFEST), self.manifest_path)
        manifest = self.load_manifest()
        item = next(item for item in manifest["inputs"]
                    if item["destination"] == "smp_trampoline.S")
        item["repository_path"] = "host-kernel/native-rust/smp_startup_entry.S"
        self.write_manifest(manifest)
        with self.assertRaisesRegex(audit.AuditError, "redirected"):
            audit.audit(self.repo)
        shutil.copyfile(os.path.join(REPO_ROOT, audit.MANIFEST), self.manifest_path)
        manifest = self.load_manifest()
        item = next(item for item in manifest["inputs"]
                    if item["destination"] == "smp_trampoline.S")
        item["kind"] = "rust_support_module"
        self.write_manifest(manifest)
        with self.assertRaisesRegex(audit.AuditError, "kind differs"):
            audit.audit(self.repo)
        shutil.copyfile(os.path.join(REPO_ROOT, audit.MANIFEST), self.manifest_path)
        with open(os.path.join(self.repo, "host-kernel/native-rust/smp_trampoline.S"), "ab") as stream:
            stream.write(b"\n# drift\n")
        with self.assertRaisesRegex(audit.AuditError, "digest drift"):
            audit.audit(self.repo)

    def test_malformed_or_escaped_dependencies_fail_closed(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        for suffix in ('#[path = "../escape.rs"] mod escape;',
                       '#[cfg_attr(all(), path = "escape.rs")] mod escape;',
                       'include!("escape.rs");'):
            with self.subTest(suffix=suffix):
                shutil.copyfile(os.path.join(REPO_ROOT, relative), path)
                with open(path, "a") as stream:
                    stream.write("\n" + suffix + "\n")
                self.rehash("smp_service.rs")
                with self.assertRaises(audit.AuditError):
                    audit.audit(self.repo)

    def test_generated_compatibility_include_cannot_be_reused(self):
        relative = "host-kernel/native-rust/smp_boot_code.rs"
        path = os.path.join(self.repo, relative)
        with open(path, "a") as stream:
            stream.write('\nconst SECOND_ID: &[u8] = include_bytes!("ihk-compat-build-id.bin");\n')
        self.rehash("smp_boot_code.rs")
        with self.assertRaisesRegex(audit.AuditError, "generated compatibility byte"):
            audit.audit(self.repo)

    def test_attribute_include_is_a_dependency_and_unbound_input_is_rejected(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        with open(path, "a") as stream:
            stream.write('\n#[doc = include_str!("attribute_data.txt")]\nconst ATTRIBUTE: u8 = 1;\n')
        payload = os.path.join(self.repo, "host-kernel/native-rust/attribute_data.txt")
        with open(payload, "w") as stream:
            stream.write("documentation bytes\n")
        self.rehash("smp_service.rs")
        closure = audit.discover_native_closure(self.repo)
        self.assertIn("attribute_data.txt", closure)
        with self.assertRaisesRegex(audit.AuditError, "destinations differ"):
            audit.audit(self.repo)
        os.unlink(payload)
        with self.assertRaisesRegex(audit.AuditError, "embedded source.*missing"):
            audit.audit(self.repo)

    def test_string_brace_does_not_end_inline_module_scope(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        with open(path, "a") as stream:
            stream.write('\nmod inline { const BRACE: &str = "}"; mod child; }\n')
        correct = os.path.join(self.repo, "host-kernel/native-rust/smp_service/inline")
        decoy = os.path.join(self.repo, "host-kernel/native-rust/inline")
        os.makedirs(correct)
        os.makedirs(decoy)
        with open(os.path.join(correct, "child.rs"), "w") as stream:
            stream.write("pub const CHILD: u8 = 1;\n")
        with open(os.path.join(decoy, "child.rs"), "w") as stream:
            stream.write("pub const DECOY: u8 = 1;\n")
        self.rehash("smp_service.rs")
        closure = audit.discover_native_closure(self.repo)
        self.assertIn("smp_service/inline/child.rs", closure)
        self.assertNotIn("inline/child.rs", closure)
        with self.assertRaisesRegex(audit.AuditError, "destinations differ"):
            audit.audit(self.repo)

    def test_explicit_path_inside_inline_uses_outer_module_directory(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        with open(path, "a") as stream:
            stream.write('\nmod inline { #[path = "child.rs"] mod child; }\n')
        correct = os.path.join(self.repo, "host-kernel/native-rust/smp_service/inline")
        decoy = os.path.join(self.repo, "host-kernel/native-rust/inline")
        os.makedirs(correct)
        os.makedirs(decoy)
        with open(os.path.join(correct, "child.rs"), "w") as stream:
            stream.write("pub const CHILD: u8 = 1;\n")
        with open(os.path.join(decoy, "child.rs"), "w") as stream:
            stream.write("pub const DECOY: u8 = 1;\n")
        self.rehash("smp_service.rs")
        closure = audit.discover_native_closure(self.repo)
        self.assertIn("smp_service/inline/child.rs", closure)
        self.assertNotIn("inline/child.rs", closure)
        with self.assertRaisesRegex(audit.AuditError, "destinations differ"):
            audit.audit(self.repo)

    def test_module_is_parsed_even_if_also_reached_as_embedded_data(self):
        relative = "host-kernel/native-rust/smp_service.rs"
        path = os.path.join(self.repo, relative)
        with open(path, "a") as stream:
            stream.write('\n#[path = "dual_child.rs"] mod dual_child;\n'
                         'const CHILD_DATA: &str = include_str!("dual_child.rs");\n')
        child = os.path.join(self.repo, "host-kernel/native-rust/dual_child.rs")
        with open(child, "w") as stream:
            stream.write("mod grandchild;\n")
        grandparent = os.path.join(self.repo, "host-kernel/native-rust/dual_child")
        os.makedirs(grandparent)
        with open(os.path.join(grandparent, "grandchild.rs"), "w") as stream:
            stream.write("pub const GRANDCHILD: u8 = 1;\n")
        self.rehash("smp_service.rs")
        closure = audit.discover_native_closure(self.repo)
        self.assertIn("dual_child.rs", closure)
        self.assertIn("dual_child/grandchild.rs", closure)
        with self.assertRaisesRegex(audit.AuditError, "destinations differ"):
            audit.audit(self.repo)

    def test_native_source_tree_rejects_duplicate_build_controls(self):
        native = os.path.join(self.repo, "host-kernel", "native-rust")
        for name in ("Kconfig", "Kbuild", "Makefile", "kconfig"):
            with self.subTest(name=name):
                path = os.path.join(native, name)
                with open(path, "w") as stream:
                    stream.write("conflicting surface\n")
                with self.assertRaises(audit.AuditError):
                    audit.audit(self.repo)
                os.unlink(path)

    def test_symlinked_duplicate_build_control_is_rejected(self):
        native = os.path.join(self.repo, "host-kernel", "native-rust")
        os.symlink("../kbuild/Kconfig", os.path.join(native, "Kconfig"))
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_the_authority(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "Kconfig":
                item["repository_path"] = "host-kernel/native-rust/not-Kconfig"
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_the_supplemental_abi(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "abi/x86_64.rs":
                item["repository_path"] = "host-kernel/native-rust/README.md"
                item["sha256"] = digest(os.path.join(
                    self.repo, "host-kernel", "native-rust", "README.md"))
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_the_supplemental_queue_source(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "ikc_queue.rs":
                item["repository_path"] = "host-kernel/native-rust/README.md"
                item["sha256"] = digest(
                    os.path.join(self.repo, "host-kernel", "native-rust", "README.md")
                )
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_the_registry_support_module(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "os_registry.rs":
                item["repository_path"] = "host-kernel/native-rust/README.md"
                item["sha256"] = digest(os.path.join(
                    self.repo, "host-kernel", "native-rust", "README.md"))
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_the_device_registry_support_module(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "device_registry.rs":
                item["repository_path"] = "host-kernel/native-rust/README.md"
                item["sha256"] = digest(os.path.join(
                    self.repo, "host-kernel", "native-rust", "README.md"))
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_the_supplemental_master_source(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "ikc_master.rs":
                item["repository_path"] = "host-kernel/native-rust/README.md"
                item["sha256"] = digest(
                    os.path.join(self.repo, "host-kernel", "native-rust", "README.md")
                )
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_the_ioctl_dispatch_support_module(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "ihk_ioctl.rs":
                item["repository_path"] = "host-kernel/native-rust/README.md"
                item["sha256"] = digest(os.path.join(
                    self.repo, "host-kernel", "native-rust", "README.md"))
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_page_support_modules(self):
        for destination in ("page_allocator.rs", "page_owner_registry.rs"):
            with self.subTest(destination=destination):
                manifest = self.load_manifest()
                for item in manifest["inputs"]:
                    if item["destination"] == destination:
                        item["repository_path"] = "host-kernel/native-rust/README.md"
                        item["sha256"] = digest(os.path.join(
                            self.repo, "host-kernel", "native-rust", "README.md"))
                        break
                self.write_manifest(manifest)
                with self.assertRaises(audit.AuditError):
                    audit.audit(self.repo)
                shutil.copyfile(
                    os.path.join(REPO_ROOT, "host-kernel", "kbuild", "stage-manifest.json"),
                    self.manifest_path,
                )

    def test_manifest_cannot_redirect_the_smp_resource_policy(self):
        manifest = self.load_manifest()
        for item in manifest["inputs"]:
            if item["destination"] == "smp_resource.rs":
                item["repository_path"] = "host-kernel/native-rust/README.md"
                item["sha256"] = digest(os.path.join(
                    self.repo, "host-kernel", "native-rust", "README.md"))
                break
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_manifest_cannot_redirect_new_service_sources(self):
        for destination in (
            "os_service.rs",
            "abi/os_service.rs",
            "abi/application.rs",
        ):
            with self.subTest(destination=destination):
                manifest = self.load_manifest()
                for item in manifest["inputs"]:
                    if item["destination"] == destination:
                        item["repository_path"] = "host-kernel/native-rust/README.md"
                        item["sha256"] = digest(os.path.join(
                            self.repo, "host-kernel", "native-rust", "README.md"))
                        break
                self.write_manifest(manifest)
                with self.assertRaises(audit.AuditError):
                    audit.audit(self.repo)
                shutil.copyfile(
                    os.path.join(REPO_ROOT, "host-kernel", "kbuild", "stage-manifest.json"),
                    self.manifest_path,
                )

    def test_manifest_cannot_replace_new_service_sources(self):
        for destination in (
            "os_service.rs",
            "abi/os_service.rs",
            "abi/application.rs",
        ):
            with self.subTest(destination=destination):
                manifest = self.load_manifest()
                replacement = "host-kernel/native-rust/ikc_master.rs"
                for item in manifest["inputs"]:
                    if item["destination"] == destination:
                        item["repository_path"] = replacement
                        item["sha256"] = digest(os.path.join(
                            self.repo, *replacement.split("/")))
                        break
                self.write_manifest(manifest)
                with self.assertRaises(audit.AuditError):
                    audit.audit(self.repo)
                shutil.copyfile(
                    os.path.join(REPO_ROOT, "host-kernel", "kbuild", "stage-manifest.json"),
                    self.manifest_path,
                )

    def test_manifest_rejects_missing_or_extra_locked_sources(self):
        manifest = self.load_manifest()
        manifest["inputs"] = [
            item for item in manifest["inputs"] if item["destination"] != "os_service.rs"
        ]
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

        shutil.copyfile(
            os.path.join(REPO_ROOT, "host-kernel", "kbuild", "stage-manifest.json"),
            self.manifest_path,
        )
        manifest = self.load_manifest()
        manifest["inputs"].append({
            "destination": "unexpected.rs",
            "repository_path": "host-kernel/native-rust/README.md",
            "sha256": digest(os.path.join(
                self.repo, "host-kernel", "native-rust", "README.md")),
        })
        self.write_manifest(manifest)
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_authoritative_kconfig_rejects_legacy_symbol_family(self):
        self.mutate_authority(
            "Kconfig", "MCKERNEL_IHK_RUST", "MCKERNEL_RUST_IHK"
        )
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_authoritative_kconfig_rejects_hidden_if_after_rehash(self):
        self.mutate_authority(
            "Kconfig",
            "\nconfig MCKERNEL_IHK_RUST\n",
            "\nif UNREVIEWED\n\nconfig MCKERNEL_IHK_RUST\n",
        )
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_authoritative_kbuild_rejects_legacy_symbol_family(self):
        self.mutate_authority(
            "Kbuild", "CONFIG_MCKERNEL_IHK_RUST", "CONFIG_MCKERNEL_RUST_IHK"
        )
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_authoritative_kbuild_rejects_continued_comment_after_rehash(self):
        self.mutate_authority(
            "Kbuild",
            "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o\n",
            "# suppress provider mapping \\\n"
            "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o\n",
        )
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_authoritative_digest_drift_is_rejected(self):
        path = os.path.join(self.repo, "host-kernel", "kbuild", "Kconfig")
        with open(path, "a") as stream:
            stream.write("# unbound drift\n")
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_duplicate_manifest_key_is_rejected(self):
        with open(self.manifest_path, "r") as stream:
            text = stream.read()
        with open(self.manifest_path, "w") as stream:
            stream.write(text.replace("{\n", '{\n  "schema_version": 2,\n', 1))
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_cli_passes_on_repository(self):
        self.assertEqual(0, audit.main(["--repo", REPO_ROOT]))


if __name__ == "__main__":
    unittest.main()
