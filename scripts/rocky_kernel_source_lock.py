#!/usr/bin/env python3
"""Validate and acquire the checksum-pinned Rocky kernel source for RK-001.

``--check`` validates the immutable identities and reports (but does not hide)
missing evidence.  ``--gate-ready`` is the only gate-credit mode and fails
closed until every required signature, replay, and license item is verified.
Network acquisition is optional and publishes an SRPM into a deterministic
content-addressed cache only after its exact size and SHA-256 match the lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterable, Mapping, Sequence

import rocky_kernel_source_review as source_review


SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
PATCH_SERIES_PATH = Path("host-kernel/rocky/patches/series.json")
MAX_MANIFEST_BYTES = 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_SHA1 = re.compile(r"^[0-9a-f]{40}$")
LICENSE_EXPRESSION_SHA256 = (
    "91f37e234988053edb7757c43af2406fdced5ef2e2e01b316fe2dd474ff52e2f"
)
LICENSE_DECISION_PATH = "host-kernel/rocky/evidence/license-decision.json"
LICENSE_DECISION_ID = "rk-001-license-decision-v1"
# Gate closure needs an independently reviewed decision whose exact digest and
# authority are registered here in a later reviewed change.  Machine capture
# can never populate these values or make RK-001 eligible on its own.
EXPECTED_LICENSE_DECISION_SHA256: str | None = None
EXPECTED_LICENSE_REVIEW_AUTHORITY_ID: str | None = None
EXPECTED_LICENSE_CAPTURE_AUTHORITY: dict[str, Any] = {
    "authority_id": "rk-001-license-capture-source-closure-v1",
    "closure_algorithm": (
        "sha256 over canonical sorted path rows and canonical source-identity rows"
    ),
    "namespaces": {
        "dist-git": {
            "item_count": 77,
            "path_set_sha256": (
                "ffe07b597e0a3b72d5e29e7b05aea8e75bdf112d75068d3d72e28547a4833c22"
            ),
            "source_manifest_sha256": (
                "ac819ee853a73c109c2db5f8735b947c1fae6374fce8b3402779720fe5621e96"
            ),
        },
        "linux": {
            "item_count": 115027,
            "path_set_sha256": (
                "f7495feae099d970ef02bbb1a73a0669b88c83c33dad80d3cc6bfb4184b2b0c2"
            ),
            "source_manifest_sha256": (
                "321b8a227f7a9473a94db6fbf747c48727a39b20bd8a24474f68578915ca4e56"
            ),
        },
        "repository": {
            "paths": [
                "host-kernel/kbuild/parent-integration-v1.json",
                (
                    "host-kernel/kbuild/patches/"
                    "0001-drivers-misc-add-mckernel-rust-host-modules.patch"
                ),
                (
                    "host-kernel/kbuild/patches/"
                    "0002-rust-bindings-expose-module-parameters.patch"
                ),
                "host-kernel/kbuild/stage-manifest.json",
                "host-kernel/kbuild/Kbuild.in",
                "host-kernel/kbuild/Kconfig",
                "host-kernel/native-rust/abi/x86_64.rs",
                "host-kernel/native-rust/ihk.rs",
                "host-kernel/native-rust/ihk_ioctl.rs",
                "host-kernel/native-rust/ihk_smp_x86_64.rs",
                "host-kernel/native-rust/ikc_master.rs",
                "host-kernel/native-rust/ikc_queue.rs",
                "host-kernel/native-rust/mcctrl.rs",
                "host-kernel/native-rust/os_registry.rs",
                "host-kernel/native-rust/page_allocator.rs",
                "host-kernel/native-rust/page_owner_registry.rs",
                "host-kernel/rocky/configs/native-rust-evidence.config",
                "host-kernel/rocky/configs/rust-minimal.config",
                (
                    "host-kernel/rocky/patches/"
                    "0001-x86-rust-set-rustc-abi-x86-softfloat.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0002-rust-support-rust-1.91-target-spec.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0003-kbuild-rust-add-rustc-min-version.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0004-rust-compile-libcore-edition-2024.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0005-rust-clean-unnecessary-transmutes-lint.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0006-rust-init-allow-dead-code-rust-1.89.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0007-rust-use-used-compiler-rust-1.89.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0008-rust-enable-arbitrary-self-types-rust-1.92.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0009-rust-block-drop-removed-merge-flag.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0010-kbuild-disable-default-const-init-unsafe.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0011-mm-ksm-fix-clang-21-uninitialized.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0012-netfs-mark-nonstring-lookup-tables.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0013-lib-crypto-mark-binary-vectors-nonstring.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0014-gcc-15-mark-byte-arrays-nonstring.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0015-gcc-15-demote-unterminated-string-warning.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0016-gcc-15-disable-unterminated-string-warning.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0017-kbuild-use-cc-disable-warning.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0018-kbuild-order-unterminated-string-disable.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0019-rust-types-add-opaque-try-ffi-init.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0020-rust-miscdevice-add-base-abstraction.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0020a-rust-miscdevice-bind-file-operations-to-module.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0021-objtool-recognize-rust-1.92-panic-const.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0022-x86-pvh-annotate-noendbr.patch"
                ),
                (
                    "host-kernel/rocky/patches/"
                    "0023-rust-update-no-alloc-shim-marker-rust-1.92.patch"
                ),
                "host-kernel/rocky/patches/series.json",
                "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs",
                "scripts/tests/fixtures/ihk_native_master_compile.rs",
                "scripts/tests/fixtures/ihk_native_queue_compile.rs",
                "scripts/tests/fixtures/ihk_ioctl_dispatch_compile.rs",
                "scripts/tests/fixtures/ihk_os_registry_compile.rs",
                "scripts/tests/fixtures/ihk_page_allocator_compile.rs",
                (
                    "scripts/tests/fixtures/"
                    "ihk_page_allocator_lifetime_compile_fail.rs"
                ),
                (
                    "scripts/tests/fixtures/"
                    "ihk_page_allocator_must_use_compile_fail.rs"
                ),
                "scripts/tests/fixtures/ihk_page_owner_registry_compile.rs",
                (
                    "scripts/tests/fixtures/"
                    "ihk_page_owner_registry_lifetime_compile_fail.rs"
                ),
                (
                    "scripts/tests/fixtures/"
                    "ihk_page_owner_registry_sync_compile_fail.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "Documentation/kbuild/makefiles.rst"
                ),
                "scripts/tests/fixtures/rust-core-rocky-6.12/Makefile",
                "scripts/tests/fixtures/rust-core-rocky-6.12/arch/arm64/Makefile",
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "arch/loongarch/kernel/Makefile"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "arch/loongarch/kvm/Makefile"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "arch/riscv/kernel/Makefile"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "arch/x86/platform/pvh/head.S"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "drivers/iio/magnetometer/ak8974.c"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "drivers/input/joystick/magellan.c"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "drivers/net/wireless/ath/carl9170/fw.c"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "fs/cachefiles/key.c"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "fs/netfs/fscache_cache.c"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "fs/netfs/fscache_cookie.c"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "include/linux/blk-mq.h"
                ),
                "scripts/tests/fixtures/rust-core-rocky-6.12/init/Kconfig",
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "lib/crypto/aescfb.c"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "lib/crypto/aesgcm.c"
                ),
                "scripts/tests/fixtures/rust-core-rocky-6.12/mm/ksm.c",
                "scripts/tests/fixtures/rust-core-rocky-6.12/rust/Makefile",
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/bindings/bindings_helper.h"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/bindings/lib.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/alloc/allocator.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/block/mq/tag_set.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/ioctl.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/init/macros.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/lib.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/list/arc.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/sync/arc.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/types.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/kernel/uaccess.rs"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "rust/macros/module.rs"
                ),
                "scripts/tests/fixtures/rust-core-rocky-6.12/rust/uapi/lib.rs",
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "scripts/Makefile.build"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "scripts/Makefile.compiler"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "scripts/Makefile.extrawarn"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "scripts/generate_rust_analyzer.py"
                ),
                (
                    "scripts/tests/fixtures/rust-core-rocky-6.12/"
                    "tools/objtool/check.c"
                ),
            ],
            "verification": (
                "recompute exact blob OIDs, bytes, and closure from the bound Git commit"
            ),
        },
        "srpm": {
            "item_count": 71,
            "path_set_sha256": (
                "d599d27ba45a688e7f550f793dc467f48e3603fb77efb790331b5b8b42a4ee96"
            ),
            "source_manifest_sha256": (
                "8158ccfb1a5899e47962e45ad107d04e0747fdf0951f167039e7ae3e13d84f47"
            ),
        },
    },
    "scope_is_derived_from_verified_closures": True,
}
EXPECTED_LICENSE_INVENTORY_ITEM_COUNT = sum(
    namespace["item_count"]
    for name, namespace in EXPECTED_LICENSE_CAPTURE_AUTHORITY["namespaces"].items()
    if name != "repository"
) + len(
    EXPECTED_LICENSE_CAPTURE_AUTHORITY["namespaces"]["repository"]["paths"]
)
EXPECTED_LICENSE_DECISION_REGISTRATION = (
    "an independently reviewed exact decision-manifest SHA-256 must be registered "
    "in the validator before RK-001 can close"
)
EXPECTED_LICENSE_ITEM_FIELDS = [
    "authorship_signals",
    "entry_type",
    "license_text_paths",
    "link_target",
    "origin",
    "path",
    "sha256",
    "size",
    "source_identity",
    "spdx_expression",
    "review_status",
    "unresolved_reasons",
]
SOURCE_EVIDENCE_REVIEW_PATH = Path(
    "host-kernel/rocky/evidence/source-evidence-review.json"
)
SOURCE_EVIDENCE_REVIEW_SHA256 = (
    "b4993bde598db1bacc39b73f4d5bfc78819bdc0e592d66475b700f824cba4896"
)
EXPECTED_REVIEWED_EVIDENCE: dict[str, dict[str, Any]] = {
    "acquisition_replay": {
        "blocker": None,
        "evidence_path": "host-kernel/rocky/evidence/acquisition-replay.json",
        "evidence_sha256": (
            "d37019bfa3c295867c68461c89bd70d9bcc8417e8dfc6ffd23ff46601280e2a0"
        ),
        "required": True,
        "status": "verified",
    },
    "dist_git_object_replay": {
        "blocker": None,
        "evidence_path": "host-kernel/rocky/evidence/dist-git-object-replay.json",
        "evidence_sha256": (
            "359ed16070bd3a401fe733a00581499e6784fa2b017c51cbf3da2bbd7fe499de"
        ),
        "required": True,
        "status": "verified",
    },
    "repository_metadata_signature_replay": {
        "blocker": None,
        "evidence_path": (
            "host-kernel/rocky/evidence/repository-metadata-signature-replay.json"
        ),
        "evidence_sha256": (
            "4573f66b43019a6b45907a611d3c52a3af4ac92cdacd0ff3c1ee8a945b270dc5"
        ),
        "required": True,
        "status": "verified",
    },
    "srpm_header_signature": {
        "blocker": None,
        "evidence_path": "host-kernel/rocky/evidence/srpm-header-signature.json",
        "evidence_sha256": (
            "0106cd8d9ae07a9191affa55f35f7d79390e66ca95c1e85034d3434d06a79901"
        ),
        "required": True,
        "signature_algorithm": "RSA/SHA256",
        "signer_fingerprint": "FC226859C0860BF0DDB95B085B106C736FEDFC85",
        "status": "verified",
    },
}


# These are immutable source identities, not defaults.  A platform update must
# change this authority, both JSON manifests, and all mutation tests together.
EXPECTED_SOURCE_IDENTITIES: dict[str, Any] = {
    "schema_version": 1,
    "lock_id": "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1",
    "observed_at": "2026-08-11",
    "target": {
        "architecture": "x86_64",
        "distribution": "Rocky Linux",
        "release": "10.2",
    },
    "source_rpm": {
        "arch": "src",
        "epoch": 0,
        "filename": "kernel-6.12.0-211.44.1.el10_2.src.rpm",
        "name": "kernel",
        "nevra": "kernel-0:6.12.0-211.44.1.el10_2.src",
        "nvr": "kernel-6.12.0-211.44.1.el10_2",
        "release": "211.44.1.el10_2",
        "repository_location": (
            "Packages/k/kernel-6.12.0-211.44.1.el10_2.src.rpm"
        ),
        "sha256": (
            "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb"
        ),
        "size": 159328372,
        "url": (
            "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/source/tree/"
            "Packages/k/kernel-6.12.0-211.44.1.el10_2.src.rpm"
        ),
        "version": "6.12.0",
    },
    "repository_snapshot": {
        "base_url": (
            "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/source/tree/"
        ),
        "primary_metadata": {
            "href": (
                "repodata/1cc64f6d0e798011d1862c2284189742f6383c6fc27c84de207"
                "c739148e50209-primary.xml.gz"
            ),
            "open_sha256": (
                "43c8be01489c52b45ccf8ded2d64b476d883b86aa5b4daf85df2a5ac9abc1ab7"
            ),
            "open_size": 1320895,
            "sha256": (
                "1cc64f6d0e798011d1862c2284189742f6383c6fc27c84de207c739148e50209"
            ),
            "size": 186048,
            "timestamp": 1786434034,
        },
        "release_key": {
            "fingerprint": "FC226859C0860BF0DDB95B085B106C736FEDFC85",
            "key_id": "5B106C736FEDFC85",
            "sha256": (
                "be8c4f070b696e64d8ce40e59a95a57e8b5c776f0015c2fd64e14b896622bdb4"
            ),
            "url": "https://download.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-10",
        },
        "repomd": {
            "revision": "10.2",
            "sha256": (
                "9085b7c0ce3d9ebda8cba25d3daafd13062ce7cd4a10c0036265af80449adea0"
            ),
            "signature": {
                "created_unix": 1786434220,
                "sha256": (
                    "40e16e3d39ddc9ed7fff85201704b0805a37d732291193e6a3143a731001641e"
                ),
                "status": "verified",
                "validsig_fingerprint": "FC226859C0860BF0DDB95B085B106C736FEDFC85",
                "verification_tool": "gpg --verify",
                "url": (
                    "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/"
                    "source/tree/repodata/repomd.xml.asc"
                ),
            },
            "url": (
                "https://download.rockylinux.org/pub/rocky/10.2/BaseOS/source/"
                "tree/repodata/repomd.xml"
            ),
        },
    },
    "dist_git": {
        "branch_context": "r10",
        "branch_is_immutable_identity": False,
        "commit": "e4cad646580f7f3dfec5e3b6b4ea9e89b7572f6c",
        "commit_parent": "ec0da4795eed03a457da5a3fb83a5622ef95839b",
        "content": [
            {
                "path": ".kernel.checksum",
                "sha256": (
                    "f9c6578888639f601e0dbfda887b73d8fcfcba5dbd68e0fef186febaa6959215"
                ),
                "size": 65,
            },
            {
                "path": ".kernel.metadata",
                "sha256": (
                    "65eddbfd4115f7d7143231c5380835accf44f9d7c394709473c5f9948b3a1b50"
                ),
                "size": 356,
            },
            {
                "path": "SPECS/kernel.spec",
                "sha256": (
                    "081eb3b79dbbd240d484c6b72ecc786abf9997f8040b88120165e9b32273fdfe"
                ),
                "size": 1855272,
            },
            {
                "path": "SOURCES/kernel-x86_64-rhel.config",
                "sha256": (
                    "5bbdda60ce822ec903c85d3d8ddda1bfc9493216bed86c6c432683aa50dcf50d"
                ),
                "size": 254653,
            },
        ],
        "repository_url": "https://git.rockylinux.org/staging/rpms/kernel.git",
        "tag": "patched/r10/kernel-6.12.0-211.44.1.el10_2",
        "tag_annotation_original_hash": (
            "2d1667d05d35af0db51fb674095decbc3ea6ca7b752134ff40815b815652616e"
        ),
        "tag_object": "e2eab3dcafd17dcf661d4df2582bcae8188a7550",
    },
    "embedded_objects": [
        {
            "path": (
                "SOURCES/kernel-abi-stablelists-6.12.0-211.44.1.el10_2.tar.xz"
            ),
            "role": "kernel ABI stable-list source object",
            "sha256": (
                "9c753338d255502a040c82be6a39a47b80df15e30fb1d3bc2f13687522c27032"
            ),
            "size": 18168,
        },
        {
            "path": "SOURCES/kernel-kabi-dw-6.12.0-211.44.1.el10_2.tar.xz",
            "role": "kernel ABI DWARF source object",
            "sha256": (
                "7547d50e4f0daeb28eba949801d3d09d0c3c6a8946859759a44d00f786791d4e"
            ),
            "size": 1096,
        },
        {
            "path": "SOURCES/linux-6.12.0-211.44.1.el10_2.tar.xz",
            "role": "Rocky-derived Linux source archive",
            "sha256": (
                "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533"
            ),
            "size": 153374592,
        },
    ],
    "patch_series": {
        "path": "host-kernel/rocky/patches/series.json",
        "sha256": (
            "6a1a5e8fb13b6ce6ed35bd8e5487bb67ecf92d2be927799b660f21b5631f68fb"
        ),
    },
    "acquisition": {
        "allowed_redirect_hosts": ["download.rockylinux.org"],
        "cache_layout_version": 1,
        "cache_relative_path": (
            "rocky/10.2/x86_64/source-rpms/sha256/2b/"
            "2bfeda65bd9bdd4b86650074c81e061c37822b80317ac0d4f5aacc89c85589cb/"
            "kernel-6.12.0-211.44.1.el10_2.src.rpm"
        ),
        "default_cache_root": ".cache/mckernel-kernel-sources",
        "hash_algorithm": "sha256",
        "network_policy": (
            "HTTPS only; reject redirects outside allowed_redirect_hosts; verify "
            "exact byte count and SHA-256 before atomic cache publication"
        ),
    },
}


EXPECTED_SERIES: dict[str, Any] = {
    "dist_git": {
        "commit": "e4cad646580f7f3dfec5e3b6b4ea9e89b7572f6c",
        "tag": "patched/r10/kernel-6.12.0-211.44.1.el10_2",
    },
    "kernel_source_nevra": "kernel-0:6.12.0-211.44.1.el10_2.src",
    "patch_application": {
        "function": "ApplyOptionalPatch",
        "minimum_line_count_to_apply": 10,
        "program": "git --work-tree=. apply",
        "spec_path": "SPECS/kernel.spec",
    },
    "patches": [
        {
            "applied": False,
            "empty": True,
            "line_count": 0,
            "order": 1,
            "path": "SOURCES/patch-6.12-redhat.patch",
            "sha256": (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ),
            "size": 0,
            "spec_reference": "Patch1",
        },
        {
            "applied": False,
            "empty": True,
            "line_count": 0,
            "order": 2,
            "path": "SOURCES/linux-kernel-test.patch",
            "sha256": (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ),
            "size": 0,
            "spec_reference": "Patch999999",
        },
        {
            "applied": True,
            "empty": False,
            "line_count": 27,
            "order": 3,
            "path": "SOURCES/1000-debrand-some-messages.patch",
            "sha256": (
                "080bbc72a543eed6b71daee1b3236b59f3a0f8b3ad20815d962444d3b106b144"
            ),
            "size": 928,
            "spec_reference": "Patch1000000",
        },
    ],
    "schema_version": 1,
    "series_id": (
        "rocky-10.2-kernel-6.12.0-211.44.1.el10_2-patch-series-v1"
    ),
    "source_lock_id": (
        "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1"
    ),
}


class SourceLockError(RuntimeError):
    """Raised when an RK-001 source identity or evidence claim is invalid."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise SourceLockError(f"cannot read {path}: {exc}") from exc
    return size, digest.hexdigest()


def object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise SourceLockError(f"duplicate JSON key: {key}")
        value[key] = child
    return value


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SourceLockError(f"cannot read {path}: {exc}") from exc
    if len(data) > MAX_MANIFEST_BYTES:
        raise SourceLockError(f"manifest is implausibly large: {path}")
    try:
        value = json.loads(data, object_pairs_hook=object_without_duplicates)
    except SourceLockError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceLockError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SourceLockError(f"{path} must contain one JSON object")
    return value, data


def exact_keys(value: object, expected: Iterable[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise SourceLockError(f"{label} must be an object")
    expected_set = set(expected)
    actual_set = set(value)
    if actual_set != expected_set:
        raise SourceLockError(
            f"{label} fields changed: actual={sorted(actual_set)}, "
            f"expected={sorted(expected_set)}"
        )
    return value


def assert_expected_subset(
    actual: object, expected: object, label: str = "source lock"
) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise SourceLockError(f"{label} must be an object")
        for key, expected_value in expected.items():
            if key not in actual:
                raise SourceLockError(f"{label}.{key} is missing")
            assert_expected_subset(actual[key], expected_value, f"{label}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise SourceLockError(f"{label} list identity changed")
        for index, expected_value in enumerate(expected):
            assert_expected_subset(actual[index], expected_value, f"{label}[{index}]")
        return
    if actual != expected or type(actual) is not type(expected):
        raise SourceLockError(
            f"{label} changed: actual={actual!r}, expected={expected!r}"
        )


def validate_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not HEX_SHA256.fullmatch(value):
        raise SourceLockError(f"{label} must be a lowercase SHA-256")
    return value


def validate_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SourceLockError(f"{label} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise SourceLockError(f"{label} is not a normalized relative path: {value!r}")
    return value


def validate_https_url(value: object, hosts: Iterable[str], label: str) -> str:
    if not isinstance(value, str):
        raise SourceLockError(f"{label} must be a URL")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname not in set(hosts)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise SourceLockError(f"{label} is not a permitted HTTPS URL: {value!r}")
    return value


def repository_evidence_path(repo: Path, relative: str, label: str) -> Path:
    root = repo.resolve()
    requested = root.joinpath(*PurePosixPath(relative).parts)
    resolved = requested.resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(resolved))))
    except ValueError as exc:
        raise SourceLockError(f"{label} is on a different filesystem root") from exc
    if common != root:
        raise SourceLockError(f"{label} escapes the repository")
    if requested != resolved or requested.is_symlink() or not requested.is_file():
        raise SourceLockError(
            f"{label} must be a regular repository file with no symlink traversal"
        )
    return requested


def validate_evidence_record(
    evidence_id: str,
    record: object,
    repo: Path | None,
) -> str | None:
    fields = {"blocker", "evidence_path", "evidence_sha256", "required", "status"}
    if evidence_id == "srpm_header_signature":
        fields |= {"signature_algorithm", "signer_fingerprint"}
    item = exact_keys(record, fields, f"evidence.{evidence_id}")
    if item["required"] is not True:
        raise SourceLockError(f"evidence.{evidence_id} must remain required")
    status = item["status"]
    if status not in {"required-missing", "captured-unverified", "verified"}:
        raise SourceLockError(f"evidence.{evidence_id} has invalid status {status!r}")
    if status == "required-missing":
        if not isinstance(item["blocker"], str) or not item["blocker"].strip():
            raise SourceLockError(f"evidence.{evidence_id} needs a blocker")
        for key in ("evidence_path", "evidence_sha256"):
            if item[key] is not None:
                raise SourceLockError(
                    f"evidence.{evidence_id}.{key} must be null while missing"
                )
        if evidence_id == "srpm_header_signature":
            for key in ("signature_algorithm", "signer_fingerprint"):
                if item[key] is not None:
                    raise SourceLockError(
                        f"evidence.{evidence_id}.{key} must be null while missing"
                    )
        return str(item["blocker"])

    path_text = validate_relative_path(
        item["evidence_path"], f"evidence.{evidence_id}.evidence_path"
    )
    expected_digest = validate_sha256(
        item["evidence_sha256"], f"evidence.{evidence_id}.evidence_sha256"
    )
    if repo is None:
        raise SourceLockError(
            f"evidence.{evidence_id} claims capture without a repository to verify it"
        )
    evidence_path = repository_evidence_path(
        repo, path_text, f"evidence.{evidence_id}.evidence_path"
    )
    size, actual_digest = sha256_file(evidence_path)
    if size == 0 or actual_digest != expected_digest:
        raise SourceLockError(f"evidence.{evidence_id} file is absent, empty, or stale")
    if evidence_id == "srpm_header_signature":
        if not isinstance(item["signature_algorithm"], str) or not item[
            "signature_algorithm"
        ].strip():
            raise SourceLockError("SRPM signature algorithm is not captured")
        fingerprint = item["signer_fingerprint"]
        if fingerprint != EXPECTED_SOURCE_IDENTITIES["repository_snapshot"][
            "release_key"
        ]["fingerprint"]:
            raise SourceLockError("SRPM signer is not the pinned Rocky Linux 10 key")
    if status != "verified":
        if not isinstance(item["blocker"], str) or not item["blocker"].strip():
            raise SourceLockError(
                f"unverified evidence.{evidence_id} needs a non-empty blocker"
            )
        return str(item["blocker"])
    if item["blocker"] is not None:
        raise SourceLockError(
            f"verified evidence.{evidence_id} must clear its blocker"
        )
    if item != EXPECTED_REVIEWED_EVIDENCE[evidence_id]:
        raise SourceLockError(
            f"verified evidence.{evidence_id} differs from the reviewed record"
        )
    return None


def validate_source_evidence_review(
    lock: Mapping[str, Any],
    series: Mapping[str, Any],
    repo: Path | None,
) -> None:
    if repo is None:
        raise SourceLockError("verified source evidence needs a repository review")
    review_path = repository_evidence_path(
        repo,
        SOURCE_EVIDENCE_REVIEW_PATH.as_posix(),
        "source evidence review manifest",
    )
    size, digest = sha256_file(review_path)
    if size == 0 or digest != SOURCE_EVIDENCE_REVIEW_SHA256:
        raise SourceLockError("source evidence review manifest is absent or stale")
    try:
        source_review.check(
            str(repo.resolve()),
            lock_override=lock,
            series_override=series,
        )
    except source_review.ReviewError as exc:
        raise SourceLockError(f"source evidence semantic review failed: {exc}") from exc


def validate_license_decision(
    decision: object,
    inventory: Mapping[str, Any],
    repo: Path | None,
) -> str | None:
    item = exact_keys(
        decision,
        {
            "authority_registration",
            "blocker",
            "decision_path",
            "decision_sha256",
            "required",
            "status",
        },
        "licenses.decision",
    )
    if item["required"] is not True:
        raise SourceLockError("license decision must remain required")
    if item["authority_registration"] != EXPECTED_LICENSE_DECISION_REGISTRATION:
        raise SourceLockError("license decision authority registration policy changed")
    if item["status"] == "required-missing":
        if not isinstance(item["blocker"], str) or not item["blocker"].strip():
            raise SourceLockError("missing license decision needs a blocker")
        for key in ("decision_path", "decision_sha256"):
            if item[key] is not None:
                raise SourceLockError(
                    f"licenses.decision.{key} must be null while missing"
                )
        return str(item["blocker"])
    if item["status"] != "verified":
        raise SourceLockError("license decision status must be missing or verified")
    if item["blocker"] is not None:
        raise SourceLockError("verified license decision must clear its blocker")
    if (
        EXPECTED_LICENSE_DECISION_SHA256 is None
        or EXPECTED_LICENSE_REVIEW_AUTHORITY_ID is None
    ):
        raise SourceLockError(
            "no independently reviewed license decision authority is registered"
        )
    if item["decision_path"] != LICENSE_DECISION_PATH:
        raise SourceLockError("license decision path differs from its reviewed location")
    digest = validate_sha256(
        item["decision_sha256"], "licenses.decision.decision_sha256"
    )
    if digest != EXPECTED_LICENSE_DECISION_SHA256:
        raise SourceLockError("license decision digest is not independently registered")
    if repo is None:
        raise SourceLockError("verified license decision needs a repository")
    decision_path = repository_evidence_path(
        repo, LICENSE_DECISION_PATH, "licenses.decision.decision_path"
    )
    value, payload = read_json(decision_path)
    if sha256_bytes(payload) != digest:
        raise SourceLockError("license decision file is absent or stale")
    manifest = exact_keys(
        value,
        {"decision_id", "inventory", "result", "review", "schema_version"},
        "license decision manifest",
    )
    if manifest["schema_version"] != 1 or manifest["decision_id"] != LICENSE_DECISION_ID:
        raise SourceLockError("license decision identity changed")
    reviewed_inventory = exact_keys(
        manifest["inventory"],
        {"item_count", "path", "sha256"},
        "license decision inventory",
    )
    if reviewed_inventory != {
        "item_count": inventory["item_count"],
        "path": inventory["inventory_path"],
        "sha256": inventory["inventory_sha256"],
    }:
        raise SourceLockError("license decision reviews a different inventory")
    review = exact_keys(
        manifest["review"],
        {"authority_id", "independent_from_capture"},
        "license decision review",
    )
    if (
        review["authority_id"] != EXPECTED_LICENSE_REVIEW_AUTHORITY_ID
        or review["independent_from_capture"] is not True
    ):
        raise SourceLockError("license decision lacks the registered independent authority")
    result = exact_keys(
        manifest["result"],
        {
            "all_items_reviewed",
            "credit_eligible",
            "review_status",
            "unresolved_count",
        },
        "license decision result",
    )
    if result != {
        "all_items_reviewed": True,
        "credit_eligible": True,
        "review_status": "independently-reviewed",
        "unresolved_count": 0,
    }:
        raise SourceLockError("license decision does not close every review blocker")
    return None


def validate_license_policy(lock: Mapping[str, Any], repo: Path | None) -> str | None:
    licenses = exact_keys(
        lock.get("licenses"),
        {
            "capture_authority",
            "decision",
            "declared_spdx_expression",
            "inventory",
            "policy",
            "spec_path",
        },
        "licenses",
    )
    if licenses["capture_authority"] != EXPECTED_LICENSE_CAPTURE_AUTHORITY:
        raise SourceLockError("license capture source-closure authority changed")
    expression = licenses["declared_spdx_expression"]
    if not isinstance(expression, str) or sha256_bytes(expression.encode()) != (
        LICENSE_EXPRESSION_SHA256
    ):
        raise SourceLockError("the exact kernel.spec License expression changed")
    if licenses["spec_path"] != "SPECS/kernel.spec":
        raise SourceLockError("licenses.spec_path changed")

    policy = exact_keys(
        licenses["policy"],
        {
            "fail_on_missing_or_ambiguous_license",
            "license_texts_required",
            "patch_authorship_and_license_required",
            "required_fields_per_item",
            "scope",
            "unreviewed_items_forbid_gate_credit",
        },
        "licenses.policy",
    )
    for flag in (
        "fail_on_missing_or_ambiguous_license",
        "license_texts_required",
        "patch_authorship_and_license_required",
        "unreviewed_items_forbid_gate_credit",
    ):
        if policy[flag] is not True:
            raise SourceLockError(f"licenses.policy.{flag} must remain true")
    required_fields = policy["required_fields_per_item"]
    if required_fields != EXPECTED_LICENSE_ITEM_FIELDS:
        raise SourceLockError("license inventory fields are incomplete or reordered")
    scope = policy["scope"]
    if not isinstance(scope, list) or len(scope) != 4:
        raise SourceLockError("license inventory scope must cover exactly four classes")
    scope_text = "\n".join(str(item).lower() for item in scope)
    for phrase in ("linux source archive", "dist-git", "patch", "license text"):
        if phrase not in scope_text:
            raise SourceLockError(f"license inventory scope does not cover {phrase}")

    inventory = exact_keys(
        licenses["inventory"],
        {
            "blocker",
            "complete",
            "inventory_path",
            "inventory_sha256",
            "item_count",
            "required",
            "status",
        },
        "licenses.inventory",
    )
    if inventory["required"] is not True:
        raise SourceLockError("license inventory must remain required")
    status = inventory["status"]
    inventory_blocker: str | None = None
    if status == "required-missing":
        if inventory["complete"] is not False:
            raise SourceLockError("missing license inventory cannot be complete")
        for key in ("inventory_path", "inventory_sha256", "item_count"):
            if inventory[key] is not None:
                raise SourceLockError(f"licenses.inventory.{key} must be null while missing")
        blocker = inventory["blocker"]
        if not isinstance(blocker, str) or not blocker.strip():
            raise SourceLockError("missing license inventory needs a blocker")
        inventory_blocker = str(blocker)
    else:
        if status != "verified" or inventory["complete"] is not True:
            raise SourceLockError(
                "license inventory status must be missing or verified-complete"
            )
        if inventory["blocker"] is not None:
            raise SourceLockError("verified license inventory must clear its blocker")
        path_text = validate_relative_path(
            inventory["inventory_path"], "licenses.inventory.inventory_path"
        )
        expected_digest = validate_sha256(
            inventory["inventory_sha256"], "licenses.inventory.inventory_sha256"
        )
        if inventory["item_count"] != EXPECTED_LICENSE_INVENTORY_ITEM_COUNT:
            raise SourceLockError(
                "verified license inventory item_count differs from source closure"
            )
        if repo is None:
            raise SourceLockError("verified license inventory needs a repository to verify it")
        inventory_path = repository_evidence_path(
            repo, path_text, "licenses.inventory.inventory_path"
        )
        size, actual_digest = sha256_file(inventory_path)
        if size == 0 or actual_digest != expected_digest:
            raise SourceLockError("license inventory file is absent, empty, or stale")
    decision_blocker = validate_license_decision(licenses["decision"], inventory, repo)
    blockers = [item for item in (inventory_blocker, decision_blocker) if item]
    return "; ".join(blockers) if blockers else None


def validate_source_lock(
    lock: dict[str, Any], series: dict[str, Any], repo: Path | None = None
) -> list[str]:
    exact_keys(
        lock,
        {
            "acquisition",
            "dist_git",
            "embedded_objects",
            "evidence",
            "gate",
            "licenses",
            "lock_id",
            "observed_at",
            "patch_series",
            "repository_snapshot",
            "schema_version",
            "source_rpm",
            "target",
        },
        "source lock",
    )
    assert_expected_subset(lock, EXPECTED_SOURCE_IDENTITIES)
    validate_series(series)

    source = lock["source_rpm"]
    repository = lock["repository_snapshot"]
    if source["url"] != repository["base_url"] + source["repository_location"]:
        raise SourceLockError("SRPM URL is not derived from its pinned repository location")
    signature = repository["repomd"]["signature"]
    release_key = repository["release_key"]
    if signature["status"] != "verified":
        raise SourceLockError("repomd signature must be verified, never assumed")
    if signature["validsig_fingerprint"] != release_key["fingerprint"]:
        raise SourceLockError("repomd signature does not match the pinned release key")

    allowed_download_hosts = lock["acquisition"]["allowed_redirect_hosts"]
    if allowed_download_hosts != ["download.rockylinux.org"]:
        raise SourceLockError("download host allowlist changed")
    for label, url, hosts in (
        ("source_rpm.url", source["url"], allowed_download_hosts),
        ("repository_snapshot.base_url", repository["base_url"], allowed_download_hosts),
        ("repository_snapshot.repomd.url", repository["repomd"]["url"], allowed_download_hosts),
        (
            "repository_snapshot.repomd.signature.url",
            signature["url"],
            allowed_download_hosts,
        ),
        ("repository_snapshot.release_key.url", release_key["url"], allowed_download_hosts),
        ("dist_git.repository_url", lock["dist_git"]["repository_url"], ["git.rockylinux.org"]),
    ):
        validate_https_url(url, hosts, label)
    validate_relative_path(
        lock["acquisition"]["cache_relative_path"],
        "acquisition.cache_relative_path",
    )

    if source["nevra"] != series["kernel_source_nevra"]:
        raise SourceLockError("patch series names a different source NEVRA")
    if lock["lock_id"] != series["source_lock_id"]:
        raise SourceLockError("patch series links to a different source lock")
    if lock["dist_git"]["commit"] != series["dist_git"]["commit"]:
        raise SourceLockError("patch series links to a different dist-git commit")
    if lock["dist_git"]["tag"] != series["dist_git"]["tag"]:
        raise SourceLockError("patch series links to a different dist-git tag")

    evidence = exact_keys(
        lock["evidence"],
        {
            "acquisition_replay",
            "dist_git_object_replay",
            "repository_metadata_signature_replay",
            "srpm_header_signature",
        },
        "evidence",
    )
    blockers: list[str] = []
    evidence_blockers: list[str] = []
    for evidence_id in sorted(evidence):
        blocker = validate_evidence_record(evidence_id, evidence[evidence_id], repo)
        if blocker:
            evidence_blockers.append(f"{evidence_id}: {blocker}")
    blockers.extend(evidence_blockers)
    if not evidence_blockers:
        validate_source_evidence_review(lock, series, repo)
    license_blocker = validate_license_policy(lock, repo)
    if license_blocker:
        blockers.append(f"license_inventory: {license_blocker}")

    gate = exact_keys(lock["gate"], {"credit_eligible", "gate_id", "policy"}, "gate")
    if gate["gate_id"] != "RK-001":
        raise SourceLockError("source lock is bound to the wrong gate")
    if not isinstance(gate["policy"], str) or "forbidden" not in gate["policy"].lower():
        raise SourceLockError("gate policy does not fail closed")
    calculated_credit = not blockers
    if gate["credit_eligible"] is not calculated_credit:
        raise SourceLockError(
            "gate.credit_eligible contradicts the required evidence state"
        )
    return blockers


def validate_series(series: dict[str, Any]) -> None:
    if series != EXPECTED_SERIES:
        assert_expected_subset(series, EXPECTED_SERIES, "patch series")
        extra = set(series) - set(EXPECTED_SERIES)
        if extra:
            raise SourceLockError(f"patch series has unexpected fields: {sorted(extra)}")
        raise SourceLockError("patch series identity changed")
    orders = [item["order"] for item in series["patches"]]
    if orders != list(range(1, len(series["patches"]) + 1)):
        raise SourceLockError("patch order must be contiguous and one-based")
    threshold = series["patch_application"]["minimum_line_count_to_apply"]
    for item in series["patches"]:
        expected_applied = item["line_count"] >= threshold
        if item["applied"] is not expected_applied:
            raise SourceLockError(f"patch application result is stale for {item['path']}")
        if item["empty"] is not (item["size"] == 0 and item["line_count"] == 0):
            raise SourceLockError(f"empty-patch classification is stale for {item['path']}")


def validate_loaded_manifests(
    lock: dict[str, Any],
    series: dict[str, Any],
    series_bytes: bytes,
    repo: Path | None,
) -> list[str]:
    blockers = validate_source_lock(lock, series, repo)
    expected_digest = lock["patch_series"]["sha256"]
    if sha256_bytes(series_bytes) != expected_digest:
        raise SourceLockError("patch-series file bytes do not match source-lock SHA-256")
    return blockers


def load_manifests(
    repo: Path,
    lock_path: Path = SOURCE_LOCK_PATH,
    series_path: Path = PATCH_SERIES_PATH,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    lock_file = lock_path if lock_path.is_absolute() else repo / lock_path
    series_file = series_path if series_path.is_absolute() else repo / series_path
    lock, _ = read_json(lock_file)
    series, series_bytes = read_json(series_file)
    blockers = validate_loaded_manifests(lock, series, series_bytes, repo)
    return lock, series, blockers


def artifact_cache_path(cache_root: Path, lock: Mapping[str, Any]) -> Path:
    relative = validate_relative_path(
        lock["acquisition"]["cache_relative_path"],
        "acquisition.cache_relative_path",
    )
    root = cache_root.resolve()
    target = root.joinpath(*PurePosixPath(relative).parts).resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(target))))
    except ValueError as exc:
        raise SourceLockError("cache path is on a different filesystem root") from exc
    if common != root:
        raise SourceLockError("cache path escapes the selected cache root")
    return target


def verify_artifact(path: Path, expected_size: int, expected_sha256: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise SourceLockError(f"cached artifact is not a regular non-symlink file: {path}")
    size, digest = sha256_file(path)
    if size != expected_size:
        raise SourceLockError(
            f"artifact size mismatch for {path}: actual={size}, expected={expected_size}"
        )
    if digest != expected_sha256:
        raise SourceLockError(
            f"artifact SHA-256 mismatch for {path}: actual={digest}, "
            f"expected={expected_sha256}"
        )


class PinnedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that leave the manifest's HTTPS host allowlist."""

    def __init__(self, allowed_hosts: Iterable[str]):
        super().__init__()
        self.allowed_hosts = frozenset(allowed_hosts)

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: BinaryIO,
        code: int,
        message: str,
        headers: Mapping[str, str],
        new_url: str,
    ) -> urllib.request.Request | None:
        validate_https_url(new_url, self.allowed_hosts, "redirect URL")
        return super().redirect_request(
            request, file_pointer, code, message, headers, new_url
        )


def stream_verified_download(
    response: BinaryIO,
    target: Path,
    expected_size: int,
    expected_sha256: str,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    digest = hashlib.sha256()
    size = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{target.name}.", dir=target.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                if not isinstance(chunk, bytes):
                    raise SourceLockError("download stream returned non-byte data")
                size += len(chunk)
                if size > expected_size:
                    raise SourceLockError("download exceeded the locked byte count")
                digest.update(chunk)
                temporary.write(chunk)
            temporary.flush()
            os.fsync(temporary.fileno())
        if size != expected_size:
            raise SourceLockError(
                f"download byte count mismatch: actual={size}, expected={expected_size}"
            )
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise SourceLockError(
                f"download SHA-256 mismatch: actual={actual_sha256}, "
                f"expected={expected_sha256}"
            )
        assert temporary_name is not None
        os.chmod(temporary_name, 0o444)
        os.replace(temporary_name, target)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def acquire_source(
    lock: Mapping[str, Any], cache_root: Path, timeout: float = 60.0
) -> Path:
    source = lock["source_rpm"]
    allowed_hosts = lock["acquisition"]["allowed_redirect_hosts"]
    url = validate_https_url(source["url"], allowed_hosts, "source_rpm.url")
    target = artifact_cache_path(cache_root, lock)
    if target.exists() or target.is_symlink():
        verify_artifact(target, source["size"], source["sha256"])
        return target
    opener = urllib.request.build_opener(PinnedRedirectHandler(allowed_hosts))
    request = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "mckernel-rk-001-source-lock/1",
        },
        method="GET",
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            validate_https_url(final_url, allowed_hosts, "final download URL")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    parsed_length = int(content_length)
                except ValueError as exc:
                    raise SourceLockError("download Content-Length is not an integer") from exc
                if parsed_length != source["size"]:
                    raise SourceLockError(
                        "download Content-Length does not match the source lock"
                    )
            stream_verified_download(
                response, target, source["size"], source["sha256"]
            )
    except (OSError, urllib.error.URLError) as exc:
        raise SourceLockError(f"source acquisition failed: {exc}") from exc
    verify_artifact(target, source["size"], source["sha256"])
    return target


def run_git(repo: Path, arguments: Sequence[str]) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", b"").decode(errors="replace").strip()
        raise SourceLockError(
            f"git {' '.join(arguments)} failed in {repo}: {stderr}"
        ) from exc
    return completed.stdout


def verify_dist_git(
    dist_git: Path, lock: Mapping[str, Any], series: Mapping[str, Any]
) -> None:
    identity = lock["dist_git"]
    if not (dist_git / ".git").exists():
        raise SourceLockError(f"not a Git worktree: {dist_git}")
    tag = identity["tag"]
    tag_object = run_git(dist_git, ["rev-parse", tag]).decode().strip()
    peeled = run_git(dist_git, ["rev-parse", f"{tag}^{{}}"]).decode().strip()
    parent = run_git(dist_git, ["rev-parse", f"{identity['commit']}^"]).decode().strip()
    if tag_object != identity["tag_object"] or not HEX_SHA1.fullmatch(tag_object):
        raise SourceLockError("dist-git annotated-tag object changed")
    if peeled != identity["commit"] or parent != identity["commit_parent"]:
        raise SourceLockError("dist-git tag peel or commit parent changed")
    tag_bytes = run_git(dist_git, ["cat-file", "-p", tag])
    if identity["tag_annotation_original_hash"].encode() not in tag_bytes:
        raise SourceLockError("dist-git tag annotation lost its original import hash")

    objects = list(identity["content"]) + list(series["patches"])
    for item in objects:
        path = item["path"]
        data = run_git(dist_git, ["show", f"{identity['commit']}:{path}"])
        if len(data) != item["size"] or sha256_bytes(data) != item["sha256"]:
            raise SourceLockError(f"dist-git object changed: {path}")
        if "line_count" in item and data.count(b"\n") != item["line_count"]:
            raise SourceLockError(f"dist-git patch line count changed: {path}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--lock", type=Path, default=SOURCE_LOCK_PATH)
    parser.add_argument("--series", type=Path, default=PATCH_SERIES_PATH)
    parser.add_argument("--cache-root", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--gate-ready", action="store_true")
    modes.add_argument("--verify-cache", action="store_true")
    modes.add_argument("--acquire", action="store_true")
    modes.add_argument("--verify-dist-git", type=Path)
    return parser.parse_args(argv)


def print_blockers(blockers: Sequence[str], stream: Any = sys.stdout) -> None:
    print(f"RK-001 NOT READY: {len(blockers)} required evidence item(s) incomplete", file=stream)
    for blocker in blockers:
        print(f"- {blocker}", file=stream)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    try:
        lock, series, blockers = load_manifests(repo, args.lock, args.series)
        if args.check:
            print(
                "Rocky kernel source lock verified: "
                f"{lock['source_rpm']['nevra']} sha256={lock['source_rpm']['sha256']}"
            )
            if blockers:
                print_blockers(blockers)
            else:
                print("RK-001 READY: all required evidence verified")
            return 0
        if args.gate_ready:
            if blockers:
                print_blockers(blockers, sys.stderr)
                return 1
            print("RK-001 READY: all required evidence verified")
            return 0

        cache_root = args.cache_root
        if cache_root is None:
            cache_root = repo / lock["acquisition"]["default_cache_root"]
        if args.verify_cache:
            target = artifact_cache_path(cache_root, lock)
            verify_artifact(
                target, lock["source_rpm"]["size"], lock["source_rpm"]["sha256"]
            )
            print(f"verified cached SRPM: {target}")
            return 0
        if args.acquire:
            target = acquire_source(lock, cache_root)
            print(f"acquired locked SRPM: {target}")
            if blockers:
                print_blockers(blockers)
            return 0
        if args.verify_dist_git is not None:
            verify_dist_git(args.verify_dist_git.resolve(), lock, series)
            print(
                "verified Rocky dist-git tag, commit, content, and patch series: "
                f"{lock['dist_git']['commit']}"
            )
            return 0
        raise SourceLockError("no mode selected")
    except SourceLockError as exc:
        print(f"Rocky kernel source-lock error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
