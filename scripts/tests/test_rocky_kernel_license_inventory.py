#!/usr/bin/env python3

from __future__ import print_function

import ast
import copy
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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


def binding(head="2" * 40):
    return {
        "container_image": inventory.EXPECTED_CONTAINER_IMAGE,
        "github_head_sha": head,
        "github_repository": "phoenix-hacking/mckernel",
        "github_run_attempt": "1",
        "github_run_id": "2",
    }


def git(repo, *arguments):
    completed = subprocess.run(
        ["git"] + list(arguments),
        cwd=str(repo),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("ascii").strip()


def synthetic_capture_inputs(root):
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "user.email", "capture@example.test")
    git(repo, "config", "user.name", "Capture Fixture")
    for relative in inventory.EXPECTED_REPOSITORY_INPUT_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "host-kernel/kbuild/stage-manifest.json":
            path.write_bytes((REPO_ROOT / relative).read_bytes())
        else:
            path.write_text("fixture for {0}\n".format(relative), encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "fixture")
    head = git(repo, "rev-parse", "HEAD")

    linux = LicenseInventoryTests.synthetic_item()
    dist_payload = b"dist-git fixture\n"
    dist_git = inventory.make_item(
        "dist-git/example",
        len(dist_payload),
        hashlib.sha256(dist_payload).hexdigest(),
        "rocky-dist-git:{0}".format(inventory.EXPECTED_DIST_GIT_COMMIT),
        "regular",
        dist_payload,
        source_identity={"git_blob_oid": "1" * 40, "git_mode": "100644"},
    )
    srpm_payload = b"SRPM fixture\n"
    srpm = inventory.make_item(
        "srpm/SOURCES/example",
        len(srpm_payload),
        hashlib.sha256(srpm_payload).hexdigest(),
        "srpm:sha256:{0}".format(inventory.EXPECTED_SOURCE_RPM_SHA256),
        "regular",
        srpm_payload,
        source_identity={
            "source_rpm_sha256": inventory.EXPECTED_SOURCE_RPM_SHA256
        },
    )
    bound = binding(head)
    repository = inventory.repository_patch_items(repo, head, {})
    items = [linux, dist_git, srpm] + repository
    static = {
        "dist-git": inventory.source_closure([dist_git]),
        "linux": inventory.source_closure([linux]),
        "srpm": inventory.source_closure([srpm]),
    }
    return repo, bound, items, static


def committed_current_repository_inputs(root):
    repo = root / "current-repository-inputs"
    repo.mkdir()
    git(repo, "init", "--quiet")
    git(repo, "config", "user.email", "capture@example.test")
    git(repo, "config", "user.name", "Capture Fixture")
    for relative in inventory.EXPECTED_REPOSITORY_INPUT_PATHS:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO_ROOT / relative).read_bytes())
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "exact repository inputs")
    return repo, git(repo, "rev-parse", "HEAD")


def rewrite_capture(directory, items):
    ordered = sorted(items, key=lambda item: item["path"])
    raw = b"".join(inventory.canonical_json(item) + b"\n" for item in ordered)
    inventory_path = directory / "license-inventory.jsonl.gz"
    with inventory_path.open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as zipped:
            zipped.write(raw)
    compressed_size, compressed_sha = inventory.hash_file(inventory_path)
    summary_path = directory / "license-inventory-summary.json"
    summary = json.loads(summary_path.read_text(encoding="ascii"))
    summary["inventory"].update(
        {
            "compressed_sha256": compressed_sha,
            "compressed_size": compressed_size,
            "item_count": len(ordered),
            "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    summary["review_counts"] = {"captured-unreviewed": len(ordered)}
    summary["signal_issue_count"] = sum(
        item["unresolved_reasons"] != ["independent-review-required"]
        for item in ordered
    )
    summary["unresolved_count"] = len(ordered)
    summary["unresolved_sample"] = [
        {"path": item["path"], "reasons": item["unresolved_reasons"]}
        for item in ordered[:200]
    ]
    summary_path.write_bytes(inventory.canonical_json(summary) + b"\n")
    _, summary_sha = inventory.hash_file(summary_path)
    (directory / "SHA256SUMS").write_text(
        "{0}  license-inventory.jsonl.gz\n{1}  license-inventory-summary.json\n".format(
            compressed_sha, summary_sha
        ),
        encoding="ascii",
    )


class LicenseInventoryTests(unittest.TestCase):
    def test_inventory_and_review_scripts_retain_python_3_6_syntax(self):
        forbidden = (
            ".is_relative" + "_to(",
            ".remove" + "prefix(",
            ".remove" + "suffix(",
            "capture_" + "output=",
            "missing_" + "ok=",
        )
        for relative in (
            "scripts/rocky_kernel_license_inventory.py",
            "scripts/rocky_kernel_source_review.py",
            "scripts/tests/test_rocky_kernel_license_inventory.py",
            "scripts/tests/test_rocky_kernel_source_review.py",
        ):
            path = REPO_ROOT / relative
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=str(path), feature_version=6)
            self.assertIsNotNone(tree)
            for fragment in forbidden:
                self.assertNotIn(fragment, source, relative)

    def test_repository_capture_contract_passes(self):
        lock, series = inventory.check_repository(REPO_ROOT)
        self.assertEqual(1, lock["schema_version"])
        self.assertEqual(1, series["schema_version"])

    def test_local_compiler_patch_and_config_are_inventoried(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo, head = committed_current_repository_inputs(Path(temporary))
            items = inventory.repository_patch_items(repo, head, {})
        paths = {item["path"] for item in items}
        self.assertEqual(len(inventory.EXPECTED_REPOSITORY_INPUT_PATHS), len(paths))
        for relative in (
            "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch",
            "host-kernel/rocky/configs/native-rust-evidence.config",
        ):
            self.assertIn("repository/" + relative, paths)

    def test_repository_inventory_binds_rust_compatibility_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo, head = committed_current_repository_inputs(Path(temporary))
            items = inventory.repository_patch_items(repo, head, {})
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
                "host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch",
                "host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch",
                "host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch",
                "host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch",
                "host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch",
                "host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch",
                "host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch",
                "host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch",
                "host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch",
                "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
                "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch",
                "host-kernel/rocky/patches/0020a-rust-miscdevice-bind-file-operations-to-module.patch",
                "host-kernel/rocky/patches/0021-objtool-recognize-rust-1.92-panic-const.patch",
                "host-kernel/rocky/patches/0022-x86-pvh-annotate-noendbr.patch",
                "host-kernel/rocky/patches/0023-rust-update-no-alloc-shim-marker-rust-1.92.patch",
            ):
                item = by_path["repository/" + relative]
                patch = REPO_ROOT / relative
                self.assertEqual(patch.stat().st_size, item["size"])
                self.assertEqual(
                    hashlib.sha256(patch.read_bytes()).hexdigest(), item["sha256"]
                )
                self.assertEqual("repository-commit:" + head, item["origin"])
                self.assertEqual(
                    {
                        "git_blob_oid": git(repo, "rev-parse", head + ":" + relative),
                        "git_commit": head,
                    },
                    item["source_identity"],
                )

    def test_repository_inventory_derives_every_staged_source_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo, head = committed_current_repository_inputs(Path(temporary))
            self.assertEqual(
                inventory.EXPECTED_STAGE_REPOSITORY_INPUT_PATHS,
                inventory.stage_repository_input_paths(repo),
            )
            by_path = {
                item["path"]: item
                for item in inventory.repository_patch_items(repo, head, {})
            }
            for relative in inventory.EXPECTED_STAGE_REPOSITORY_INPUT_PATHS:
                self.assertIn("repository/" + relative, by_path)

    def test_repository_inventory_binds_current_native_foundations(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo, head = committed_current_repository_inputs(Path(temporary))
            by_path = {
                item["path"]: item
                for item in inventory.repository_patch_items(repo, head, {})
            }
        for relative in (
            "host-kernel/native-rust/ikc_master.rs",
            "host-kernel/native-rust/ikc_queue.rs",
            "host-kernel/native-rust/ihk_ioctl.rs",
            "host-kernel/native-rust/os_registry.rs",
            "host-kernel/native-rust/page_allocator.rs",
            "host-kernel/native-rust/page_owner_registry.rs",
            "scripts/tests/fixtures/ihk_native_master_compile.rs",
            "scripts/tests/fixtures/ihk_native_queue_compile.rs",
            "scripts/tests/fixtures/ihk_ioctl_dispatch_compile.rs",
            "scripts/tests/fixtures/ihk_os_registry_compile.rs",
            "scripts/tests/fixtures/ihk_page_allocator_compile.rs",
            "scripts/tests/fixtures/ihk_page_allocator_lifetime_compile_fail.rs",
            "scripts/tests/fixtures/ihk_page_allocator_must_use_compile_fail.rs",
            "scripts/tests/fixtures/ihk_page_owner_registry_compile.rs",
            "scripts/tests/fixtures/ihk_page_owner_registry_lifetime_compile_fail.rs",
            "scripts/tests/fixtures/ihk_page_owner_registry_sync_compile_fail.rs",
        ):
            item = by_path["repository/" + relative]
            source = REPO_ROOT / relative
            self.assertEqual(source.stat().st_size, item["size"])
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(), item["sha256"]
            )

    def test_repository_inventory_binds_full_rust_core_preimages(self):
        fixture_root = "scripts/tests/fixtures/rust-core-rocky-6.12/"
        relatives = (
            "Documentation/kbuild/makefiles.rst",
            "Makefile",
            "arch/arm64/Makefile",
            "arch/loongarch/kernel/Makefile",
            "arch/loongarch/kvm/Makefile",
            "arch/riscv/kernel/Makefile",
            "fs/netfs/fscache_cache.c",
            "fs/netfs/fscache_cookie.c",
            "init/Kconfig",
            "mm/ksm.c",
            "rust/Makefile",
            "rust/bindings/bindings_helper.h",
            "rust/bindings/lib.rs",
            "rust/kernel/alloc/allocator.rs",
            "rust/kernel/ioctl.rs",
            "rust/kernel/uaccess.rs",
            "rust/kernel/types.rs",
            "rust/uapi/lib.rs",
            "scripts/Makefile.compiler",
            "scripts/generate_rust_analyzer.py",
            "mm/ksm.c",
            "fs/netfs/fscache_cache.c",
            "fs/netfs/fscache_cookie.c",
        )
        with tempfile.TemporaryDirectory() as temporary:
            repo, head = committed_current_repository_inputs(Path(temporary))
            items = inventory.repository_patch_items(repo, head, {})
            by_path = {item["path"]: item for item in items}
            for relative in relatives:
                repository_relative = fixture_root + relative
                item = by_path["repository/" + repository_relative]
                source = REPO_ROOT / repository_relative
                self.assertEqual(source.stat().st_size, item["size"])
                self.assertEqual(
                    hashlib.sha256(source.read_bytes()).hexdigest(), item["sha256"]
                )
                self.assertEqual("repository-commit:" + head, item["origin"])
                self.assertEqual(
                    {
                        "git_blob_oid": git(
                            repo, "rev-parse", head + ":" + repository_relative
                        ),
                        "git_commit": head,
                    },
                    item["source_identity"],
                )

    def test_linux_archive_maps_spdx_and_preserves_missing_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "linux.tar.xz"
            synthetic_linux_archive(archive)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            items, licenses = inventory.inventory_linux_archive(archive, digest)
        by_path = {item["path"]: item for item in items}
        self.assertEqual(
            ["linux/LICENSES/preferred/GPL-2.0"], licenses["GPL-2.0-only"]
        )
        source = by_path["linux/drivers/example.c"]
        self.assertEqual("captured-unreviewed", source["review_status"])
        self.assertEqual(
            ["linux/LICENSES/preferred/GPL-2.0"], source["license_text_paths"]
        )
        link = by_path["linux/drivers/example-link.c"]
        self.assertEqual("captured-unreviewed", link["review_status"])
        self.assertEqual(source["spdx_expression"], link["spdx_expression"])
        self.assertIn("link-provenance-needs-review", link["unresolved_reasons"])
        missing = by_path["linux/firmware/blob.bin"]
        self.assertEqual("captured-unreviewed", missing["review_status"])
        self.assertEqual("NOASSERTION", missing["spdx_expression"])
        self.assertIn("missing-spdx", missing["unresolved_reasons"])

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

    def test_legitimate_multiple_license_texts_are_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "duplicate.tar.xz"
            with tarfile.open(str(archive_path), "w:xz") as archive:
                for suffix in ("preferred/one", "dual/two"):
                    add_file(
                        archive,
                        "linux-test/LICENSES/{0}".format(suffix),
                        b"Valid-License-Identifier: GPL-2.0-only\n",
                    )
            items, licenses = inventory.inventory_linux_archive(
                archive_path, "0" * 64
            )
        self.assertEqual(
            [
                "linux/LICENSES/dual/two",
                "linux/LICENSES/preferred/one",
            ],
            licenses["GPL-2.0-only"],
        )
        self.assertTrue(items)

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
            ["linux/LICENSES/exceptions/GCC-exception-2.0"],
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
            {
                "MIT": ["linux/LICENSES/preferred/MIT"],
                "GPL-2.0-only": ["linux/COPYING"],
            },
        )
        self.assertEqual("captured-unreviewed", item["review_status"])
        self.assertIn("ambiguous-spdx", item["unresolved_reasons"])

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
        self.assertIn("missing-spdx", item["unresolved_reasons"])

    def test_malformed_real_spdx_header_remains_unreviewed(self):
        prefix = b"// SPDX-License-Identifier: '\n"
        item = inventory.make_item(
            "linux/example.c", len(prefix), hashlib.sha256(prefix).hexdigest(),
            "synthetic", "regular", prefix
        )
        self.assertEqual("captured-unreviewed", item["review_status"])
        self.assertEqual("NOASSERTION", item["spdx_expression"])
        self.assertIn("malformed-spdx", item["unresolved_reasons"])

    def test_capture_is_deterministic_and_self_verifying(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, bound, items, static = synthetic_capture_inputs(root)
            first = root / "first"
            second = root / "second"
            with mock.patch.object(
                inventory, "EXPECTED_STATIC_NAMESPACE_CLOSURES", static
            ):
                summary = inventory.write_capture(
                    first,
                    copy.deepcopy(items),
                    bound,
                    inventory.EXPECTED_SOURCE_LOCK_SHA256,
                    inventory.EXPECTED_PATCH_SERIES_SHA256,
                    repo,
                )
                inventory.write_capture(
                    second,
                    copy.deepcopy(items),
                    bound,
                    inventory.EXPECTED_SOURCE_LOCK_SHA256,
                    inventory.EXPECTED_PATCH_SERIES_SHA256,
                    repo,
                )
                verified = inventory.verify_capture(first, repo)
            self.assertEqual(
                (first / "license-inventory.jsonl.gz").read_bytes(),
                (second / "license-inventory.jsonl.gz").read_bytes(),
            )
            self.assertEqual(summary["inventory"]["item_count"], verified["inventory"]["item_count"])
            self.assertFalse(verified["complete"])
            self.assertEqual(
                verified["inventory"]["item_count"], verified["unresolved_count"]
            )
            self.assertTrue(
                all(
                    value["complete"]
                    for value in verified["scope"]["namespaces"].values()
                )
            )

    def test_capture_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, bound, items, static = synthetic_capture_inputs(root)
            output = root / "capture"
            with mock.patch.object(
                inventory, "EXPECTED_STATIC_NAMESPACE_CLOSURES", static
            ):
                inventory.write_capture(
                    output,
                    items,
                    bound,
                    inventory.EXPECTED_SOURCE_LOCK_SHA256,
                    inventory.EXPECTED_PATCH_SERIES_SHA256,
                    repo,
                )
            path = output / "license-inventory.jsonl.gz"
            path.write_bytes(path.read_bytes() + b"tamper")
            with self.assertRaises(inventory.InventoryError):
                inventory.verify_capture(output, repo)

    def test_fully_rehashed_one_row_capture_cannot_claim_complete_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, bound, items, static = synthetic_capture_inputs(root)
            output = root / "capture"
            with mock.patch.object(
                inventory, "EXPECTED_STATIC_NAMESPACE_CLOSURES", static
            ):
                inventory.write_capture(
                    output,
                    copy.deepcopy(items),
                    bound,
                    inventory.EXPECTED_SOURCE_LOCK_SHA256,
                    inventory.EXPECTED_PATCH_SERIES_SHA256,
                    repo,
                )
                rewrite_capture(
                    output,
                    [item for item in items if item["path"].startswith("linux/")][
                        :1
                    ],
                )
                with self.assertRaisesRegex(
                    inventory.InventoryError, "omits|required source|closure"
                ):
                    inventory.verify_capture(output, repo)

    def test_verification_replays_repository_bytes_and_exact_git_blobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, bound, items, static = synthetic_capture_inputs(root)
            output = root / "capture"
            with mock.patch.object(
                inventory, "EXPECTED_STATIC_NAMESPACE_CLOSURES", static
            ):
                inventory.write_capture(
                    output,
                    items,
                    bound,
                    inventory.EXPECTED_SOURCE_LOCK_SHA256,
                    inventory.EXPECTED_PATCH_SERIES_SHA256,
                    repo,
                )
                target = repo / inventory.EXPECTED_REPOSITORY_INPUT_PATHS[0]
                target.write_text("working-tree substitution\n", encoding="utf-8")
                with self.assertRaisesRegex(
                    inventory.InventoryError, "bound repository commit"
                ):
                    inventory.verify_capture(output, repo)

    def test_machine_capture_cannot_self_attest_review_or_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, bound, items, static = synthetic_capture_inputs(root)
            forged = copy.deepcopy(items)
            forged[0]["review_status"] = "verified"
            with self.assertRaisesRegex(inventory.InventoryError, "reviewed"):
                inventory.write_capture(
                    root / "forged",
                    forged,
                    bound,
                    inventory.EXPECTED_SOURCE_LOCK_SHA256,
                    inventory.EXPECTED_PATCH_SERIES_SHA256,
                    repo,
                )

            output = root / "valid"
            with mock.patch.object(
                inventory, "EXPECTED_STATIC_NAMESPACE_CLOSURES", static
            ):
                inventory.write_capture(
                    output,
                    items,
                    bound,
                    inventory.EXPECTED_SOURCE_LOCK_SHA256,
                    inventory.EXPECTED_PATCH_SERIES_SHA256,
                    repo,
                )
            summary_path = output / "license-inventory-summary.json"
            summary = json.loads(summary_path.read_text(encoding="ascii"))
            summary["complete"] = True
            summary["review_complete"] = True
            summary_path.write_bytes(inventory.canonical_json(summary) + b"\n")
            with self.assertRaises(inventory.InventoryError):
                inventory.verify_capture(output, repo)

    def test_capture_authorities_are_exact_not_merely_well_formed(self):
        valid = binding()
        for mutation in ("container", "lock", "series"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(valid)
                lock_sha = inventory.EXPECTED_SOURCE_LOCK_SHA256
                series_sha = inventory.EXPECTED_PATCH_SERIES_SHA256
                if mutation == "container":
                    changed["container_image"] = "rocky@example@sha256:" + "0" * 64
                    with self.assertRaises(inventory.InventoryError):
                        inventory.validate_capture_binding(changed)
                elif mutation == "lock":
                    with tempfile.TemporaryDirectory() as temporary:
                        with self.assertRaises(inventory.InventoryError):
                            inventory.write_capture(
                                Path(temporary) / "capture",
                                [self.synthetic_item()],
                                changed,
                                "0" * 64,
                                series_sha,
                                REPO_ROOT,
                            )
                else:
                    with tempfile.TemporaryDirectory() as temporary:
                        with self.assertRaises(inventory.InventoryError):
                            inventory.write_capture(
                                Path(temporary) / "capture",
                                [self.synthetic_item()],
                                changed,
                                lock_sha,
                                "0" * 64,
                                REPO_ROOT,
                            )

    @staticmethod
    def synthetic_item():
        return inventory.make_item(
            "linux/example.c",
            0,
            hashlib.sha256(b"").hexdigest(),
            "linux-archive:sha256:{0}".format(
                inventory.EXPECTED_LINUX_ARCHIVE_SHA256
            ),
            "regular",
            b"// SPDX-License-Identifier: MIT\n",
            source_identity={
                "archive_sha256": inventory.EXPECTED_LINUX_ARCHIVE_SHA256
            },
        )

    def test_patch_authorship_and_missing_license_signals_are_explicit(self):
        payload = (
            b"From: Example Author <author@example.test>\n"
            b"Signed-off-by: Example Author <author@example.test>\n"
        )
        item = inventory.make_item(
            "dist-git/example.patch",
            len(payload),
            hashlib.sha256(payload).hexdigest(),
            "rocky-dist-git:{0}".format(inventory.EXPECTED_DIST_GIT_COMMIT),
            "regular",
            payload,
            source_identity={"git_blob_oid": "1" * 40, "git_mode": "100644"},
        )
        self.assertEqual(
            ["Example Author <author@example.test>"], item["authorship_signals"]
        )
        self.assertIn("patch-license-signal-missing", item["unresolved_reasons"])
        inventory.validate_generated_item(item)

    def test_dist_git_tree_is_complete_bounded_and_mode_explicit(self):
        rows = inventory.parse_tree(
            b"100644 blob " + b"1" * 40 + b"\tregular\0"
            b"120000 blob " + b"2" * 40 + b"\tlink\0"
        )
        self.assertEqual(
            [("regular", "100644", "1" * 40), ("link", "120000", "2" * 40)],
            rows,
        )
        with self.assertRaises(inventory.InventoryError):
            inventory.parse_tree(
                b"100644 blob " + b"1" * 40 + b"\tduplicate\0"
                b"100644 blob " + b"2" * 40 + b"\tduplicate\0"
            )

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"a":1,"a":2}\n', encoding="ascii")
            with self.assertRaises(inventory.InventoryError):
                inventory.read_json(path)

    def test_relative_paths_reject_ambiguous_forms(self):
        for value in ("", "/absolute", "../escape", "a/../b", "a/./b"):
            with self.subTest(value=value):
                with self.assertRaises(inventory.InventoryError):
                    inventory.safe_relative(value, "test")


if __name__ == "__main__":
    unittest.main()
