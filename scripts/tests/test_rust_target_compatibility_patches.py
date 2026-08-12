#!/usr/bin/env python3
"""Replay the frozen Rust compiler-compatibility patch series."""

from __future__ import print_function

import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PATCHES = (
    REPO_ROOT
    / "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch",
)
PREIMAGE = REPO_ROOT / "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs"
POSTIMAGE_SHA256 = "555ff4dff6548bb5f24087cdad737363b5694668aa462f77adfb3571498ec678"
CORE_PREIMAGE = REPO_ROOT / "scripts/tests/fixtures/rust-core-rocky-6.12"


class RustTargetCompatibilityPatchTests(unittest.TestCase):
    def test_every_patch_rejects_second_application(self):
        from scripts import linux_api_exact_probe as probe

        self.assertEqual(4, len(PATCHES))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "linux"
            shutil.copytree(str(CORE_PREIMAGE), str(root))
            target = root / "scripts/generate_rust_target.rs"
            target.write_bytes(PREIMAGE.read_bytes())
            command = ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i"]
            for patch in PATCHES:
                probe.run_checked(command + [str(patch)], root)
            for patch in PATCHES:
                with self.assertRaises(probe.ProbeError):
                    probe.run_checked(command + [str(patch)], root)

    def test_series_applies_in_order_to_exact_rocky_preimage(self):
        from scripts import linux_api_exact_probe as probe

        self.assertEqual(
            "9c21a1b67751db98e407439b77d014be6b92ba3cf6457fde6a4118a798f4fa05",
            probe.sha256_file(PREIMAGE),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "scripts/generate_rust_target.rs"
            target.parent.mkdir()
            target.write_bytes(PREIMAGE.read_bytes())
            for patch in PATCHES[:2]:
                probe.run_checked(
                    ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i", str(patch)],
                    root,
                )
            self.assertEqual(POSTIMAGE_SHA256, probe.sha256_file(target))
            text = target.read_text(encoding="utf-8")
            self.assertEqual(2, text.count('ts.push("rustc-abi", "x86-softfloat")'))
            self.assertEqual(1, text.count('ts.push("target-pointer-width", 64)'))
            self.assertEqual(1, text.count('ts.push("target-pointer-width", 32)'))

    def test_second_patch_alone_cannot_form_the_accepted_postimage(self):
        from scripts import linux_api_exact_probe as probe

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "scripts/generate_rust_target.rs"
            target.parent.mkdir()
            target.write_bytes(PREIMAGE.read_bytes())
            probe.run_checked(
                ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i", str(PATCHES[1])],
                root,
            )
            self.assertNotEqual(POSTIMAGE_SHA256, probe.sha256_file(target))
            self.assertNotIn(
                'ts.push("rustc-abi", "x86-softfloat")',
                target.read_text(encoding="utf-8"),
            )

    def test_core_series_applies_in_order_to_exact_rocky_preimages(self):
        from scripts import linux_api_exact_probe as probe

        for relative, digest in probe.RUST_CORE_COMPAT_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "linux"
            shutil.copytree(str(CORE_PREIMAGE), str(root))
            for patch in PATCHES[2:]:
                probe.run_checked(
                    ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i", str(patch)],
                    root,
                )
            for relative, digest in probe.RUST_CORE_COMPAT_POSTIMAGE_SHA256S:
                self.assertEqual(digest, probe.sha256_file(root / relative))
            makefile = (root / "rust/Makefile").read_text(encoding="utf-8")
            compiler = (root / "scripts/Makefile.compiler").read_text(
                encoding="utf-8"
            )
            analyzer = (
                root / "scripts/generate_rust_analyzer.py"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "core-edition := $(if $(call rustc-min-version,108700),2024,2021)",
                makefile,
            )
            self.assertIn(
                "private skip_flags = --edition=2021 -Wunreachable_pub",
                makefile,
            )
            self.assertIn(
                "private rustc_target_flags = --edition=$(core-edition) $(core-cfgs)",
                makefile,
            )
            self.assertIn(
                "rustc-min-version = $(call test-ge, $(CONFIG_RUSTC_VERSION), $1)",
                compiler,
            )
            self.assertIn('parser.add_argument("core_edition")', analyzer)

    def test_core_edition_patch_without_version_helper_is_incomplete(self):
        from scripts import linux_api_exact_probe as probe

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "linux"
            shutil.copytree(str(CORE_PREIMAGE), str(root))
            probe.run_checked(
                ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i", str(PATCHES[3])],
                root,
            )
            self.assertNotIn(
                "rustc-min-version = ",
                (root / "scripts/Makefile.compiler").read_text(encoding="utf-8"),
            )
            self.assertNotEqual(
                dict(probe.RUST_CORE_COMPAT_POSTIMAGE_SHA256S)[
                    "scripts/Makefile.compiler"
                ],
                probe.sha256_file(root / "scripts/Makefile.compiler"),
            )


if __name__ == "__main__":
    unittest.main()
