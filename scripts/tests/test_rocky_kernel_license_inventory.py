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
