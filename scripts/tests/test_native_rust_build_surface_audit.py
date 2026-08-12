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
        for relative in audit.SUPPLEMENTAL_INPUTS.values():
            destination = os.path.join(self.repo, *relative.split("/"))
            parent = os.path.dirname(destination)
            if not os.path.isdir(parent):
                os.makedirs(parent)
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

    def test_authoritative_kconfig_rejects_legacy_symbol_family(self):
        self.mutate_authority(
            "Kconfig", "MCKERNEL_IHK_RUST", "MCKERNEL_RUST_IHK"
        )
        with self.assertRaises(audit.AuditError):
            audit.audit(self.repo)

    def test_authoritative_kbuild_rejects_legacy_symbol_family(self):
        self.mutate_authority(
            "Kbuild", "CONFIG_MCKERNEL_IHK_RUST", "CONFIG_MCKERNEL_RUST_IHK"
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
