#!/usr/bin/env python3

from __future__ import print_function

import copy
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_license_inventory as inventory  # noqa: E402


def add_file(archive, name, payload):
    info = tarfile.TarInfo(name=name)
    info.size = len(payload)
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(payload))


def add_link(archive, name, target):
    info = tarfile.TarInfo(name=name)
    info.type = tarfile.SYMTYPE
    info.linkname = target
    info.mode = 0o777
    archive.addfile(info)


def synthetic_linux_archive(path, include_missing=True):
    with tarfile.open(str(path), "w:xz") as archive:
        root = tarfile.TarInfo(name="linux-test/")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        archive.addfile(root)
        add_file(
            archive,
            "linux-test/LICENSES/preferred/GPL-2.0",
            b"Valid-License-Identifier: GPL-2.0-only\nlicense text\n",
        )
        add_file(
            archive,
            "linux-test/drivers/example.c",
            b"// SPDX-License-Identifier: GPL-2.0-only\nint example;\n",
        )
        add_link(archive, "linux-test/drivers/example-link.c", "example.c")
        if include_missing:
            add_file(archive, "linux-test/firmware/blob.bin", b"\x00\x01\x02")


class LicenseInventoryTests(unittest.TestCase):
    def test_repository_capture_contract_passes(self):
        lock, series = inventory.check_repository(REPO_ROOT)
        self.assertEqual(1, lock["schema_version"])
        self.assertEqual(1, series["schema_version"])

    def test_local_compiler_patch_and_config_are_inventoried(self):
        items = inventory.repository_patch_items(
            REPO_ROOT, "0" * 40, {"GPL-2.0-only": "linux/COPYING"}
        )
        paths = {item["path"] for item in items}
        for relative in (
            "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch",
            "host-kernel/rocky/configs/native-rust-evidence.config",
        ):
            self.assertIn("repository/" + relative, paths)

    def test_repository_inventory_binds_rust_compatibility_patch(self):
        items = inventory.repository_patch_items(REPO_ROOT, "a" * 40, {})
        by_path = {item["path"]: item for item in items}
        for relative in (
            "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch",
            "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch",
            "host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch",
            "host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch",
            "host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch",
            "host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch",
            "host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch",
            "host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch",
            "host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch",
        ):
            item = by_path["repository/" + relative]
            patch = REPO_ROOT / relative
            self.assertEqual(patch.stat().st_size, item["size"])
            self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(), item["sha256"])
            self.assertEqual("repository-commit:" + "a" * 40, item["origin"])

    def test_repository_inventory_binds_rocky_rust_core_preimages(self):
        items = inventory.repository_patch_items(
            REPO_ROOT, "b" * 40, {"GPL-2.0": "linux/COPYING", "GPL-2.0-only": "linux/COPYING"}
        )
        by_path = {item["path"]: item for item in items}
        fixture_root = "scripts/tests/fixtures/rust-core-rocky-6.12"
        relatives = (
            "Documentation/kbuild/makefiles.rst",
            "arch/arm64/Makefile",
            "rust/Makefile",
            "init/Kconfig",
            "include/linux/blk-mq.h",
            "rust/bindings/lib.rs",
            "rust/uapi/lib.rs",
            "rust/kernel/init/macros.rs",
            "rust/kernel/lib.rs",
            "rust/kernel/block/mq/tag_set.rs",
            "rust/kernel/list/arc.rs",
            "rust/kernel/sync/arc.rs",
            "rust/macros/module.rs",
            "scripts/Makefile.build",
            "scripts/Makefile.compiler",
            "scripts/generate_rust_analyzer.py",
        )
        for relative in relatives:
            repository_relative = fixture_root + "/" + relative
            source = REPO_ROOT / repository_relative
            item = by_path["repository/" + repository_relative]
            self.assertEqual(source.stat().st_size, item["size"])
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(), item["sha256"]
            )
            self.assertEqual("repository-commit:" + "b" * 40, item["origin"])
        self.assertEqual(
            "captured-unreviewed",
            by_path["repository/" + fixture_root + "/arch/arm64/Makefile"]["review_status"],
        )
        self.assertEqual(
            "verified",
            by_path["repository/" + fixture_root + "/rust/Makefile"]["review_status"],
        )

    def test_linux_archive_maps_spdx_and_preserves_missing_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "linux.tar.xz"
            synthetic_linux_archive(archive)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            items, licenses = inventory.inventory_linux_archive(archive, digest)
        by_path = {item["path"]: item for item in items}
        self.assertEqual(
            "linux/LICENSES/preferred/GPL-2.0", licenses["GPL-2.0-only"]
        )
        source = by_path["linux/drivers/example.c"]
        self.assertEqual("verified", source["review_status"])
        self.assertEqual(
            ["linux/LICENSES/preferred/GPL-2.0"], source["license_text_paths"]
        )
        link = by_path["linux/drivers/example-link.c"]
        self.assertEqual("verified", link["review_status"])
        self.assertEqual(source["spdx_expression"], link["spdx_expression"])
        missing = by_path["linux/firmware/blob.bin"]
        self.assertEqual("captured-unreviewed", missing["review_status"])
        self.assertEqual("NOASSERTION", missing["spdx_expression"])
        self.assertEqual("missing-spdx", missing["_reason"])

    def test_archive_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "unsafe.tar.xz"
            with tarfile.open(str(archive_path), "w:xz") as archive:
                add_file(archive, "linux-test/../escape", b"bad")
            with self.assertRaises(inventory.InventoryError):
                inventory.inventory_linux_archive(archive_path, "0" * 64)

    def test_root_level_archive_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "root-file.tar.xz"
            with tarfile.open(str(archive_path), "w:xz") as archive:
                add_file(archive, "outside.c", b"bad")
            with self.assertRaisesRegex(inventory.InventoryError, "outside"):
                inventory.inventory_linux_archive(archive_path, "0" * 64)

    def test_duplicate_license_identifier_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "duplicate.tar.xz"
            with tarfile.open(str(archive_path), "w:xz") as archive:
                for suffix in ("preferred/one", "dual/two"):
                    add_file(
                        archive,
                        "linux-test/LICENSES/{0}".format(suffix),
                        b"Valid-License-Identifier: GPL-2.0-only\n",
                    )
            with self.assertRaisesRegex(inventory.InventoryError, "duplicate license"):
                inventory.inventory_linux_archive(archive_path, "0" * 64)

    def test_documented_exception_example_is_not_a_license_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "documented-exception.tar.xz"
            with tarfile.open(str(archive_path), "w:xz") as archive:
                add_file(
                    archive,
                    "linux-test/LICENSES/exceptions/GCC-exception-2.0",
                    b"SPDX-Exception-Identifier: GCC-exception-2.0\nexception text\n",
                )
                add_file(
                    archive,
                    "linux-test/Documentation/process/license-rules.rst",
                    b"Example:\n  SPDX-Exception-Identifier: GCC-exception-2.0\n",
                )
            items, licenses = inventory.inventory_linux_archive(
                archive_path, "0" * 64
            )
        self.assertEqual(
            "linux/LICENSES/exceptions/GCC-exception-2.0",
            licenses["GCC-exception-2.0"],
        )
        by_path = {item["path"]: item for item in items}
        documented = by_path["linux/Documentation/process/license-rules.rst"]
        self.assertEqual("captured-unreviewed", documented["review_status"])
        self.assertEqual("NOASSERTION", documented["spdx_expression"])

    def test_composite_valid_expression_does_not_claim_other_license_texts(self):
        prefix = (
            b"Valid-License-Identifier: GPL-2.0 OR GFDL-1.1-no-invariants-only\n"
            b"Valid-License-Identifier: GFDL-1.1-no-invariants-only\n"
        )
        self.assertEqual(
            ["GFDL-1.1-no-invariants-only"],
            inventory.license_identifiers(prefix),
        )

    def test_ambiguous_spdx_lines_remain_unreviewed(self):
        prefix = (
            b"// SPDX-License-Identifier: MIT\n"
            b"// SPDX-License-Identifier: GPL-2.0-only\n"
        )
        item = inventory.make_item(
            "linux/conflict.c", len(prefix), hashlib.sha256(prefix).hexdigest(),
            "synthetic", "regular", prefix
        )
        inventory.resolve_items(
            [item],
            {"MIT": "linux/LICENSES/preferred/MIT", "GPL-2.0-only": "linux/COPYING"},
        )
        self.assertEqual("captured-unreviewed", item["review_status"])
        self.assertEqual("ambiguous-spdx", item["_reason"])

    def test_spdx_text_inside_code_or_documentation_is_not_a_header(self):
        prefix = (
            b"prefix = '# SPDX-License-Identifier: '\n"
            b"  SPDX-License-Identifier: MIT\n"
        )
        item = inventory.make_item(
            "linux/example.py", len(prefix), hashlib.sha256(prefix).hexdigest(),
            "synthetic", "regular", prefix
        )
        self.assertEqual("captured-unreviewed", item["review_status"])
        self.assertEqual("NOASSERTION", item["spdx_expression"])
        self.assertEqual("missing-spdx", item["_reason"])

    def test_malformed_real_spdx_header_remains_unreviewed(self):
        prefix = b"// SPDX-License-Identifier: '\n"
        item = inventory.make_item(
            "linux/example.c", len(prefix), hashlib.sha256(prefix).hexdigest(),
            "synthetic", "regular", prefix
        )
        self.assertEqual("captured-unreviewed", item["review_status"])
        self.assertEqual("NOASSERTION", item["spdx_expression"])
        self.assertEqual("malformed-spdx", item["_reason"])

    def test_capture_is_deterministic_and_self_verifying(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "linux.tar.xz"
            synthetic_linux_archive(archive)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            items, _ = inventory.inventory_linux_archive(archive, digest)
            binding = {
                "container_image": "rocky@example@sha256:" + "1" * 64,
                "github_head_sha": "2" * 40,
                "github_repository": "phoenix-hacking/mckernel",
                "github_run_attempt": "1",
                "github_run_id": "2",
            }
            first = root / "first"
            second = root / "second"
            summary = inventory.write_capture(
                first, copy.deepcopy(items), binding, "3" * 64, "4" * 64
            )
            inventory.write_capture(
                second, copy.deepcopy(items), binding, "3" * 64, "4" * 64
            )
            self.assertEqual(
                (first / "license-inventory.jsonl.gz").read_bytes(),
                (second / "license-inventory.jsonl.gz").read_bytes(),
            )
            verified = inventory.verify_capture(first)
            self.assertEqual(summary["inventory"]["item_count"], verified["inventory"]["item_count"])
            self.assertFalse(verified["complete"])
            self.assertEqual(1, verified["unresolved_count"])

    def test_capture_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "linux.tar.xz"
            synthetic_linux_archive(archive, include_missing=False)
            items, _ = inventory.inventory_linux_archive(
                archive, hashlib.sha256(archive.read_bytes()).hexdigest()
            )
            output = root / "capture"
            inventory.write_capture(output, items, {}, "3" * 64, "4" * 64)
            path = output / "license-inventory.jsonl.gz"
            path.write_bytes(path.read_bytes() + b"tamper")
            with self.assertRaises(inventory.InventoryError):
                inventory.verify_capture(output)

    def test_relative_paths_reject_ambiguous_forms(self):
        for value in ("", "/absolute", "../escape", "a/../b", "a/./b"):
            with self.subTest(value=value):
                with self.assertRaises(inventory.InventoryError):
                    inventory.safe_relative(value, "test")


if __name__ == "__main__":
    unittest.main()
