#!/usr/bin/env python3
"""Replay the frozen Rust compiler-compatibility patch series."""

from __future__ import print_function

import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PATCHES = (
    REPO_ROOT
    / "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch",
)
PREIMAGE = REPO_ROOT / "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs"
POSTIMAGE_SHA256 = "555ff4dff6548bb5f24087cdad737363b5694668aa462f77adfb3571498ec678"


class RustTargetCompatibilityPatchTests(unittest.TestCase):
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
            for patch in PATCHES:
                probe.run_checked(
                    ["patch", "-p1", "--batch", "--forward", "-i", str(patch)],
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
                ["patch", "-p1", "--batch", "--forward", "-i", str(PATCHES[1])],
                root,
            )
            self.assertNotEqual(POSTIMAGE_SHA256, probe.sha256_file(target))
            self.assertNotIn(
                'ts.push("rustc-abi", "x86-softfloat")',
                target.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
