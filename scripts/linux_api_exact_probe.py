#!/usr/bin/env python3
"""Capture and verify exact Rocky Linux API evidence for RS-001.

The frozen API-needs manifest is an R0 inventory, not a Rocky 10.2 claim.  This
tool adds a separate, immutable evidence layer tied to the checksum-locked
Rocky source RPM, source archive, patched source tree, selected configuration,
kernel build outputs, generated Rust bindings, and tool binaries.

The tool never awards RS-001 credit.  Even a technically complete capture is
marked review-required and credit-ineligible; missing exact inputs or reviewed
maps keep technical readiness false.
"""

from __future__ import print_function

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


SCHEMA_VERSION = 1
CONTRACT_ID = "mckernel-rs001-exact-linux-api-probe-v1"
EVIDENCE_PROFILE = "rocky-10.2-exact-linux-api-evidence-v1"
EXPECTED_NEED_COUNT = 268
EXPECTED_MODULES = ("ihk", "ihk_smp_x86_64", "mcctrl")
NEEDS_PATH = Path("host-kernel/contracts/linux-api-needs-v1.json")
CONTRACT_PATH = Path("host-kernel/contracts/linux-api-exact-probe-v1.json")
SOURCE_LOCK_PATH = Path("host-kernel/rocky/source-lock.json")
PATCH_SERIES_PATH = Path("host-kernel/rocky/patches/series.json")
RUST_COMPAT_PATCH_PATHS = (
    Path("host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch"),
    Path("host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch"),
    Path("host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch"),
    Path("host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch"),
    Path("host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch"),
    Path("host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch"),
    Path("host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch"),
    Path("host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch"),
    Path("host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch"),
    Path("host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch"),
    Path("host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch"),
    Path("host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch"),
    Path("host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch"),
    Path("host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch"),
    Path("host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch"),
    Path("host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch"),
    Path("host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch"),
    Path("host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch"),
    Path("host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch"),
    Path("host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch"),
    Path("host-kernel/rocky/patches/0020a-rust-miscdevice-bind-file-operations-to-module.patch"),
    Path("host-kernel/rocky/patches/0021-objtool-recognize-rust-1.92-panic-const.patch"),
    Path("host-kernel/rocky/patches/0022-x86-pvh-annotate-noendbr.patch"),
    Path("host-kernel/rocky/patches/0023-rust-update-no-alloc-shim-marker-rust-1.92.patch"),
)
MISCDEVICE_OWNER_LOCAL_ORIGIN = (
    "McKernel RS-006 miscdevice module-owner compatibility"
)
MISCDEVICE_OWNER_ROCKY_BASE = "linux-6.12.0-211.44.1.el10_2"
MISCDEVICE_OWNER_LICENSE = "GPL-2.0"
MISCDEVICE_OWNER_INTEGRATION_STATUS = "active-ordered-unbuilt"
CONFIG_POLICY_PATH = Path("host-kernel/rocky/config-policy.json")
TOOLCHAIN_LOCK_PATH = Path("host-kernel/rocky/toolchain-lock.json")
WORKFLOW_PATH = Path(".github/workflows/rs001-linux-api-exact-probe.yml")
SCRIPT_PATH = Path("scripts/linux_api_exact_probe.py")
RUST_COMPAT_FIXTURE_PATH = Path(
    "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs"
)
RUST_COMPAT_FIXTURE_SHA256 = (
    "9c21a1b67751db98e407439b77d014be6b92ba3cf6457fde6a4118a798f4fa05"
)
RUST_COMPAT_POSTIMAGE_SHA256 = (
    "555ff4dff6548bb5f24087cdad737363b5694668aa462f77adfb3571498ec678"
)
RUST_CORE_COMPAT_FIXTURE_ROOT = Path(
    "scripts/tests/fixtures/rust-core-rocky-6.12"
)
RUST_CORE_COMPAT_PREIMAGE_SHA256S = (
    ("Documentation/kbuild/makefiles.rst", "e6625c8e3b13b8b41b7cbb6c70541025ca3f417421cf57ad959d5ff7d9944070"),
    ("arch/arm64/Makefile", "f184c381ccc6f72332d0409fb5c329ea2a8e807ae3ad797ffe7f4d00adea7cc0"),
    ("rust/Makefile", "65c896300a77852631c339e2d0cb49b72de44b4dfc854320a7d09b16c68adaff"),
    ("scripts/Makefile.compiler", "290feec444dab068b257cbc1456cb3cec8d0c1840da7c46067a01202ad5a8105"),
    ("scripts/generate_rust_analyzer.py", "26c0b246dbdeee5c1bcb787744b0b7e781e422b5c9ddebba7e9a7ee629aec58f"),
)
RUST_CORE_COMPAT_POSTIMAGE_SHA256S = (
    ("Documentation/kbuild/makefiles.rst", "180f5f93323cb8658f885e2c1233ae6ff1a8a04c393dcf01abe5b586bf26373e"),
    ("arch/arm64/Makefile", "27d44d2ca4dbd92f3e2577b3dec171a79e5147698eb8e69710932252fb129122"),
    ("rust/Makefile", "ea5a2f26d7a8ec607c35b568dff02c7cde712d7ff356e0edcc759a8ac79376e9"),
    ("scripts/Makefile.compiler", "d5b48a68e9b00c6fe240805ccdf52105ac4655fb3ae0eff8c2c0815806766378"),
    ("scripts/generate_rust_analyzer.py", "470ca4bf6e5a35d4b193ef46c3130b051921f2a18fa33891c17f482f9a3e80ca"),
)
RUST_BINDINGS_COMPAT_PREIMAGE_SHA256S = (
    ("init/Kconfig", "35cfd4cc4e8850302a072b9d8aef35d827883f6e30f4ff2d428d12eb622fa749"),
    ("rust/bindings/lib.rs", "19e4c18d9999bd6871d5ea01decb37956c96a7dbf3064578e96130f539405524"),
    ("rust/uapi/lib.rs", "bdfbafb3df88795d587d42a00ca1a574b31b8668721c645c87eff3ecf318fef8"),
)
RUST_BINDINGS_COMPAT_POSTIMAGE_SHA256S = (
    ("init/Kconfig", "629abc3bdd5105cc843a2a1835819d69e43ead874b8ee9867d3384741641391d"),
    ("rust/bindings/lib.rs", "6729d72292b3003c37f8f68a81c2496bc2d53b2441d2df6502c86a0a99f5a4cd"),
    ("rust/uapi/lib.rs", "0b4ba3250770fd0aa8aaeeb73fdaa76dab8b323cc88750ec82046d9f39859bd0"),
)
RUST_1_89_COMPAT_PREIMAGE_SHA256S = (
    ("rust/Makefile", "65c896300a77852631c339e2d0cb49b72de44b4dfc854320a7d09b16c68adaff"),
    ("rust/kernel/init/macros.rs", "5f7171499edf31631d6aa25df850a81f902c2473fe94d3d6a75137b926e2c336"),
    ("rust/kernel/lib.rs", "730fce907dbd8c48439f63f506d9400ceb707282846f1e325822c77dc99a56f0"),
    ("rust/macros/module.rs", "5fbe26a038e97bdd04e629195e405987f61132d688f4fe808742d02a6bce223f"),
    ("scripts/Makefile.build", "cc30dcf2a77a0a66c748baaadd54c3733af67e904feceb92891f9f31c45409e3"),
)
RUST_1_89_COMPAT_POSTIMAGE_SHA256S = (
    ("rust/Makefile", "ea5a2f26d7a8ec607c35b568dff02c7cde712d7ff356e0edcc759a8ac79376e9"),
    ("rust/kernel/init/macros.rs", "62e0f3cf9fffdf5679ff65c2399116820ef5994df61a1cbb264500302f51f963"),
    ("rust/kernel/lib.rs", "72ff1b9f40f61a519e050d5e77919e1e099f399de0610997b515117e75485202"),
    ("rust/macros/module.rs", "974f7353529834258579b358deb04d4af595e3440d082068cacb9e1796dde5ff"),
    ("scripts/Makefile.build", "bf07905579ac0b533fdfe4caedbff96875244d24af1b62c22fd287d7f9b41b04"),
)
RUST_1_92_RECONCILIATION_PREIMAGE_SHA256S = (
    ("include/linux/blk-mq.h", "336277799bcff072562b6e01b632d2c5136092bf62d37011452794350871d5ba"),
    ("rust/kernel/block/mq/tag_set.rs", "f811f6d04fec48a695495b38083c7729cdd574696310f1e53072e1f793fe1fa3"),
    ("rust/kernel/lib.rs", "730fce907dbd8c48439f63f506d9400ceb707282846f1e325822c77dc99a56f0"),
    ("rust/kernel/list/arc.rs", "69c4d3226b174ed5a183e501a82423d655dd5f54d2664be11fcae1297bec2e1f"),
    ("rust/kernel/sync/arc.rs", "3f3a8b0d560dcf5a1c965fbe677ca759a43e4fae405d0cec63196577672d51f9"),
    ("scripts/Makefile.build", "cc30dcf2a77a0a66c748baaadd54c3733af67e904feceb92891f9f31c45409e3"),
)
RUST_1_92_RECONCILIATION_POSTIMAGE_SHA256S = (
    ("include/linux/blk-mq.h", "336277799bcff072562b6e01b632d2c5136092bf62d37011452794350871d5ba"),
    ("rust/kernel/block/mq/tag_set.rs", "b7a4acbd77165513ba8ffa7d65cc9296a81ab66b4ddd77ef67a927b14b456e6d"),
    ("rust/kernel/lib.rs", "7e4ab7eda6ffea5c0309dfcbac7ab91c7ea3107d2c706bb7e07d41687fbd9fd9"),
    ("rust/kernel/list/arc.rs", "6bfd5e6d5732819f4097ef5e8917f1031a393d70350848fdf91bb5b1a9458866"),
    ("rust/kernel/sync/arc.rs", "d18fccfcbe7a55297dfd4574218c9e6aeeaf8d30f99b0128071f0f444768d8ae"),
    ("scripts/Makefile.build", "9a4d2a34fb5db30c43db86f14474a9b3135bd877ad2850aedb437d0c7606f9df"),
)
RUST_MISCDEVICE_PREIMAGE_SHA256S = (
    ("rust/kernel/types.rs", "3fe4d0cc0910560abefbd668afdb7aad90629b90079ad5e09a6b4346203f9413"),
    ("rust/bindings/bindings_helper.h", "e7590a0468bb99dbf3f32dc5a3d40d2f5f35b4ac50803e9f755825a856ad518c"),
)
RUST_MISCDEVICE_POSTIMAGE_SHA256S = (
    ("rust/kernel/types.rs", "3fde339b8a41b521407faa9e45d51ce9ecb183a170e9c650a72d25c73d50f6f7"),
    ("rust/kernel/lib.rs", "12079556f6e69f48db7fc887227e9243f9fc6837715afb5eaddf57bab8850cdd"),
    ("rust/bindings/bindings_helper.h", "f2644392ca91a791e4ab2ffb05a9b30a911a51f1ae025c696c710cfb3a447d07"),
    ("rust/kernel/miscdevice.rs", "0f2c43a6a64688b6b8387de4813a76289a66f67a1787893d747273c36983b8ee"),
)
RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S = (
    ("tools/objtool/check.c", "71b836ba23a062554bc3038e8e8c7f940bfb38d05dec8d063ef87b70901d4f2e"),
)
RUST_OBJTOOL_NORETURN_POSTIMAGE_SHA256S = (
    ("tools/objtool/check.c", "2c8d113bcbf65bc0de8ad360f70bc707a0379baa925da01cebf0e95f23ce28e7"),
)
PVH_OBJTOOL_COMPAT_PREIMAGE_SHA256S = (
    ("arch/x86/platform/pvh/head.S", "37bb547fa36816be42d4376a342485074eab76aac92e3c5975613420f2670ff1"),
)
PVH_OBJTOOL_COMPAT_POSTIMAGE_SHA256S = (
    ("arch/x86/platform/pvh/head.S", "d7e13bfa0c80d152af07799d6fce8beabc7bfd17cdf8d37cde2ac754bba51da4"),
)
RUST_ALLOC_SHIM_V2_FIXTURE_PREIMAGE_SHA256S = (
    ("rust/kernel/alloc/allocator.rs", "15ce17c9dba35266ff57c1da606f98f2fa4ccb0048fea7d196cce22a4febdc3f"),
)
RUST_ALLOC_SHIM_V2_PREIMAGES = (
    {
        "path": "rust/kernel/alloc/allocator.rs",
        "sha256": "15ce17c9dba35266ff57c1da606f98f2fa4ccb0048fea7d196cce22a4febdc3f",
        "size": 3079,
    },
    {
        "path": "rust/kernel/lib.rs",
        "sha256": "12079556f6e69f48db7fc887227e9243f9fc6837715afb5eaddf57bab8850cdd",
        "size": 4142,
    },
)
RUST_ALLOC_SHIM_V2_POSTIMAGES = (
    {
        "path": "rust/kernel/alloc/allocator.rs",
        "sha256": "5eadd2f8bfd94c5f5636d674afdc7fa93de4f49ad09c199ab687235418010e3f",
        "size": 3146,
    },
    {
        "path": "rust/kernel/lib.rs",
        "sha256": "cde3e1e9608006f36c3a44ee11be848d8481c665f75b6d29937c9e9d9f76b0b6",
        "size": 4196,
    },
)
CLANG_21_WARNING_PREIMAGE_SHA256S = (
    ("Makefile", "b2d9e6f03fa466db088337572dec4b0f98db8f5775ca537bce0a179a1ac216bd"),
    ("arch/loongarch/kernel/Makefile", "0f1aeabed014f3e16ab67cc0b9dfc7c72eb726b6439d95562ba08264fba19a9b"),
    ("arch/loongarch/kvm/Makefile", "af128de8bcbb08f5864ae2337c99ffd1897552377618653ad85ff45c89260ff9"),
    ("arch/riscv/kernel/Makefile", "7a41a7b2abe85a8ab1631c65ad5a9e6dc43f13a83cd6e9fc47514a34ef4612f8"),
    ("scripts/Makefile.extrawarn", "f8b158270273a1ce7054847b0e63051756fbfc5ad83f244d908229861300502b"),
)
CLANG_21_WARNING_POSTIMAGE_SHA256S = (
    ("Makefile", "96d61309de7b5a043f53f8203c05ea30c27808fc7db06b3503d98105f4fde6f6"),
    ("arch/loongarch/kernel/Makefile", "029acf9d4dbff4a807595c9b3ee9e114e53e05c3d724d8db487d1da7c79a8021"),
    ("arch/loongarch/kvm/Makefile", "f497d63c91d5e7b86f2f3b47058fa8dab3866a5903138ea566acfa83df6bb2a3"),
    ("arch/riscv/kernel/Makefile", "b50f087e3bce61fd0541c0122e8ef997c3a3f3b64c8f2464f19a54e862d4b93c"),
    ("scripts/Makefile.extrawarn", "c027f8dc67f2a00011f651517003b312c430d5411bf7783d766ed31a7b64ac02"),
)
CLANG_21_SOURCE_FIX_PREIMAGE_SHA256S = (
    ("mm/ksm.c", "9747f8b5edcc4cf75333bc24e393658c59b8f86fb58a8588ec28bed51f6e626b"),
    ("fs/netfs/fscache_cache.c", "c2de391430c3097d43cdaa48d172bdb00c3405a6799550b9985412490d633024"),
    ("fs/netfs/fscache_cookie.c", "5582559081b3bbf67e9cfd361ee27a63ffcf2973d248e3a05bd3b95e49a2ce45"),
    ("lib/crypto/aescfb.c", "718a46e880372f010abdf657c23fd0ec7cbb76efdd939bd526b7c99483c01a8c"),
    ("lib/crypto/aesgcm.c", "9f83ab9dc4e613ebb73d7e808975f29522de00fdce7f25f7b43fe3cddc4ec4e4"),
    ("drivers/iio/magnetometer/ak8974.c", "1ca66cb95c7596663c08a431cc7217d7d8c1e35684f744c0f8cb70c4aa972b36"),
    ("drivers/input/joystick/magellan.c", "378f72010cc8ac622a55355d6744d29f0dfa166ff061953eb22ba8e8846a1667"),
    ("drivers/net/wireless/ath/carl9170/fw.c", "445740ac539580d044d8209edd64db36405b2691391d72c827ced99436c5b0ca"),
    ("fs/cachefiles/key.c", "8c8a2707524f17f81138607fe2327437421f782ef58b6d1516d2f06315850d62"),
)
CLANG_21_SOURCE_FIX_POSTIMAGE_SHA256S = (
    ("mm/ksm.c", "d3d926171fd7f3cf6885ac57664146182260f43147dc334c2094cc194b4f7f04"),
    ("fs/netfs/fscache_cache.c", "a211f051c4c052504f193566ffac2b31f53bad5f6712ffc7932894bb6b752de1"),
    ("fs/netfs/fscache_cookie.c", "7ce7899790e9928adf5922affb761106229ab0a5430020ff7eb1cfe950fd0ab1"),
    ("lib/crypto/aescfb.c", "2256a26cb3107a1b4d3781170a9ea1db5a235d178f596ca4b47118070e9e9354"),
    ("lib/crypto/aesgcm.c", "2e4bcb4fabcbae935b836bc8c3555716dd8485c39bdebf2f72642f1a38a70c98"),
    ("drivers/iio/magnetometer/ak8974.c", "1f296aed1b37cb88ffdde827e48d7d25fd653ee58ddff63ab915cd8251fc031a"),
    ("drivers/input/joystick/magellan.c", "378f72010cc8ac622a55355d6744d29f0dfa166ff061953eb22ba8e8846a1667"),
    ("drivers/net/wireless/ath/carl9170/fw.c", "33f6e432e29f0d28a0092b3cf1228a590862ae70a3cc2cb8eef9a576e927d2b8"),
    ("fs/cachefiles/key.c", "7973105f797ff23c9e7565a7ac4d938175f506c2e5afb65f7a396c2514fc1d09"),
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CONFIG_LINE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
RUST_BINDING = re.compile(
    r"\bpub\s+(?:(?:unsafe|const)\s+)*(?:fn|static(?:\s+mut)?)\s+([A-Za-z_][A-Za-z0-9_]*)"
)
TOOL_PROBES = (
    ("python", (sys.executable, "--version")),
    ("make", ("make", "--version")),
    ("clang", ("clang", "--version")),
    ("ld.lld", ("ld.lld", "--version")),
    ("llvm-nm", ("llvm-nm", "--version")),
    ("rustc", ("rustc", "--version", "--verbose")),
    ("bindgen", ("bindgen", "--version")),
    ("pahole", ("pahole", "--version")),
    ("openssl", ("openssl", "version")),
    ("patch", ("patch", "--version")),
    ("rpm", ("rpm", "--version")),
)
RUST_COMPAT_UPSTREAM_COMMITS = (
    "6273a058383e05465083b535ed9469f2c8a48321",
    "8851e27d2cb947ea8bbbe8e812068f7bf5cbd00b",
    "ac954145e1ee3f72033161cbe4ac0b16b5354ae7",
    "f4daa80d6be7d3c55ca72a8e560afc4e21f886aa",
    "7129ea6e242b00938532537da41ddf5fa3e21471",
    None,
    "7498159226772d66f150dd406be462d75964a366",
    "c95bbb59a9b22f9b838b15d28319185c1c884329",
    "31d813a3b8cbde2d09ba4dee282ca29096541006",
    "d0afcfeb9e3810ec89d1ffde1a0e36621bb75dca",
    "153ad566724fe6f57b14f66e9726d295d22e576d",
    "58db1c3cd0ce857e7210b0a95908900c25c28c3e",
    "e202196b8aa249d78ab87eae56bbe0e71e3dc39c",
    "05e8d261a34e5c637e37be55c26e42cf5c75ee5c",
    "d5d45a7f26194460964eb5677a9226697f7b7fdd",
    "9d7a0577c9db35c4cc52db90bc415ea248446472",
    "a79be02bba5c31f967885c7f3bf3a756d77d11d9",
    "4f79eaa2ceac86a0e0f304b0bab556cca5bf4f30",
    "a69dc41a4211b0da311ae3a3b79dd4497c9dfb60",
    "f893691e742688ae21ad597c5bba13bef54706cd",
    None,
    None,
    None,
    None,
)
RUST_COMPAT_STABLE_COMMITS = (
    None,
    None,
    "1814e71a4e9c20bd69dbe1e007d31c0ab2c237a2",
    "60d8db49ef143c04f7daf90dafa3347a7af3b4c7",
    "376b73292a262124c8aed10026e9da23e92554b2",
    "5d2d34f36724585801937e76f81a69ab97cd045b",
    "d9ebd928288bb82df8efeb3a34f2cd31883f440e",
    "e18d5b42489311bc86d7ce5fb0f19af067495589",
    None,
    "511ceee89966ce906ca8989523e1a67ba6de44c1",
    "f7ff0324760013762088f70d74ed1ddb7edffb13",
    None,
    None,
    None,
    "9f58537e9b8f07d56aca68308dc73db60fbc7ad3",
    "d66cf772bebd789448121cdfc42734fb042c9c4b",
    "3f856d5d84467c7fba0bf3cca405089c497e37eb",
    "dd8a734155ae28094d27b96c00a478fa0ee6d5d7",
    None,
    None,
    None,
    None,
    None,
    None,
)
RUST_CORE_COMPAT_FAILURE_EVIDENCE = (
    {
        "workflow": "RS-001 exact Rocky Linux API evidence",
        "repository_commit": "e1010bcf9129306ef4bc8b14b569d8c1802f2595",
        "run_id": 31566495851,
        "job_id": 94019257413,
        "artifact_id": None,
        "artifact_zip_sha256": None,
        "rust_core_diagnostic_count": 8,
    },
    {
        "workflow": "Native Rust host modules exact Rocky build",
        "repository_commit": "3b46c7e1be9cd89d35b45e228ee8c96ea87c77ae",
        "run_id": 31566770544,
        "job_id": 94020070018,
        "artifact_id": 9129770822,
        "artifact_zip_sha256": "f08bfab3394c91bf7aaf6709f558b3ccf1aac9f8e1b4605617bafa7ea25b10d2",
        "rust_core_diagnostic_count": 8,
    },
)
RUST_UAPI_COMPAT_FAILURE_EVIDENCE = (
    {
        "workflow": "RS-001 exact Rocky Linux API evidence",
        "repository_commit": "c0b8687f39f6718c3647beaaa5e84c58fbbf6878",
        "run_id": 31568982595,
        "job_id": 94026729494,
        "artifact_id": None,
        "artifact_zip_sha256": None,
        "rust_uapi_diagnostic_count": 156,
    },
    {
        "workflow": "Native Rust host modules exact Rocky build",
        "repository_commit": "c0b8687f39f6718c3647beaaa5e84c58fbbf6878",
        "run_id": 31568982672,
        "job_id": 94026729704,
        "artifact_id": 9130600533,
        "artifact_zip_sha256": "ee6413b03d472e7dc770a39f90b31e3439e0d1c65467f9c05da8b1dc7516b6a1",
        "rust_uapi_diagnostic_count": 156,
    },
)
RUST_KERNEL_1_92_RECONCILIATION_FAILURE_EVIDENCE = (
    {
        "workflow": "RS-001 exact Rocky Linux API evidence",
        "repository_commit": "8bf9446938faf08d8bb4ab1c6d177dcfd8212660",
        "run_id": 31571633622,
        "job_id": 94034684734,
        "artifact_id": None,
        "artifact_zip_sha256": None,
        "artifact_zip_bytes": None,
        "rust_kernel_diagnostic_count": 8,
    },
    {
        "workflow": "Native Rust host modules exact Rocky build",
        "repository_commit": "8bf9446938faf08d8bb4ab1c6d177dcfd8212660",
        "run_id": 31571633686,
        "job_id": 94034684824,
        "artifact_id": 9131625436,
        "artifact_zip_sha256": "fa0a900b182da68e818e751f56980ca7432a8ea1108e9ac6b25426784b53cbab",
        "artifact_zip_bytes": 60214,
        "rust_kernel_diagnostic_count": 8,
    },
)
RUST_OBJTOOL_NORETURN_FAILURE_EVIDENCE = {
    "workflow": "Native Rust host modules exact Rocky build",
    "repository_commit": "9438ad175b4c1ac7855f6afc119f154639fe18c2",
    "run_id": 31644047766,
    "job_id": 94273299611,
    "artifact_id": 9160078637,
    "artifact_zip_bytes": 62669,
    "artifact_zip_sha256": (
        "e4c3786f8fed3255fcd4f4c9e9baba340527050bf5be1b044b9c81cdd5a4cfbc"
    ),
    "rustc_version": "1.92.0",
    "objtool_diagnostic_count": 1,
    "symbol_fragment": "_4core9panicking11panic_const23panic_const_",
}
CLANG_21_DEFAULT_CONST_FAILURE_EVIDENCE = (
    {
        "workflow": "RS-001 exact Rocky Linux API evidence",
        "repository_commit": "54e0bb475336b8c7661ad026de289625e06c8f64",
        "run_id": 31574226844,
        "job_id": 94042622684,
        "artifact_id": None,
        "artifact_zip_sha256": None,
        "artifact_zip_bytes": None,
        "clang_default_const_diagnostic_count": 3,
    },
    {
        "workflow": "Native Rust host modules exact Rocky build",
        "repository_commit": "54e0bb475336b8c7661ad026de289625e06c8f64",
        "run_id": 31574226958,
        "job_id": 94042622785,
        "artifact_id": 9132598094,
        "artifact_zip_sha256": "456d947ea5a4e73de2da7ff6e4dd41376c62ccb0ca91e38fbdbe3fefe5e65d79",
        "artifact_zip_bytes": 112757,
        "clang_default_const_diagnostic_count": 3,
    },
)
OPENSSL_TOOL_CLOSURE_FAILURE_EVIDENCE = (
    {
        "workflow": "RS-001 exact Rocky Linux API evidence",
        "repository_commit": "9490d9a33aabd9ba1d823d2ab390d792f55f0eba",
        "run_id": 31576319131,
        "job_id": 94049141031,
        "artifact_id": None,
        "artifact_zip_sha256": None,
        "artifact_zip_bytes": None,
        "missing_command": "openssl",
        "failure_boundary": "GENKEY certs/signing_key.pem",
    },
    {
        "workflow": "Native Rust host modules exact Rocky build",
        "repository_commit": "9490d9a33aabd9ba1d823d2ab390d792f55f0eba",
        "run_id": 31576319128,
        "job_id": 94049140684,
        "artifact_id": 9133510114,
        "artifact_zip_sha256": "c7a76b23e9ed3443f270e23d28cce187965b11ea4a8d13ec03fcf5bbf0053c99",
        "artifact_zip_bytes": 132850,
        "missing_command": "openssl",
        "failure_boundary": "GENKEY certs/signing_key.pem",
    },
)
CLANG_21_SOURCE_FAILURE_EVIDENCE = (
    {
        "workflow": "RS-001 exact Rocky Linux API evidence",
        "repository_commit": "6059a00d15cd68b834ede0e9c28e28d934bdd071",
        "run_id": 31581528986,
        "job_id": 94065469904,
        "artifact_id": None,
        "artifact_zip_sha256": None,
        "artifact_zip_bytes": None,
        "diagnostic": (
            "-Wsometimes-uninitialized; "
            "-Wunterminated-string-initialization"
        ),
        "failure_boundary": "mm/ksm.o and fs/netfs/fscache_cache.o",
        "clang_21_source_diagnostic_count": 2,
    },
    {
        "workflow": "Native Rust host modules exact Rocky build",
        "repository_commit": "ab6d62e758c7fe2c1a396c720da59e9ddee44458",
        "run_id": 31578138109,
        "job_id": 94054822782,
        "artifact_id": 9134206857,
        "artifact_zip_sha256": "4c971df8d5be18499334d776a20bad7eb23f05ac88259e6dab5d064d035359be",
        "artifact_zip_bytes": 137224,
        "diagnostic": "-Wsometimes-uninitialized",
        "failure_boundary": "mm/ksm.o",
        "clang_21_source_diagnostic_count": 1,
    },
)
PVH_OBJTOOL_LOCAL_ORIGIN = "McKernel Rocky 10.2 exact-build compatibility"
PVH_OBJTOOL_ROCKY_BASE = "linux-6.12.0-211.44.1.el10_2"
PVH_OBJTOOL_FAILURE_EVIDENCE = {
    "workflow": "Native Rust host modules exact Rocky build",
    "repository_commit": "80a07871b81aa3d05378eb07b3d4cd9d8b922ef0",
    "run_id": 31605746750,
    "job_id": 94144112731,
    "artifact_id": 9145918955,
    "build_phase": "bzImage",
    "build_exit_code": 2,
    "build_log_sha256": "614f179c466c2721817fbc9b44c1dbaa9e45f4d638ed489e2b31c2c5beb69f6f",
    "build_log_bytes": 232963,
    "diagnostic": "pvh_start_xen+0x64: relocation to !ENDBR: pvh_start_xen+0x0",
    "failure_boundary": "LD vmlinux.o",
}
RUST_ALLOC_SHIM_V2_LOCAL_ORIGIN = "McKernel Rocky 10.2 exact-build compatibility"
RUST_ALLOC_SHIM_V2_ROCKY_BASE = "linux-6.12.0-211.44.1.el10_2"
RUST_ALLOC_SHIM_V2_RUST_REFERENCE = {
    "commit": "6f935a044d1ddeb6160494a6320d008d7c311aef",
    "pull_request": 141061,
}
RUST_ALLOC_SHIM_V2_LINUX_REFERENCE = {
    "allocator_removal_commit": "392e34b6bc22077ef63abf62387ea3e9f39418c1",
}
RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE = {
    "workflow": "Native Rust host modules exact Rocky build",
    "repository_commit": "6f662225cbb4067800b2a16cbcce81e85924a6bc",
    "run_id": 32082343363,
    "job_id": 95547626904,
    "artifact_id": 9305826810,
    "artifact_zip_bytes": 235955,
    "artifact_zip_sha256": (
        "c262ff48d96d1f3d8a9dc577b7cbfc52f6186bfc7c95a83c5db2634ca8f8749b"
    ),
    "build_phase": "bzImage",
    "build_exit_code": 2,
    "build_log_bytes": 234697,
    "build_log_sha256": (
        "beb8153582de991449fed2958746210cd060d4887cad79fe777d8cfe4b3d4b50"
    ),
    "rustc_version": "1.92.0",
    "diagnostic": (
        "undefined symbol: __rustc::__rust_no_alloc_shim_is_unstable_v2"
    ),
    "failure_boundary": "LD .tmp_vmlinux1",
}


class ProbeError(RuntimeError):
    """Raised when an exact-source contract or capture is malformed."""


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def pretty(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    try:
        with open(str(path), "rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except (IOError, OSError) as exc:
        raise ProbeError("cannot hash {0}: {1}".format(path, exc))
    return digest.hexdigest()


def object_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def read_json(path):
    try:
        with open(str(path), "r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=object_without_duplicates)
    except (IOError, OSError, ValueError) as exc:
        raise ProbeError("cannot parse {0}: {1}".format(path, exc))
    if not isinstance(value, dict):
        raise ProbeError("{0} must contain one JSON object".format(path))
    return value


def atomic_write(path, text):
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(path))
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def require_keys(value, keys, label):
    if not isinstance(value, dict):
        raise ProbeError("{0} must be an object".format(label))
    if set(value) != set(keys):
        raise ProbeError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(set(keys) - set(value)), sorted(set(value) - set(keys))
            )
        )
    return value


def regular_file(path, label):
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise ProbeError("{0} is missing, non-regular, or a symlink: {1}".format(label, path))
    return resolved


def repository_file(repo, relative, label):
    if relative.is_absolute() or ".." in relative.parts:
        raise ProbeError("{0} escapes repository: {1}".format(label, relative))
    candidate = repo / relative
    resolved = candidate.resolve()
    try:
        common = os.path.commonpath((str(resolved), str(repo.resolve())))
    except ValueError:
        common = ""
    if common != str(repo.resolve()):
        raise ProbeError("{0} escapes repository: {1}".format(label, candidate))
    return regular_file(candidate, label)


def file_record(path):
    path = regular_file(path, "capture input")
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def evidence_digest(value):
    unsigned = copy.deepcopy(value)
    unsigned.pop("evidence_sha256", None)
    return sha256_bytes(canonical_bytes(unsigned))


def contract_digest(value):
    unsigned = copy.deepcopy(value)
    unsigned.pop("contract_sha256", None)
    return sha256_bytes(canonical_bytes(unsigned))


def validate_needs_manifest(manifest):
    if manifest.get("schema_version") != 1:
        raise ProbeError("Linux API needs schema changed")
    if manifest.get("manifest_id") != "mckernel-native-rust-linux-api-needs-v1":
        raise ProbeError("Linux API needs identity changed")
    unsigned = copy.deepcopy(manifest)
    recorded = unsigned.pop("manifest_sha256", None)
    if recorded != sha256_bytes(canonical_bytes(unsigned)):
        raise ProbeError("Linux API needs manifest digest is stale")
    needs = manifest.get("needs")
    if not isinstance(needs, list) or len(needs) != EXPECTED_NEED_COUNT:
        raise ProbeError("Linux API needs must contain exactly 268 rows")
    ids = []
    prior = None
    for index, need in enumerate(needs):
        if not isinstance(need, dict):
            raise ProbeError("need {0} is malformed".format(index))
        need_id = need.get("id")
        symbol = need.get("symbol")
        kind = need.get("lookup_kind")
        modules = need.get("owner", {}).get("consuming_modules")
        if (
            not isinstance(need_id, str)
            or not isinstance(symbol, str)
            or kind not in ("module_import", "dynamic_kallsyms")
            or not isinstance(modules, list)
            or not modules
            or any(module not in EXPECTED_MODULES for module in modules)
        ):
            raise ProbeError("need {0} has invalid identity".format(index))
        key = (0 if kind == "module_import" else 1, symbol)
        if prior is not None and key <= prior:
            raise ProbeError("Linux API needs are not unique and sorted")
        prior = key
        ids.append(need_id)
    if len(ids) != len(set(ids)):
        raise ProbeError("Linux API need IDs are duplicated")
    coverage = manifest.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("need_count") != len(needs):
        raise ProbeError("Linux API needs coverage is stale")
    return needs


def lock_record(repo, relative):
    path = repository_file(repo, relative, str(relative))
    value = read_json(path)
    return value, {
        "path": str(relative),
        "sha256": sha256_file(path),
    }


def rust_compatibility_patch_records(repo):
    fixture = repository_file(
        repo, RUST_COMPAT_FIXTURE_PATH, "Rocky Rust target generator fixture"
    )
    if sha256_file(fixture) != RUST_COMPAT_FIXTURE_SHA256:
        raise ProbeError("Rocky Rust target generator fixture digest changed")
    for relative, digest in RUST_CORE_COMPAT_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Rust core fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError("Rocky Rust core fixture digest changed: {0}".format(relative))
    for relative, digest in RUST_BINDINGS_COMPAT_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Rust bindings fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Rust bindings fixture digest changed: {0}".format(relative)
            )
    for relative, digest in RUST_1_89_COMPAT_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Rust 1.89 compatibility fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Rust 1.89 compatibility fixture digest changed: {0}".format(
                    relative
                )
            )
    for relative, digest in RUST_1_92_RECONCILIATION_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Rust 1.92 reconciliation fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Rust 1.92 reconciliation fixture digest changed: {0}".format(
                    relative
                )
            )
    for relative, digest in CLANG_21_WARNING_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Clang 21 warning-policy fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Clang 21 warning-policy fixture digest changed: {0}".format(
                    relative
                )
            )
    for relative, digest in CLANG_21_SOURCE_FIX_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Clang 21 source-fix fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Clang 21 source-fix fixture digest changed: {0}".format(
                    relative
                )
            )
    for relative, digest in RUST_MISCDEVICE_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Rust miscdevice fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Rust miscdevice fixture digest changed: {0}".format(relative)
            )
    for relative, digest in RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Rust Objtool fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Rust Objtool fixture digest changed: {0}".format(relative)
            )
    for relative, digest in PVH_OBJTOOL_COMPAT_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky PVH objtool fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky PVH objtool fixture digest changed: {0}".format(relative)
            )
    for relative, digest in RUST_ALLOC_SHIM_V2_FIXTURE_PREIMAGE_SHA256S:
        path = repository_file(
            repo,
            RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
            "Rocky Rust allocator shim fixture file",
        )
        if sha256_file(path) != digest:
            raise ProbeError(
                "Rocky Rust allocator shim fixture digest changed: {0}".format(
                    relative
                )
            )
    records = []
    required_additions = (
        {
            "+    fn rustc_version_atleast(&self, major: u32, minor: u32, patch: u32)": 1,
            "+        if cfg.rustc_version_atleast(1, 86, 0) {": 2,
            '+            ts.push("rustc-abi", "x86-softfloat");': 2,
        },
        {
            "+        if cfg.rustc_version_atleast(1, 91, 0) {": 2,
            '+            ts.push("target-pointer-width", 64);': 1,
            '+            ts.push("target-pointer-width", 32);': 1,
        },
        {
            "+rustc-min-version = $(call test-ge, $(CONFIG_RUSTC_VERSION), $1)": 1,
            "+ifeq ($(call rustc-min-version, 108500),y)": 1,
            "+$(RUSTC) support functions": 1,
        },
        {
            "+core-edition := $(if $(call rustc-min-version,108700),2024,2021)": 1,
            "+$(obj)/core.o: private skip_flags = --edition=2021 -Wunreachable_pub": 1,
            "+$(obj)/core.o: private rustc_target_flags = --edition=$(core-edition) $(core-cfgs)": 1,
            '+    parser.add_argument("core_edition")': 1,
        },
        {
            "+config RUSTC_HAS_UNNECESSARY_TRANSMUTES": 1,
            "+\tdef_bool RUSTC_VERSION >= 108800": 1,
            "+#[cfg_attr(CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES, allow(unnecessary_transmutes))]": 1,
            "+#![cfg_attr(CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES, allow(unnecessary_transmutes))]": 1,
        },
        {
            "+        #[allow(dead_code)]": 2,
        },
        {
            "+\t\t-Zcrate-attr='feature(used_with_arg)' \\": 1,
            "+#![feature(used_with_arg)]": 1,
            "+                    #[used(compiler)]": 4,
            "+                #[used(compiler)]": 1,
            "+rust_allowed_features := new_uninit,used_with_arg": 1,
        },
        {
            "+#![feature(arbitrary_self_types)]": 1,
            "+rust_allowed_features := arbitrary_self_types,new_uninit,used_with_arg": 1,
        },
        {
            "+                    flags: 0,": 1,
        },
        {
            "+KBUILD_CFLAGS += $(call cc-disable-warning, default-const-init-unsafe)": 1,
        },
        {
            "+\tif (ksm_advisor == KSM_ADVISOR_SCAN_TIME)": 1,
            "+\telse\n": 1,
            "+\t\toutput = \"[none] scan-time\";": 1,
        },
        {
            "+static const char fscache_cache_states[NR__FSCACHE_CACHE_STATE] __nonstring = \"-PAEW\";": 1,
            "+static const char fscache_cookie_states[FSCACHE_COOKIE_STATE__NR] __nonstring = \"-LCAIFUWRD\";": 1,
        },
        {
            "+\tu8\tptext[64] __nonstring;": 1,
            "+\tu8\tctext[64] __nonstring;": 1,
            "+\tu8\tkey[AES_MAX_KEY_SIZE] __nonstring;": 1,
            "+\tu8\tiv[AES_BLOCK_SIZE] __nonstring;": 1,
            "+static const u8 __initconst ctext0[16] __nonstring =": 1,
            "+static const u8 __initconst ctext1[32] __nonstring =": 1,
            "+static const u8 __initconst ptext2[64] __nonstring =": 1,
            "+static const u8 __initconst ctext2[80] __nonstring =": 1,
            "+static const u8 __initconst ptext3[60] __nonstring =": 1,
            "+static const u8 __initconst ctext3[76] __nonstring =": 1,
            "+static const u8 __initconst ctext4[16] __nonstring =": 1,
            "+static const u8 __initconst ctext5[32] __nonstring =": 1,
            "+static const u8 __initconst ptext6[64] __nonstring =": 1,
            "+static const u8 __initconst ctext6[80] __nonstring =": 1,
            "+static const u8 __initconst ctext7[16] __nonstring =": 1,
            "+static const u8 __initconst ctext8[32] __nonstring =": 1,
            "+static const u8 __initconst ptext9[64] __nonstring =": 1,
            "+static const u8 __initconst ctext9[80] __nonstring =": 1,
            "+static const u8 __initconst ptext10[60] __nonstring =": 1,
            "+static const u8 __initconst ctext10[76] __nonstring =": 1,
            "+static const u8 __initconst ptext11[60] __nonstring =": 1,
            "+static const u8 __initconst ctext11[76] __nonstring =": 1,
            "+static const u8 __initconst ptext12[719] __nonstring =": 1,
            "+static const u8 __initconst ctext12[735] __nonstring =": 1,
            "+\tu8\t\tkey[AES_MAX_KEY_SIZE] __nonstring;": 1,
            "+\tu8\t\tiv[GCM_AES_IV_SIZE] __nonstring;": 1,
            "+\tu8\t\tassoc[20] __nonstring;": 1,
        },
        {
            "+\t\t\tstatic const char axis[] = \"XYZ\";": 1,
            "+\t\t\tstatic const char pgaxis[] = \"ZYZXYX\";": 1,
            "+static const u8 otus_magic[4] __nonstring = { OTUS_MAGIC };": 1,
            "+static const char cachefiles_charmap[64] __nonstring =": 1,
        },
        {
            "+#Currently, disable -Wunterminated-string-initialization as an error": 1,
            "+KBUILD_CFLAGS += $(call cc-option, -Wno-error=unterminated-string-initialization)": 1,
        },
        {
            "+#Currently, disable -Wunterminated-string-initialization as broken": 1,
            "+KBUILD_CFLAGS += $(call cc-option, -Wno-unterminated-string-initialization)": 1,
        },
        {
            "+KBUILD_CFLAGS-$(CONFIG_CC_NO_STRINGOP_OVERFLOW) += $(call cc-disable-warning, stringop-overflow)": 1,
            "+KBUILD_CFLAGS += $(call cc-disable-warning, unterminated-string-initialization)": 1,
            "+CFLAGS_module.o\t\t+= $(call cc-disable-warning, override-init)": 1,
            "+CFLAGS_syscall.o\t+= $(call cc-disable-warning, override-init)": 1,
            "+CFLAGS_traps.o\t\t+= $(call cc-disable-warning, override-init)": 1,
            "+CFLAGS_perf_event.o\t+= $(call cc-disable-warning, override-init)": 1,
            "+CFLAGS_exit.o\t+= $(call cc-disable-warning, override-init)": 1,
            "+CFLAGS_syscall_table.o\t+= $(call cc-disable-warning, override-init)": 1,
            "+CFLAGS_compat_syscall_table.o += $(call cc-disable-warning, override-init)": 1,
            "+KBUILD_CFLAGS += $(call cc-disable-warning, frame-address)": 1,
        },
        {
            "+KBUILD_CFLAGS += -Wextra": 1,
            "+# Currently, disable -Wstringop-overflow for GCC 11, globally.": 1,
            "+KBUILD_CFLAGS-$(CONFIG_CC_NO_STRINGOP_OVERFLOW) += $(call cc-disable-warning, stringop-overflow)": 1,
            "+KBUILD_CFLAGS-$(CONFIG_CC_STRINGOP_OVERFLOW) += $(call cc-option, -Wstringop-overflow)": 1,
            "+# Currently, disable -Wunterminated-string-initialization as broken": 1,
            "+KBUILD_CFLAGS += $(call cc-disable-warning, unterminated-string-initialization)": 1,
        },
        {
            "+    pub fn try_ffi_init<E>(": 1,
            "+        init_func: impl FnOnce(*mut T) -> Result<(), E>,": 1,
            "+        unsafe { init::pin_init_from_closure::<_, E>(move |slot| init_func(Self::raw_get(slot))) }": 1,
        },
        {
            "+#include <linux/miscdevice.h>": 1,
            "+pub mod miscdevice;": 1,
            "+pub struct MiscDeviceRegistration<T> {": 1,
            "+        result.minor = bindings::MISC_DYNAMIC_MINOR as _;": 1,
            "+                to_result(unsafe { bindings::misc_register(slot) })": 1,
            "+        unsafe { bindings::misc_deregister(self.inner.get()) };": 1,
            "+pub trait MiscDevice {": 1,
            "+    type Ptr: ForeignOwnable + Send + Sync;": 1,
            "+unsafe extern \"C\" fn fops_open<T: MiscDevice>(": 1,
        },
        {
            "+    ThisModule,": 1,
            "+    const MODULE: &'static ThisModule;": 1,
            "+            owner: T::MODULE.as_ptr(),": 1,
            "+            compat_ioctl: maybe_fn(T::HAS_COMPAT_IOCTL, fops_compat_ioctl::<T>),": 1,
        },
        {
            "+\t       strstr(func->name, \"_4core9panicking11panic_const23panic_const_\")\t\t\t||": 1,
        },
        {
            "+\tANNOTATE_NOENDBR": 1,
        },
        {
            "+// See <https://github.com/rust-lang/rust/pull/141061>.": 1,
            "+#[rustc_std_internal_symbol]": 1,
            "+fn __rust_no_alloc_shim_is_unstable_v2() {}": 1,
            "+#![allow(internal_features)]": 1,
            "+#![feature(rustc_attrs)]": 1,
        },
    )
    required_deletions = (
        {},
        {},
        {},
        {},
        {},
        {},
        {},
        {
            "-#![feature(receiver_trait)]": 1,
            "-impl<T, const ID: u64> core::ops::Receiver for ListArc<T, ID> where T: ListArcSafe<ID> + ?Sized {}": 1,
            "-impl<T: ?Sized> core::ops::Receiver for Arc<T> {}": 1,
            "-impl<T: ?Sized> core::ops::Receiver for ArcBorrow<'_, T> {}": 1,
        },
        {
            "-                    flags: bindings::BLK_MQ_F_SHOULD_MERGE,": 1,
        },
        {},
        {
            "-\tif (ksm_advisor == KSM_ADVISOR_NONE)": 1,
            "-\t\toutput = \"[none] scan-time\";": 1,
            "-\telse if (ksm_advisor == KSM_ADVISOR_SCAN_TIME)": 1,
        },
        {
            "-static const char fscache_cache_states[NR__FSCACHE_CACHE_STATE] = \"-PAEW\";": 1,
            "-static const char fscache_cookie_states[FSCACHE_COOKIE_STATE__NR] = \"-LCAIFUWRD\";": 1,
        },
        {
            "-\tu8\tptext[64];": 1,
            "-\tu8\tctext[64];": 1,
            "-\tu8\tkey[AES_MAX_KEY_SIZE];": 1,
            "-\tu8\tiv[AES_BLOCK_SIZE];": 1,
            "-static const u8 __initconst ctext0[16] =": 1,
            "-static const u8 __initconst ctext1[32] =": 1,
            "-static const u8 __initconst ptext2[64] =": 1,
            "-static const u8 __initconst ctext2[80] =": 1,
            "-static const u8 __initconst ptext3[60] =": 1,
            "-static const u8 __initconst ctext3[76] =": 1,
            "-static const u8 __initconst ctext4[16] =": 1,
            "-static const u8 __initconst ctext5[32] =": 1,
            "-static const u8 __initconst ptext6[64] =": 1,
            "-static const u8 __initconst ctext6[80] =": 1,
            "-static const u8 __initconst ctext7[16] =": 1,
            "-static const u8 __initconst ctext8[32] =": 1,
            "-static const u8 __initconst ptext9[64] =": 1,
            "-static const u8 __initconst ctext9[80] =": 1,
            "-static const u8 __initconst ptext10[60] =": 1,
            "-static const u8 __initconst ctext10[76] =": 1,
            "-static const u8 __initconst ptext11[60] =": 1,
            "-static const u8 __initconst ctext11[76] =": 1,
            "-static const u8 __initconst ptext12[719] =": 1,
            "-static const u8 __initconst ctext12[735] =": 1,
            "-\tu8\t\tkey[AES_MAX_KEY_SIZE];": 1,
            "-\tu8\t\tiv[GCM_AES_IV_SIZE];": 1,
            "-\tu8\t\tassoc[20];": 1,
        },
        {
            "-\t\t\tstatic const char axis[3] = \"XYZ\";": 1,
            "-\t\t\tstatic const char pgaxis[6] = \"ZYZXYX\";": 1,
            "-static const u8 otus_magic[4] = { OTUS_MAGIC };": 1,
            "-static const char cachefiles_charmap[64] =": 1,
        },
        {},
        {
            "-#Currently, disable -Wunterminated-string-initialization as an error": 1,
            "-KBUILD_CFLAGS += $(call cc-option, -Wno-error=unterminated-string-initialization)": 1,
        },
        {
            "-KBUILD_CFLAGS-$(CONFIG_CC_NO_STRINGOP_OVERFLOW) += $(call cc-option, -Wno-stringop-overflow)": 1,
            "-KBUILD_CFLAGS += $(call cc-option, -Wno-unterminated-string-initialization)": 1,
            "-CFLAGS_module.o\t\t+= $(call cc-option,-Wno-override-init,)": 1,
            "-CFLAGS_syscall.o\t+= $(call cc-option,-Wno-override-init,)": 1,
            "-CFLAGS_traps.o\t\t+= $(call cc-option,-Wno-override-init,)": 1,
            "-CFLAGS_perf_event.o\t+= $(call cc-option,-Wno-override-init,)": 1,
            "-CFLAGS_exit.o\t+= $(call cc-option,-Wno-override-init,)": 1,
            "-CFLAGS_syscall_table.o\t+= $(call cc-option,-Wno-override-init,)": 1,
            "-CFLAGS_compat_syscall_table.o += $(call cc-option,-Wno-override-init,)": 1,
            "-KBUILD_CFLAGS += $(call cc-disable-warning,frame-address,)": 1,
        },
        {
            "-#Currently, disable -Wstringop-overflow for GCC 11, globally.": 1,
            "-KBUILD_CFLAGS-$(CONFIG_CC_NO_STRINGOP_OVERFLOW) += $(call cc-disable-warning, stringop-overflow)": 1,
            "-KBUILD_CFLAGS-$(CONFIG_CC_STRINGOP_OVERFLOW) += $(call cc-option, -Wstringop-overflow)": 1,
            "-#Currently, disable -Wunterminated-string-initialization as broken": 1,
            "-KBUILD_CFLAGS += $(call cc-disable-warning, unterminated-string-initialization)": 1,
            "-KBUILD_CFLAGS += -Wextra": 1,
        },
        {},
        {},
        {
            "-            compat_ioctl: if T::HAS_COMPAT_IOCTL {": 1,
            "-                Some(bindings::compat_ptr_ioctl)": 1,
        },
        {},
        {},
        {
            "-#[no_mangle]": 1,
            "-static __rust_no_alloc_shim_is_unstable: u8 = 0;": 1,
        },
    )
    expected_diff_counts = (
        1, 1, 3, 2, 3, 1, 4, 4, 1, 1, 1, 2, 2, 3, 1, 1, 5, 2, 1, 3, 1, 1, 1, 2
    )
    for index, relative in enumerate(RUST_COMPAT_PATCH_PATHS):
        path = repository_file(repo, relative, "Rust target compatibility patch")
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (IOError, OSError, UnicodeDecodeError) as exc:
            raise ProbeError(
                "cannot read Rust target compatibility patch: {0}".format(exc)
            )
        if not raw.endswith(b"\n") or b"\r" in raw:
            raise ProbeError("Rust target compatibility patch must be LF-only text")
        commit = RUST_COMPAT_UPSTREAM_COMMITS[index]
        stable_commit = RUST_COMPAT_STABLE_COMMITS[index]
        if (
            (commit is not None and text.count(commit) != (1 if index >= 18 else 2))
            or (
                stable_commit is not None
                and text.count(stable_commit) != 2
            )
            or text.count("diff --git ") != expected_diff_counts[index]
            or any(
                text.count(fragment) != count
                for fragment, count in required_additions[index].items()
            )
            or any(
                text.count(fragment) != count
                for fragment, count in required_deletions[index].items()
            )
            or (
                14 <= index <= 17
                and (
                    text.count("Stable-Branch: linux-6.12.y") != 1
                    or text.count("Stable-First-Release: v6.12.31") != 1
                    or text.count("Rocky-Base: linux-6.12.0-211.44.1.el10_2") != 1
                    or text.count(
                        "Rocky-Series-Context: cumulative ordered repository "
                        "compatibility patches"
                    ) != 1
                    or text.count("License: GPL-2.0-only") != 1
                )
            )
            or (
                index == 20
                and (
                    text.count("From: McKernel local compatibility integration") != 1
                    or text.count(
                        "Status: active ordered Rocky compatibility patch; "
                        "unbuilt and noncrediting"
                    )
                    != 1
                    or text.count("License: " + MISCDEVICE_OWNER_LICENSE) != 1
                    or "Upstream-Commit:" in text
                    or "Stable-Commit:" in text
                )
            )
            or (
                index == 21
                and (
                    text.count(
                        "Observed-Repository-Commit: "
                        "9438ad175b4c1ac7855f6afc119f154639fe18c2"
                    ) != 1
                    or text.count(
                        "Observed-Workflow: Native Rust host modules exact Rocky build"
                    ) != 1
                    or text.count("Observed-Run-ID: 31644047766") != 1
                    or text.count("Observed-Job-ID: 94273299611") != 1
                    or text.count("Observed-Artifact-ID: 9160078637") != 1
                    or text.count("Observed-Artifact-Zip-Bytes: 62669") != 1
                    or text.count(
                        "Observed-Artifact-Zip-SHA256: "
                        "e4c3786f8fed3255fcd4f4c9e9baba340527050bf5be1b044b9c81cdd5a4cfbc"
                    ) != 1
                    or text.count("Observed-Rustc: 1.92.0") != 1
                    or text.count(
                        "Rocky-Base: linux-6.12.0-211.44.1.el10_2"
                    ) != 1
                    or text.count("License: GPL-2.0-only") != 1
                    or "Upstream-Commit:" in text
                    or "Stable-Commit:" in text
                )
            )
            or (
                index == 22
                and (
                    text.count("Local-Origin: " + PVH_OBJTOOL_LOCAL_ORIGIN) != 1
                    or text.count("Rocky-Base: " + PVH_OBJTOOL_ROCKY_BASE) != 1
                    or text.count("Failure-Run: 31605746750") != 1
                    or text.count("Failure-Job: 94144112731") != 1
                    or text.count("Failure-Artifact: 9145918955") != 1
                    or text.count(
                        "Failure-Commit: "
                        + PVH_OBJTOOL_FAILURE_EVIDENCE["repository_commit"]
                    )
                    != 1
                    or text.count("Failure-Phase: bzImage") != 1
                    or text.count("Failure-Exit-Code: 2") != 1
                    or text.count(
                        "Failure-Log-SHA256: "
                        + PVH_OBJTOOL_FAILURE_EVIDENCE["build_log_sha256"]
                    )
                    != 1
                    or text.count("Failure-Log-Bytes: 232963") != 1
                    or text.count("License: GPL-2.0-only") != 1
                    or "absolute relocation as part of a broader PVH cleanup" not in text
                    or "Upstream-Commit:" in text
                    or "Stable-Commit:" in text
                )
            )
            or (
                index == 23
                and (
                    text.count(
                        "Observed-Repository-Commit: "
                        + RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE["repository_commit"]
                    )
                    != 1
                    or text.count(
                        "Observed-Workflow: "
                        + RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE["workflow"]
                    )
                    != 1
                    or text.count("Observed-Run-ID: 32082343363") != 1
                    or text.count("Observed-Job-ID: 95547626904") != 1
                    or text.count("Observed-Artifact-ID: 9305826810") != 1
                    or text.count("Observed-Artifact-Zip-Bytes: 235955") != 1
                    or text.count(
                        "Observed-Artifact-Zip-SHA256: "
                        + RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE[
                            "artifact_zip_sha256"
                        ]
                    )
                    != 1
                    or text.count("Observed-Rustc: 1.92.0") != 1
                    or text.count("Observed-Failure-Phase: bzImage") != 1
                    or text.count("Observed-Build-Log-Bytes: 234697") != 1
                    or text.count(
                        "Observed-Build-Log-SHA256: "
                        + RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE["build_log_sha256"]
                    )
                    != 1
                    or text.count(
                        "Observed-Diagnostic: "
                        + RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE["diagnostic"]
                    )
                    != 1
                    or text.count("Rust-Reference-PR: 141061") != 1
                    or text.count(
                        "Rust-Reference-Commit: "
                        + RUST_ALLOC_SHIM_V2_RUST_REFERENCE["commit"]
                    )
                    != 1
                    or text.count(
                        RUST_ALLOC_SHIM_V2_LINUX_REFERENCE[
                            "allocator_removal_commit"
                        ]
                    )
                    != 1
                    or text.count(
                        "Local-Origin: " + RUST_ALLOC_SHIM_V2_LOCAL_ORIGIN
                    )
                    != 1
                    or text.count(
                        "Rocky-Base: " + RUST_ALLOC_SHIM_V2_ROCKY_BASE
                    )
                    != 1
                    or text.count("License: GPL-2.0-only") != 1
                    or "Upstream-Commit:" in text
                    or "Stable-Commit:" in text
                )
            )
        ):
            raise ProbeError(
                "Rust target compatibility patch is not frozen upstream commit {0}".format(
                    commit or stable_commit
                )
            )
        record = {
            "applied_after": (
                "exact Rocky dist-git patch series"
                if index == 0
                else str(RUST_COMPAT_PATCH_PATHS[index - 1])
            ),
            "path": str(relative),
            "sha256": sha256_bytes(raw),
            "size": len(raw),
            "stable_commit": stable_commit,
            "upstream_commit": commit,
        }
        if index == 20:
            record.update(
                {
                    "integration_status": MISCDEVICE_OWNER_INTEGRATION_STATUS,
                    "license": MISCDEVICE_OWNER_LICENSE,
                    "local_origin": MISCDEVICE_OWNER_LOCAL_ORIGIN,
                    "rocky_base": MISCDEVICE_OWNER_ROCKY_BASE,
                }
            )
        elif index == 21:
            relative_path, preimage_sha256 = RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S[0]
            _relative_path, postimage_sha256 = RUST_OBJTOOL_NORETURN_POSTIMAGE_SHA256S[0]
            record["observed_failure"] = dict(RUST_OBJTOOL_NORETURN_FAILURE_EVIDENCE)
            record["preimage"] = {
                "path": relative_path,
                "sha256": preimage_sha256,
                "size": 116914,
            }
            record["postimage"] = {
                "path": relative_path,
                "sha256": postimage_sha256,
                "size": 116993,
            }
        elif index == 22:
            record.update(
                {
                    "failure_evidence": dict(PVH_OBJTOOL_FAILURE_EVIDENCE),
                    "license": "GPL-2.0-only",
                    "local_origin": PVH_OBJTOOL_LOCAL_ORIGIN,
                    "rocky_base": PVH_OBJTOOL_ROCKY_BASE,
                }
            )
        elif index == 23:
            record.update(
                {
                    "failure_evidence": dict(RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE),
                    "license": "GPL-2.0-only",
                    "linux_reference": dict(RUST_ALLOC_SHIM_V2_LINUX_REFERENCE),
                    "local_origin": RUST_ALLOC_SHIM_V2_LOCAL_ORIGIN,
                    "postimages": [
                        dict(row) for row in RUST_ALLOC_SHIM_V2_POSTIMAGES
                    ],
                    "preimages": [
                        dict(row) for row in RUST_ALLOC_SHIM_V2_PREIMAGES
                    ],
                    "rocky_base": RUST_ALLOC_SHIM_V2_ROCKY_BASE,
                    "rust_reference": dict(RUST_ALLOC_SHIM_V2_RUST_REFERENCE),
                }
            )
        records.append(record)
    return records


def verify_rust_compatibility_patch_replay(repo, records):
    fixture = repository_file(
        repo, RUST_COMPAT_FIXTURE_PATH, "Rocky Rust target generator fixture"
    )
    with tempfile.TemporaryDirectory(prefix="rs001-rust-compat-") as temporary:
        root = Path(temporary)
        target = root / "scripts/generate_rust_target.rs"
        target.parent.mkdir()
        shutil.copyfile(str(fixture), str(target))
        for record in records[:2]:
            patch_path = repository_file(
                repo, Path(record["path"]), "Rust target compatibility patch"
            )
            run_checked(
                [
                    shutil.which("patch") or "patch",
                    "-p1",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(patch_path),
                ],
                root,
            )
        if sha256_file(target) != RUST_COMPAT_POSTIMAGE_SHA256:
            raise ProbeError("Rust target compatibility patch postimage changed")
    with tempfile.TemporaryDirectory(prefix="rs001-rust-core-compat-") as temporary:
        root = Path(temporary)
        for relative, _unused_digest in (
            RUST_CORE_COMPAT_PREIMAGE_SHA256S
            + RUST_BINDINGS_COMPAT_PREIMAGE_SHA256S
            + RUST_1_89_COMPAT_PREIMAGE_SHA256S
            + RUST_1_92_RECONCILIATION_PREIMAGE_SHA256S
            + CLANG_21_WARNING_PREIMAGE_SHA256S
            + CLANG_21_SOURCE_FIX_PREIMAGE_SHA256S
            + RUST_MISCDEVICE_PREIMAGE_SHA256S
            + RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S
            + PVH_OBJTOOL_COMPAT_PREIMAGE_SHA256S
            + RUST_ALLOC_SHIM_V2_FIXTURE_PREIMAGE_SHA256S
        ):
            source = repository_file(
                repo,
                RUST_CORE_COMPAT_FIXTURE_ROOT / relative,
                "Rocky Rust core fixture file",
            )
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source), str(target))
        block_flag = "BLK_MQ_F_SHOULD_MERGE"
        if block_flag in (root / "include/linux/blk-mq.h").read_text(
            encoding="utf-8"
        ) or (root / "rust/kernel/block/mq/tag_set.rs").read_text(
            encoding="utf-8"
        ).count(block_flag) != 1:
            raise ProbeError(
                "Rocky Rust block source no longer has the frozen C/Rust flag mismatch"
            )
        for record in records[2:7]:
            patch_path = repository_file(
                repo, Path(record["path"]), "Rust core compatibility patch"
            )
            run_checked(
                [
                    shutil.which("patch") or "patch",
                    "-p1",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(patch_path),
                ],
                root,
            )
        for relative, digest in RUST_CORE_COMPAT_POSTIMAGE_SHA256S:
            if sha256_file(root / relative) != digest:
                raise ProbeError(
                    "Rust core compatibility patch postimage changed: {0}".format(
                        relative
                    )
                )
        for relative, digest in RUST_BINDINGS_COMPAT_POSTIMAGE_SHA256S:
            if sha256_file(root / relative) != digest:
                raise ProbeError(
                    "Rust bindings compatibility patch postimage changed: {0}".format(
                        relative
                    )
                )
        for relative, digest in RUST_1_89_COMPAT_POSTIMAGE_SHA256S:
            if sha256_file(root / relative) != digest:
                raise ProbeError(
                    "Rust 1.89 compatibility patch postimage changed: {0}".format(
                        relative
                    )
                )
        for record in records[7:-1]:
            patch_path = repository_file(
                repo, Path(record["path"]), "Rust 1.92 reconciliation patch"
            )
            run_checked(
                [
                    shutil.which("patch") or "patch",
                    "-p1",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(patch_path),
                ],
                root,
            )
        for row in RUST_ALLOC_SHIM_V2_PREIMAGES:
            path = root / row["path"]
            if sha256_file(path) != row["sha256"] or path.stat().st_size != row["size"]:
                raise ProbeError(
                    "Rust allocator shim patch preimage changed: {0}".format(
                        row["path"]
                    )
                )
        allocator_patch = repository_file(
            repo,
            Path(records[-1]["path"]),
            "Rust allocator shim compatibility patch",
        )
        run_checked(
            [
                shutil.which("patch") or "patch",
                "-p1",
                "--batch",
                "--forward",
                "--fuzz=0",
                "--no-backup-if-mismatch",
                "-i",
                str(allocator_patch),
            ],
            root,
        )
        pvh_patch = repository_file(
            repo,
            Path(records[-2]["path"]),
            "PVH objtool compatibility patch",
        )
        try:
            second_apply = subprocess.run(
                [
                    shutil.which("patch") or "patch",
                    "-p1",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(pvh_patch),
                ],
                cwd=str(root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProbeError(
                "PVH compatibility second-apply check failed to execute: {0}".format(
                    exc
                )
            )
        if second_apply.returncode == 0:
            raise ProbeError("PVH compatibility patch unexpectedly applies twice")
        try:
            allocator_second_apply = subprocess.run(
                [
                    shutil.which("patch") or "patch",
                    "-p1",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(allocator_patch),
                ],
                cwd=str(root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProbeError(
                "Rust allocator shim second-apply check failed to execute: {0}".format(
                    exc
                )
            )
        if allocator_second_apply.returncode == 0:
            raise ProbeError(
                "Rust allocator shim compatibility patch unexpectedly applies twice"
            )
        for relative, digest in RUST_1_92_RECONCILIATION_POSTIMAGE_SHA256S:
            if (
                relative not in dict(RUST_MISCDEVICE_POSTIMAGE_SHA256S)
                and sha256_file(root / relative) != digest
            ):
                raise ProbeError(
                    "Rust 1.92 reconciliation patch postimage changed: {0}".format(
                        relative
                    )
                )
        for relative, digest in CLANG_21_WARNING_POSTIMAGE_SHA256S:
            if sha256_file(root / relative) != digest:
                raise ProbeError(
                    "Clang 21 warning-policy patch postimage changed: {0}".format(
                        relative
                    )
                )
        for relative, digest in CLANG_21_SOURCE_FIX_POSTIMAGE_SHA256S:
            if sha256_file(root / relative) != digest:
                raise ProbeError(
                    "Clang 21 source-fix patch postimage changed: {0}".format(
                        relative
                    )
                )
        for relative, digest in RUST_MISCDEVICE_POSTIMAGE_SHA256S:
            if (
                relative not in {row["path"] for row in RUST_ALLOC_SHIM_V2_POSTIMAGES}
                and sha256_file(root / relative) != digest
            ):
                raise ProbeError(
                    "Rust miscdevice compatibility patch postimage changed: {0}".format(
                        relative
                    )
                )
        for relative, digest in RUST_OBJTOOL_NORETURN_POSTIMAGE_SHA256S:
            if sha256_file(root / relative) != digest:
                raise ProbeError(
                    "Rust Objtool compatibility patch postimage changed: {0}".format(
                        relative
                    )
                )
        for relative, digest in PVH_OBJTOOL_COMPAT_POSTIMAGE_SHA256S:
            if sha256_file(root / relative) != digest:
                raise ProbeError(
                    "PVH objtool compatibility patch postimage changed: {0}".format(
                        relative
                    )
                )
        for row in RUST_ALLOC_SHIM_V2_POSTIMAGES:
            path = root / row["path"]
            if sha256_file(path) != row["sha256"] or path.stat().st_size != row["size"]:
                raise ProbeError(
                    "Rust allocator shim patch postimage changed: {0}".format(
                        row["path"]
                    )
                )
        if block_flag in (root / "rust/kernel/block/mq/tag_set.rs").read_text(
            encoding="utf-8"
        ):
            raise ProbeError("Rust block reconciliation retained the removed merge flag")


def build_contract(repo):
    needs_path = repository_file(repo, NEEDS_PATH, "Linux API needs")
    needs_manifest = read_json(needs_path)
    needs = validate_needs_manifest(needs_manifest)
    source_lock, source_record = lock_record(repo, SOURCE_LOCK_PATH)
    patch_series, patch_record = lock_record(repo, PATCH_SERIES_PATH)
    config_policy, config_record = lock_record(repo, CONFIG_POLICY_PATH)
    toolchain_lock, toolchain_record = lock_record(repo, TOOLCHAIN_LOCK_PATH)
    rust_compat_records = rust_compatibility_patch_records(repo)
    verify_rust_compatibility_patch_replay(repo, rust_compat_records)
    source_rpm = source_lock.get("source_rpm", {})
    embedded = source_lock.get("embedded_objects", [])
    archives = [
        row
        for row in embedded
        if isinstance(row, dict)
        and row.get("role") == "Rocky-derived Linux source archive"
    ]
    if len(archives) != 1:
        raise ProbeError("source lock must name exactly one Linux source archive")
    if source_lock.get("lock_id") != config_policy.get("source_lock_id"):
        raise ProbeError("source and config locks diverge")
    if source_lock.get("lock_id") != toolchain_lock.get("source_lock", {}).get(
        "lock_id"
    ):
        raise ProbeError("source and toolchain locks diverge")
    patch_rows = patch_series.get("patches")
    if not isinstance(patch_rows, list):
        raise ProbeError("patch series is malformed")
    ids = [row["id"] for row in needs]
    workflow = repository_file(repo, WORKFLOW_PATH, "RS-001 workflow")
    script = repository_file(repo, SCRIPT_PATH, "RS-001 checker")
    contract = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "gate": {
            "gate_id": "RS-001",
            "credit_eligible": False,
            "self_attestation_forbidden": True,
            "policy": (
                "Capture may prove exact technical facts but can never mark RS-001 PASS; "
                "independent review and evidence registration are required."
            ),
        },
        "target": {
            "distribution": "Rocky Linux",
            "release": "10.2",
            "architecture": "x86_64",
            "kernel_nvr": source_rpm.get("nvr"),
            "source_rpm_filename": source_rpm.get("filename"),
            "source_rpm_bytes": source_rpm.get("size"),
            "source_rpm_sha256": source_rpm.get("sha256"),
            "source_archive_filename": archives[0].get("path", "").split("/")[-1],
            "source_archive_root": archives[0].get("path", "").split("/")[-1].rsplit(
                ".tar.xz", 1
            )[0],
            "source_archive_bytes": archives[0].get("size"),
            "source_archive_sha256": archives[0].get("sha256"),
        },
        "frozen_needs": {
            "path": str(NEEDS_PATH),
            "file_sha256": sha256_file(needs_path),
            "manifest_sha256": needs_manifest["manifest_sha256"],
            "need_count": len(needs),
            "need_ids_sha256": sha256_bytes(canonical_bytes(ids)),
        },
        "repository_inputs": {
            "source_lock": source_record,
            "patch_series": patch_record,
            "rust_target_compatibility_patches": rust_compat_records,
            "rust_target_generator_preimage": {
                "path": str(RUST_COMPAT_FIXTURE_PATH),
                "sha256": RUST_COMPAT_FIXTURE_SHA256,
            },
            "rust_core_build_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in RUST_CORE_COMPAT_PREIMAGE_SHA256S
            ],
            "rust_bindings_build_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in RUST_BINDINGS_COMPAT_PREIMAGE_SHA256S
            ],
            "rust_1_89_build_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in RUST_1_89_COMPAT_PREIMAGE_SHA256S
            ],
            "rust_1_92_reconciliation_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in RUST_1_92_RECONCILIATION_PREIMAGE_SHA256S
            ],
            "rust_objtool_noreturn_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S
            ],
            "clang_21_warning_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in CLANG_21_WARNING_PREIMAGE_SHA256S
            ],
            "clang_21_source_fix_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in CLANG_21_SOURCE_FIX_PREIMAGE_SHA256S
            ],
            "pvh_objtool_compatibility_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in PVH_OBJTOOL_COMPAT_PREIMAGE_SHA256S
            ],
            "rust_alloc_shim_v2_fixture_preimages": [
                {
                    "path": str(RUST_CORE_COMPAT_FIXTURE_ROOT / relative),
                    "sha256": digest,
                }
                for relative, digest in RUST_ALLOC_SHIM_V2_FIXTURE_PREIMAGE_SHA256S
            ],
            "config_policy": config_record,
            "toolchain_lock": toolchain_record,
            "checker": {"path": str(SCRIPT_PATH), "sha256": sha256_file(script)},
            "workflow": {"path": str(WORKFLOW_PATH), "sha256": sha256_file(workflow)},
        },
        "rust_core_compatibility_failure_evidence": [
            dict(row) for row in RUST_CORE_COMPAT_FAILURE_EVIDENCE
        ],
        "rust_uapi_compatibility_failure_evidence": [
            dict(row) for row in RUST_UAPI_COMPAT_FAILURE_EVIDENCE
        ],
        "rust_kernel_1_92_reconciliation_failure_evidence": [
            dict(row) for row in RUST_KERNEL_1_92_RECONCILIATION_FAILURE_EVIDENCE
        ],
        "rust_objtool_noreturn_failure_evidence": dict(
            RUST_OBJTOOL_NORETURN_FAILURE_EVIDENCE
        ),
        "rust_alloc_shim_v2_failure_evidence": dict(
            RUST_ALLOC_SHIM_V2_FAILURE_EVIDENCE
        ),
        "clang_21_default_const_failure_evidence": [
            dict(row) for row in CLANG_21_DEFAULT_CONST_FAILURE_EVIDENCE
        ],
        "openssl_tool_closure_failure_evidence": [
            dict(row) for row in OPENSSL_TOOL_CLOSURE_FAILURE_EVIDENCE
        ],
        "clang_21_source_failure_evidence": [
            dict(row) for row in CLANG_21_SOURCE_FAILURE_EVIDENCE
        ],
        "source_patch_contract": {
            "patches": [
                {
                    "applied": row.get("applied"),
                    "empty": row.get("empty"),
                    "path": row.get("path"),
                    "sha256": row.get("sha256"),
                    "size": row.get("size"),
                }
                for row in patch_rows
            ]
            + [
                {
                    "applied": True,
                    "empty": False,
                    "path": record["path"],
                    "sha256": record["sha256"],
                    "size": record["size"],
                }
                for record in rust_compat_records
            ],
            "tree_comparison": (
                "fresh locked archive plus every applied Rocky patch and the bound "
                "Rust target compatibility patch must byte-match the supplied "
                "out-of-tree build source"
            ),
        },
        "required_capture_inputs": [
            "locked source RPM bytes",
            "locked Linux source archive bytes",
            "all locked Rocky and repository compatibility patch bytes",
            "byte-exact patched source tree",
            "locked Rocky x86_64 baseline config",
            "first and second idempotent resolved configs",
            "Module.symvers from the exact selected build",
            "System.map from the exact selected build",
            "generated Rust bindings from the exact selected build",
            "kernel.release and compiler/tool provenance",
        ],
        "per_need_evidence": [
            "availability in System.map and/or Module.symvers",
            "export class, provider module, and namespace",
            "selected config digest plus separately reviewed Kconfig requirements",
            "generated Rust binding or separately reviewed Rust abstraction",
            "separately reviewed compiler-backed consumer context classification",
        ],
        "reviewed_map_pins": {
            "config_requirements_sha256": None,
            "consumer_contexts_sha256": None,
            "rust_abstractions_sha256": None,
        },
        "readiness_without_exact_capture": {
            "gate_status": "NOT_READY",
            "technical_complete": False,
            "credit_eligible": False,
            "blocker": "exact compiler/source/build inputs and pinned reviewed maps are absent",
        },
        "evidence_profile": EVIDENCE_PROFILE,
    }
    contract["contract_sha256"] = contract_digest(contract)
    return contract


def validate_contract(contract, repo):
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ProbeError("probe contract schema changed")
    if contract.get("contract_id") != CONTRACT_ID:
        raise ProbeError("probe contract identity changed")
    if contract.get("contract_sha256") != contract_digest(contract):
        raise ProbeError("probe contract digest is stale")
    expected = build_contract(repo)
    if contract != expected:
        raise ProbeError("exact Linux API probe contract is stale")
    gate = contract.get("gate", {})
    if gate.get("credit_eligible") is not False or gate.get(
        "self_attestation_forbidden"
    ) is not True:
        raise ProbeError("probe contract permits self-attested gate credit")
    readiness = contract.get("readiness_without_exact_capture", {})
    if readiness != {
        "gate_status": "NOT_READY",
        "technical_complete": False,
        "credit_eligible": False,
        "blocker": "exact compiler/source/build inputs and pinned reviewed maps are absent",
    }:
        raise ProbeError("absent-input readiness must remain fail-closed")


def parse_config(path):
    values = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse config {0}: {1}".format(path, exc))
    for line in lines:
        match = CONFIG_LINE.match(line)
        if match:
            name, value = match.groups()
        else:
            match = CONFIG_UNSET.match(line)
            if not match:
                continue
            name, value = match.group(1), "n"
        if name in values:
            raise ProbeError("duplicate config symbol {0} in {1}".format(name, path))
        values[name] = value
    if not values:
        raise ProbeError("config has no symbols: {0}".format(path))
    return values


def config_capture(baseline, resolved, second, policy, repo):
    baseline = regular_file(baseline, "baseline config")
    resolved = regular_file(resolved, "resolved config")
    second = regular_file(second, "second-pass config")
    baseline_values = parse_config(baseline)
    resolved_values = parse_config(resolved)
    second_values = parse_config(second)
    baseline_sha = sha256_file(baseline)
    resolved_sha = sha256_file(resolved)
    second_sha = sha256_file(second)
    expected_baseline = policy.get("baseline", {}).get("sha256")
    if baseline_sha != expected_baseline:
        raise ProbeError("baseline config does not match Rocky lock")
    fragment_relative = Path(policy.get("delta", {}).get("fragment_path", ""))
    fragment = repository_file(repo, fragment_relative, "Rust config fragment")
    if sha256_file(fragment) != policy.get("delta", {}).get("fragment_sha256"):
        raise ProbeError("Rust config fragment digest changed")
    all_names = set(baseline_values) | set(resolved_values)
    changed = sorted(
        name
        for name in all_names
        if baseline_values.get(name, "<absent>")
        != resolved_values.get(name, "<absent>")
    )
    allowed = set(policy.get("delta", {}).get("allowed_symbols", []))
    allowed.update(
        policy.get("verification_evidence", {})
        .get("olddefconfig_delta", {})
        .get("generated_symbol_allowlist", [])
    )
    unexpected = sorted(set(changed) - allowed)
    assertions = []
    for row in policy.get("delta", {}).get("changes", []):
        assertions.append(
            {
                "symbol": row.get("symbol"),
                "expected": row.get("resolved"),
                "actual": resolved_values.get(row.get("symbol"), "<absent>"),
                "matches": resolved_values.get(row.get("symbol"), "<absent>")
                == row.get("resolved"),
            }
        )
    for row in policy.get("preserve", []):
        assertions.append(
            {
                "symbol": row.get("symbol"),
                "expected": row.get("value"),
                "actual": resolved_values.get(row.get("symbol"), "<absent>"),
                "matches": resolved_values.get(row.get("symbol"), "<absent>")
                == row.get("value"),
            }
        )
    exact = (
        resolved_sha == second_sha
        and resolved_values == second_values
        and not unexpected
        and all(row["matches"] for row in assertions)
    )
    return {
        "baseline": dict(file_record(baseline), path_role="locked Rocky baseline"),
        "fragment": dict(file_record(fragment), path=str(fragment_relative)),
        "resolved": dict(file_record(resolved), path_role="first olddefconfig pass"),
        "second_pass": dict(file_record(second), path_role="second olddefconfig pass"),
        "changed_symbols": changed,
        "allowed_changed_symbols": sorted(allowed),
        "unexpected_changed_symbols": unexpected,
        "assertions": assertions,
        "idempotent": resolved_sha == second_sha and resolved_values == second_values,
        "exact_policy_match": exact,
        "selected_config_sha256": resolved_sha,
    }


def safe_member_name(name, root):
    normalized = name.rstrip("/")
    if not normalized or normalized.startswith("/") or "\\" in normalized:
        raise ProbeError("unsafe archive member: {0}".format(name))
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ProbeError("unsafe archive member: {0}".format(name))
    if parts[0] != root:
        raise ProbeError("archive member escapes locked root: {0}".format(name))
    return parts


def validate_archive(archive, target):
    archive = regular_file(archive, "Linux source archive")
    if archive.name != target["source_archive_filename"]:
        raise ProbeError("Linux source archive filename changed")
    if archive.stat().st_size != target["source_archive_bytes"]:
        raise ProbeError("Linux source archive size changed")
    if sha256_file(archive) != target["source_archive_sha256"]:
        raise ProbeError("Linux source archive digest changed")
    root = target["source_archive_root"]
    try:
        stream = tarfile.open(str(archive), "r:xz")
    except (IOError, OSError, tarfile.TarError) as exc:
        raise ProbeError("cannot open Linux source archive: {0}".format(exc))
    with stream:
        members = stream.getmembers()
        if not members:
            raise ProbeError("Linux source archive is empty")
        for member in members:
            safe_member_name(member.name, root)
            if member.issym() or member.islnk():
                link = member.linkname
                if link.startswith("/") or "\\" in link:
                    raise ProbeError("unsafe archive link: {0}".format(member.name))
                combined = os.path.normpath(
                    os.path.join(os.path.dirname(member.name), link)
                )
                safe_member_name(combined, root)
            if not (
                member.isfile()
                or member.isdir()
                or member.issym()
                or member.islnk()
            ):
                raise ProbeError("unsupported archive member type: {0}".format(member.name))
    return archive


def tree_manifest(root):
    root = root.resolve()
    if not root.is_dir() or root.is_symlink():
        raise ProbeError("source tree is missing or a symlink: {0}".format(root))
    rows = []
    for directory, names, files in os.walk(str(root), followlinks=False):
        names.sort()
        files.sort()
        base = Path(directory)
        for name in list(names) + files:
            path = base / name
            relative = str(path.relative_to(root))
            if path.is_symlink():
                rows.append(
                    {"kind": "symlink", "path": relative, "target": os.readlink(str(path))}
                )
            elif path.is_file():
                rows.append(
                    {
                        "kind": "file",
                        "path": relative,
                        "bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
    rows.sort(key=lambda row: (row["path"], row["kind"]))
    return rows


def locate_asset(asset_root, logical_path):
    basename = Path(logical_path).name
    matches = [path for path in asset_root.rglob(basename) if path.is_file()]
    if len(matches) != 1:
        raise ProbeError(
            "expected one source asset {0}, found {1}".format(basename, len(matches))
        )
    return regular_file(matches[0], "source asset " + basename)


def run_checked(argv, cwd):
    try:
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError("command failed to execute: {0}".format(exc))
    if completed.returncode != 0:
        raise ProbeError(
            "command failed ({0}): {1}".format(
                completed.returncode,
                completed.stderr.decode("utf-8", errors="replace")[-2000:],
            )
        )
    return completed


def source_capture(source_rpm, archive, source_root, asset_root, contract):
    source_rpm = regular_file(source_rpm, "source RPM")
    target = contract["target"]
    if source_rpm.name != target["source_rpm_filename"]:
        raise ProbeError("source RPM filename changed")
    if source_rpm.stat().st_size != target["source_rpm_bytes"]:
        raise ProbeError("source RPM size changed")
    if sha256_file(source_rpm) != target["source_rpm_sha256"]:
        raise ProbeError("source RPM digest changed")
    archive = validate_archive(archive, target)
    asset_root = asset_root.resolve()
    if not asset_root.is_dir() or asset_root.is_symlink():
        raise ProbeError("source asset directory is invalid")
    patch_records = []
    applied = []
    for row in contract["source_patch_contract"]["patches"]:
        path = locate_asset(asset_root, row["path"])
        record = {
            "path": row["path"],
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "applied": row["applied"],
            "empty": row["empty"],
        }
        if record["bytes"] != row["size"] or record["sha256"] != row["sha256"]:
            raise ProbeError("locked patch bytes changed: {0}".format(row["path"]))
        patch_records.append(record)
        if row["applied"] and not row["empty"]:
            applied.append(path)
    source_root = source_root.resolve()
    actual_rows = tree_manifest(source_root)
    with tempfile.TemporaryDirectory(prefix="rs001-source-") as temporary:
        temporary_root = Path(temporary)
        with tarfile.open(str(archive), "r:xz") as stream:
            stream.extractall(str(temporary_root))
        expected_root = temporary_root / target["source_archive_root"]
        patch_binary = shutil.which("patch")
        if not patch_binary:
            raise ProbeError("patch is required for exact source replay")
        for path in applied:
            run_checked(
                [
                    patch_binary,
                    "-p1",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "--no-backup-if-mismatch",
                    "-i",
                    str(path),
                ],
                expected_root,
            )
        expected_rows = tree_manifest(expected_root)
    if actual_rows != expected_rows:
        limit = min(len(actual_rows), len(expected_rows))
        mismatch = next(
            (
                index
                for index in range(limit)
                if actual_rows[index] != expected_rows[index]
            ),
            limit,
        )
        raise ProbeError(
            "patched source tree differs from locked replay at row {0}; actual={1}, expected={2}".format(
                mismatch,
                actual_rows[mismatch] if mismatch < len(actual_rows) else "<missing>",
                expected_rows[mismatch] if mismatch < len(expected_rows) else "<missing>",
            )
        )
    tree_sha = sha256_bytes(canonical_bytes(actual_rows))
    return {
        "source_rpm": dict(file_record(source_rpm), filename=source_rpm.name),
        "source_archive": dict(file_record(archive), filename=archive.name),
        "patches": patch_records,
        "patched_tree_file_count": len(actual_rows),
        "patched_tree_manifest_sha256": tree_sha,
        "exact_locked_replay": True,
    }


def parse_module_symvers(path):
    path = regular_file(path, "Module.symvers")
    symbols = defaultdict(list)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse Module.symvers: {0}".format(exc))
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        fields = line.split("\t") if "\t" in line else line.split()
        if len(fields) < 4 or not fields[1]:
            raise ProbeError("malformed Module.symvers line {0}".format(number))
        row = {
            "crc": fields[0],
            "symbol": fields[1],
            "provider": fields[2],
            "export_class": fields[3],
            "namespace": fields[4] if len(fields) >= 5 else "",
        }
        symbols[row["symbol"]].append(row)
    if not symbols:
        raise ProbeError("Module.symvers contains no symbols")
    return path, symbols


def parse_system_map(path):
    path = regular_file(path, "System.map")
    symbols = defaultdict(list)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse System.map: {0}".format(exc))
    for number, line in enumerate(lines, 1):
        fields = line.split()
        if len(fields) < 3:
            if line.strip():
                raise ProbeError("malformed System.map line {0}".format(number))
            continue
        address, kind, symbol = fields[:3]
        if not re.match(r"^[0-9a-fA-F]+$", address) or len(kind) != 1:
            raise ProbeError("malformed System.map line {0}".format(number))
        symbols[symbol].append({"address": address.lower(), "type": kind})
    if not symbols:
        raise ProbeError("System.map contains no symbols")
    return path, symbols


def rust_bindings(path):
    path = regular_file(path, "generated Rust bindings")
    try:
        text = path.read_text(encoding="utf-8")
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise ProbeError("cannot parse generated Rust bindings: {0}".format(exc))
    names = sorted(set(match.group(1) for match in RUST_BINDING.finditer(text)))
    if not names:
        raise ProbeError("generated Rust bindings expose no public functions/statics")
    return path, set(names), sha256_bytes(canonical_bytes(names))


def tool_capture():
    rows = []
    for probe_id, command in TOOL_PROBES:
        executable = command[0]
        found = executable if os.path.isabs(executable) else shutil.which(executable)
        if not found:
            rows.append(
                {
                    "id": probe_id,
                    "command": list(command),
                    "status": "missing",
                    "path": None,
                    "sha256": None,
                    "exit_code": None,
                    "stdout_sha256": None,
                    "stderr_sha256": None,
                    "version_excerpt": None,
                    "rpm_owner": None,
                    "rpm_owner_query_sha256": None,
                }
            )
            continue
        path = Path(found).resolve()
        if not path.is_file():
            raise ProbeError("tool is not a regular file: {0}".format(found))
        try:
            completed = subprocess.run(
                list(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            stdout = b""
            stderr = str(exc).encode("utf-8")
            exit_code = -1
        combined = (stdout + b"\n" + stderr).decode("utf-8", errors="replace")
        rpm_owner = None
        rpm_owner_query = b""
        rpm_binary = shutil.which("rpm")
        if rpm_binary:
            try:
                owner = subprocess.run(
                    [rpm_binary, "-qf", str(path), "--qf", "%{NEVRA}\\n"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
                rpm_owner_query = owner.stdout + b"\n" + owner.stderr
                if owner.returncode == 0:
                    rpm_owner = owner.stdout.decode(
                        "utf-8", errors="replace"
                    ).strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                rpm_owner_query = str(exc).encode("utf-8")
        rows.append(
            {
                "id": probe_id,
                "command": list(command),
                "status": "captured" if exit_code == 0 else "failed",
                "path": str(path),
                "sha256": sha256_file(path),
                "exit_code": exit_code,
                "stdout_sha256": sha256_bytes(stdout),
                "stderr_sha256": sha256_bytes(stderr),
                "version_excerpt": combined[:500],
                "rpm_owner": rpm_owner,
                "rpm_owner_query_sha256": sha256_bytes(rpm_owner_query),
            }
        )
    return rows


def read_os_release():
    path = Path("/etc/os-release")
    if not path.is_file():
        return {"id": None, "version_id": None, "sha256": None}
    data = path.read_bytes()
    values = {}
    for line in data.decode("utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return {
        "id": values.get("ID"),
        "version_id": values.get("VERSION_ID"),
        "sha256": sha256_bytes(data),
    }


def optional_pinned_map(path, pin, label):
    if path is None:
        return None, {"status": "missing", "sha256": None, "trusted": False}
    path = regular_file(path, label)
    digest = sha256_file(path)
    value = read_json(path)
    trusted = isinstance(pin, str) and HEX64.match(pin) and digest == pin
    return value, {"status": "captured", "sha256": digest, "trusted": trusted}


def per_need_rows(needs, symvers, system_map, bindings, config_sha, maps, pins):
    config_map, context_map, abstraction_map = maps
    config_pin, context_pin, abstraction_pin = pins
    rows = []
    for need in needs:
        need_id = need["id"]
        symbol = need["symbol"]
        kind = need["lookup_kind"]
        exports = sorted(
            symvers.get(symbol, []),
            key=lambda row: (
                row["provider"], row["export_class"], row["namespace"], row["crc"]
            ),
        )
        map_rows = sorted(
            system_map.get(symbol, []), key=lambda row: (row["type"], row["address"])
        )
        if exports:
            availability = "exported"
        elif map_rows:
            availability = "present_unexported"
        else:
            availability = "absent_from_selected_build"
        config_entry = (
            config_map.get("requirements", {}).get(need_id)
            if isinstance(config_map, dict)
            else None
        )
        context_entry = (
            context_map.get("contexts", {}).get(need_id)
            if isinstance(context_map, dict)
            else None
        )
        abstraction_entry = (
            abstraction_map.get("abstractions", {}).get(need_id)
            if isinstance(abstraction_map, dict)
            else None
        )
        config_resolved = config_pin and isinstance(config_entry, dict)
        context_resolved = context_pin and isinstance(context_entry, dict)
        abstraction_resolved = abstraction_pin and isinstance(abstraction_entry, dict)
        direct_binding = symbol in bindings
        if kind == "dynamic_kallsyms":
            rust_status = (
                "reviewed_replacement"
                if abstraction_resolved
                else "private_lookup_retirement_unresolved"
            )
            disposition = "retire_dynamic_lookup"
        else:
            rust_status = (
                "generated_binding"
                if direct_binding
                else "reviewed_abstraction"
                if abstraction_resolved
                else "rust_callable_surface_unresolved"
            )
            disposition = "direct_or_reviewed_rust_api"
        rows.append(
            {
                "id": need_id,
                "symbol": symbol,
                "lookup_kind": kind,
                "consuming_modules": need["owner"]["consuming_modules"],
                "availability": {
                    "status": availability,
                    "system_map_entries": map_rows,
                },
                "export": {
                    "status": (
                        "unique"
                        if len(exports) == 1
                        else "absent"
                        if not exports
                        else "ambiguous"
                    ),
                    "entries": exports,
                },
                "configuration": {
                    "selected_config_sha256": config_sha,
                    "status": (
                        "reviewed_requirements_pinned"
                        if config_resolved
                        else "selected_config_only_requirements_unresolved"
                    ),
                    "reviewed_requirement": config_entry if config_resolved else None,
                },
                "rust_callable": {
                    "generated_binding": direct_binding,
                    "status": rust_status,
                    "reviewed_abstraction": (
                        abstraction_entry if abstraction_resolved else None
                    ),
                },
                "call_context": {
                    "status": (
                        "reviewed_contexts_pinned"
                        if context_resolved
                        else "compiler_backed_context_unresolved"
                    ),
                    "reviewed_context": context_entry if context_resolved else None,
                },
                "production_disposition": disposition,
            }
        )
    return rows


def build_evidence(args, repo, contract):
    needs_manifest = read_json(repository_file(repo, NEEDS_PATH, "Linux API needs"))
    needs = validate_needs_manifest(needs_manifest)
    source_lock = read_json(repository_file(repo, SOURCE_LOCK_PATH, "source lock"))
    config_policy = read_json(
        repository_file(repo, CONFIG_POLICY_PATH, "config policy")
    )
    toolchain_lock = read_json(
        repository_file(repo, TOOLCHAIN_LOCK_PATH, "toolchain lock")
    )
    source = source_capture(
        args.source_rpm,
        args.source_archive,
        args.source_root,
        args.source_assets,
        contract,
    )
    config = config_capture(
        args.baseline_config,
        args.resolved_config,
        args.second_pass_config,
        config_policy,
        repo,
    )
    symvers_path, symvers = parse_module_symvers(args.module_symvers)
    system_map_path, system_map = parse_system_map(args.system_map)
    bindings_path, bindings, binding_set_sha = rust_bindings(args.rust_bindings)
    pins = contract["reviewed_map_pins"]
    config_map, config_map_record = optional_pinned_map(
        args.config_requirements,
        pins["config_requirements_sha256"],
        "config requirements map",
    )
    context_map, context_map_record = optional_pinned_map(
        args.consumer_contexts,
        pins["consumer_contexts_sha256"],
        "consumer context map",
    )
    abstraction_map, abstraction_map_record = optional_pinned_map(
        args.rust_abstractions,
        pins["rust_abstractions_sha256"],
        "Rust abstraction map",
    )
    rows = per_need_rows(
        needs,
        symvers,
        system_map,
        bindings,
        config["selected_config_sha256"],
        (config_map, context_map, abstraction_map),
        (
            config_map_record["trusted"],
            context_map_record["trusted"],
            abstraction_map_record["trusted"],
        ),
    )
    tools = tool_capture()
    counts = {
        "availability": dict(sorted(Counter(row["availability"]["status"] for row in rows).items())),
        "export": dict(sorted(Counter(row["export"]["status"] for row in rows).items())),
        "configuration": dict(sorted(Counter(row["configuration"]["status"] for row in rows).items())),
        "rust_callable": dict(sorted(Counter(row["rust_callable"]["status"] for row in rows).items())),
        "call_context": dict(sorted(Counter(row["call_context"]["status"] for row in rows).items())),
    }
    blockers = []
    if source_lock.get("gate", {}).get("credit_eligible") is not True:
        blockers.append(
            "Rocky source acquisition/signature/license evidence is not independently gate-ready"
        )
    if not config["exact_policy_match"]:
        blockers.append("selected config does not exactly satisfy the locked delta/preservation policy")
    if config_policy.get("gate", {}).get("credit_eligible") is not True:
        blockers.append(
            "the resolved config is not yet registered as the exact Rocky RPM production config"
        )
    closure = toolchain_lock.get("closure", {})
    if closure.get("status") != "verified" or closure.get("all_archives_verified") is not True:
        blockers.append("exact archived and signature-verified toolchain closure is missing")
    missing_tools = [row["id"] for row in tools if row["status"] != "captured"]
    if missing_tools:
        blockers.append("required tool probes are missing or failed: " + ",".join(missing_tools))
    for label, record in (
        ("per-need CONFIG requirements", config_map_record),
        ("compiler-backed consumer contexts", context_map_record),
        ("reviewed Rust abstractions", abstraction_map_record),
    ):
        if not record["trusted"]:
            blockers.append(label + " are not pinned by the contract")
    unavailable = [
        row["id"]
        for row in rows
        if row["lookup_kind"] == "module_import"
        and row["availability"]["status"] != "exported"
    ]
    if unavailable:
        blockers.append(
            "{0} imported APIs are not exported by the selected build".format(
                len(unavailable)
            )
        )
    unresolved_rust = [
        row["id"]
        for row in rows
        if row["rust_callable"]["status"]
        in (
            "rust_callable_surface_unresolved",
            "private_lookup_retirement_unresolved",
        )
    ]
    if unresolved_rust:
        blockers.append(
            "{0} needs lack a pinned Rust-callable/replacement disposition".format(
                len(unresolved_rust)
            )
        )
    blockers.append(
        "independent RS-001 review and immutable evidence registration are required; this capture cannot award gate credit"
    )
    head = args.github_head_sha or git_head(repo)
    if not HEX40.match(head):
        raise ProbeError("repository capture commit must be exact 40-hex")
    os_release = read_os_release()
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "profile": EVIDENCE_PROFILE,
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract["contract_sha256"],
        "capture_identity": {
            "repository_commit": head,
            "github_repository": args.github_repository,
            "github_run_id": args.github_run_id,
            "github_run_attempt": args.github_run_attempt,
        },
        "target": contract["target"],
        "inputs": {
            "frozen_needs_file_sha256": contract["frozen_needs"]["file_sha256"],
            "frozen_needs_manifest_sha256": contract["frozen_needs"]["manifest_sha256"],
            "source_lock_sha256": contract["repository_inputs"]["source_lock"]["sha256"],
            "config_policy_sha256": contract["repository_inputs"]["config_policy"]["sha256"],
            "toolchain_lock_sha256": contract["repository_inputs"]["toolchain_lock"]["sha256"],
            "patch_series_sha256": contract["repository_inputs"]["patch_series"]["sha256"],
            "rust_target_compatibility_patch_sha256s": [
                row["sha256"]
                for row in contract["repository_inputs"][
                    "rust_target_compatibility_patches"
                ]
            ],
        },
        "environment": {
            "architecture": platform.machine(),
            "os_release": os_release,
            "uname": platform.uname()._asdict(),
            "tools": tools,
        },
        "source": source,
        "configuration": config,
        "build_outputs": {
            "module_symvers": dict(file_record(symvers_path), symbol_count=len(symvers)),
            "system_map": dict(file_record(system_map_path), symbol_count=len(system_map)),
            "rust_bindings": dict(
                file_record(bindings_path),
                binding_count=len(bindings),
                binding_set_sha256=binding_set_sha,
            ),
            "kernel_release": args.kernel_release,
        },
        "reviewed_maps": {
            "config_requirements": config_map_record,
            "consumer_contexts": context_map_record,
            "rust_abstractions": abstraction_map_record,
        },
        "needs": rows,
        "coverage": {
            "need_count": len(rows),
            "need_ids_sha256": sha256_bytes(canonical_bytes([row["id"] for row in rows])),
            "by_status": counts,
        },
        "readiness": {
            "gate": "RS-001",
            "gate_status": "NOT_READY",
            "technical_complete": False,
            "credit_eligible": False,
            "review_required": True,
            "blockers": blockers,
        },
    }
    evidence["evidence_sha256"] = evidence_digest(evidence)
    validate_evidence(evidence, contract, needs_manifest)
    return evidence


def git_head(repo):
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError("cannot resolve repository commit: {0}".format(exc))
    value = completed.stdout.decode("ascii", errors="replace").strip()
    if completed.returncode != 0 or not HEX40.match(value):
        raise ProbeError("cannot resolve exact repository commit")
    return value


def validate_evidence(evidence, contract, needs_manifest):
    require_keys(
        evidence,
        {
            "schema_version",
            "profile",
            "contract_id",
            "contract_sha256",
            "capture_identity",
            "target",
            "inputs",
            "environment",
            "source",
            "configuration",
            "build_outputs",
            "reviewed_maps",
            "needs",
            "coverage",
            "readiness",
            "evidence_sha256",
        },
        "evidence",
    )
    if evidence["schema_version"] != SCHEMA_VERSION or evidence["profile"] != EVIDENCE_PROFILE:
        raise ProbeError("evidence schema/profile changed")
    if evidence["contract_id"] != CONTRACT_ID or evidence["contract_sha256"] != contract["contract_sha256"]:
        raise ProbeError("evidence is not bound to the exact contract")
    if evidence["evidence_sha256"] != evidence_digest(evidence):
        raise ProbeError("evidence digest is stale")
    if evidence["target"] != contract["target"]:
        raise ProbeError("evidence target diverges from the contract")
    expected_inputs = {
        "frozen_needs_file_sha256": contract["frozen_needs"]["file_sha256"],
        "frozen_needs_manifest_sha256": contract["frozen_needs"]["manifest_sha256"],
        "source_lock_sha256": contract["repository_inputs"]["source_lock"]["sha256"],
        "config_policy_sha256": contract["repository_inputs"]["config_policy"]["sha256"],
        "toolchain_lock_sha256": contract["repository_inputs"]["toolchain_lock"]["sha256"],
        "patch_series_sha256": contract["repository_inputs"]["patch_series"]["sha256"],
        "rust_target_compatibility_patch_sha256s": [
            row["sha256"]
            for row in contract["repository_inputs"][
                "rust_target_compatibility_patches"
            ]
        ],
    }
    if evidence["inputs"] != expected_inputs:
        raise ProbeError("evidence repository input bindings changed")
    identity = require_keys(
        evidence["capture_identity"],
        {
            "repository_commit",
            "github_repository",
            "github_run_id",
            "github_run_attempt",
        },
        "capture identity",
    )
    if not HEX40.match(str(identity["repository_commit"])):
        raise ProbeError("capture identity is not an exact commit")
    environment = require_keys(
        evidence["environment"],
        {"architecture", "os_release", "uname", "tools"},
        "capture environment",
    )
    if environment["architecture"] != "x86_64":
        raise ProbeError("capture architecture is not x86_64")
    os_release = environment["os_release"]
    if (
        not isinstance(os_release, dict)
        or os_release.get("id") != "rocky"
        or os_release.get("version_id") != "10.2"
        or not HEX64.match(str(os_release.get("sha256")))
    ):
        raise ProbeError("capture runtime is not hash-bound Rocky 10.2")
    tools = environment["tools"]
    if not isinstance(tools, list) or [row.get("id") for row in tools] != [
        row[0] for row in TOOL_PROBES
    ]:
        raise ProbeError("tool capture is incomplete or reordered")
    for tool in tools:
        require_keys(
            tool,
            {
                "id",
                "command",
                "status",
                "path",
                "sha256",
                "exit_code",
                "stdout_sha256",
                "stderr_sha256",
                "version_excerpt",
                "rpm_owner",
                "rpm_owner_query_sha256",
            },
            "tool capture",
        )
        if tool.get("status") not in ("captured", "failed", "missing"):
            raise ProbeError("tool capture status is invalid")
        if tool.get("status") == "captured" and (
            tool.get("exit_code") != 0
            or not HEX64.match(str(tool.get("sha256")))
            or not HEX64.match(str(tool.get("stdout_sha256")))
            or not HEX64.match(str(tool.get("stderr_sha256")))
        ):
            raise ProbeError("captured tool lacks immutable provenance")
        if tool.get("status") != "missing" and not HEX64.match(
            str(tool.get("rpm_owner_query_sha256"))
        ):
            raise ProbeError("tool RPM-owner query is not digest-bound")
    source = require_keys(
        evidence["source"],
        {
            "source_rpm",
            "source_archive",
            "patches",
            "patched_tree_file_count",
            "patched_tree_manifest_sha256",
            "exact_locked_replay",
        },
        "source evidence",
    )
    if source["exact_locked_replay"] is not True:
        raise ProbeError("source evidence is not an exact locked replay")
    if source["source_rpm"] != {
        "bytes": contract["target"]["source_rpm_bytes"],
        "sha256": contract["target"]["source_rpm_sha256"],
        "filename": contract["target"]["source_rpm_filename"],
    }:
        raise ProbeError("source RPM evidence diverges from lock")
    if source["source_archive"] != {
        "bytes": contract["target"]["source_archive_bytes"],
        "sha256": contract["target"]["source_archive_sha256"],
        "filename": contract["target"]["source_archive_filename"],
    }:
        raise ProbeError("source archive evidence diverges from lock")
    expected_patches = contract["source_patch_contract"]["patches"]
    if len(source["patches"]) != len(expected_patches):
        raise ProbeError("source patch evidence count changed")
    for actual, expected in zip(source["patches"], expected_patches):
        if actual != {
            "path": expected["path"],
            "bytes": expected["size"],
            "sha256": expected["sha256"],
            "applied": expected["applied"],
            "empty": expected["empty"],
        }:
            raise ProbeError("source patch evidence diverges from lock")
    if (
        not isinstance(source["patched_tree_file_count"], int)
        or source["patched_tree_file_count"] < 1
        or not HEX64.match(str(source["patched_tree_manifest_sha256"]))
    ):
        raise ProbeError("patched source tree evidence is malformed")
    configuration = evidence["configuration"]
    required_config = {
        "baseline",
        "fragment",
        "resolved",
        "second_pass",
        "changed_symbols",
        "allowed_changed_symbols",
        "unexpected_changed_symbols",
        "assertions",
        "idempotent",
        "exact_policy_match",
        "selected_config_sha256",
    }
    require_keys(configuration, required_config, "configuration evidence")
    if configuration["selected_config_sha256"] != configuration["resolved"].get(
        "sha256"
    ):
        raise ProbeError("selected config digest is not the resolved config")
    recomputed_config_exact = (
        configuration["idempotent"] is True
        and not configuration["unexpected_changed_symbols"]
        and isinstance(configuration["assertions"], list)
        and bool(configuration["assertions"])
        and all(row.get("matches") is True for row in configuration["assertions"])
    )
    if configuration["exact_policy_match"] is not recomputed_config_exact:
        raise ProbeError("configuration exactness result is stale")
    outputs = require_keys(
        evidence["build_outputs"],
        {"module_symvers", "system_map", "rust_bindings", "kernel_release"},
        "build outputs",
    )
    if not isinstance(outputs["kernel_release"], str) or not outputs["kernel_release"]:
        raise ProbeError("kernel release evidence is missing")
    for label, count_key in (
        ("module_symvers", "symbol_count"),
        ("system_map", "symbol_count"),
        ("rust_bindings", "binding_count"),
    ):
        record = outputs[label]
        if (
            not isinstance(record, dict)
            or not HEX64.match(str(record.get("sha256")))
            or not isinstance(record.get("bytes"), int)
            or record.get("bytes") < 1
            or not isinstance(record.get(count_key), int)
            or record.get(count_key) < 1
        ):
            raise ProbeError("{0} build evidence is malformed".format(label))
    if not HEX64.match(str(outputs["rust_bindings"].get("binding_set_sha256"))):
        raise ProbeError("Rust binding set digest is missing")
    reviewed_maps = evidence["reviewed_maps"]
    if set(reviewed_maps) != {
        "config_requirements",
        "consumer_contexts",
        "rust_abstractions",
    }:
        raise ProbeError("reviewed map evidence is malformed")
    pins = contract["reviewed_map_pins"]
    for label, pin_name in (
        ("config_requirements", "config_requirements_sha256"),
        ("consumer_contexts", "consumer_contexts_sha256"),
        ("rust_abstractions", "rust_abstractions_sha256"),
    ):
        record = reviewed_maps[label]
        expected_trust = (
            isinstance(pins[pin_name], str)
            and record.get("sha256") == pins[pin_name]
        )
        if record.get("trusted") is not expected_trust:
            raise ProbeError("reviewed map trust is not contract-derived")
    needs = validate_needs_manifest(needs_manifest)
    rows = evidence["needs"]
    if not isinstance(rows, list) or len(rows) != EXPECTED_NEED_COUNT:
        raise ProbeError("evidence must contain exactly 268 need rows")
    expected_ids = [need["id"] for need in needs]
    actual_ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if actual_ids != expected_ids or len(actual_ids) != len(set(actual_ids)):
        raise ProbeError("evidence need identities diverge from frozen manifest")
    for need, row in zip(needs, rows):
        require_keys(
            row,
            {
                "id",
                "symbol",
                "lookup_kind",
                "consuming_modules",
                "availability",
                "export",
                "configuration",
                "rust_callable",
                "call_context",
                "production_disposition",
            },
            "need evidence " + need["id"],
        )
        if (
            row["symbol"] != need["symbol"]
            or row["lookup_kind"] != need["lookup_kind"]
            or row["consuming_modules"] != need["owner"]["consuming_modules"]
        ):
            raise ProbeError("need evidence identity changed: " + need["id"])
        if row["configuration"].get("selected_config_sha256") != evidence[
            "configuration"
        ].get("selected_config_sha256"):
            raise ProbeError("need config binding changed: " + need["id"])
        exports = row["export"].get("entries")
        if not isinstance(exports, list):
            raise ProbeError("need export rows are malformed: " + need["id"])
        for export in exports:
            require_keys(
                export,
                {"crc", "symbol", "provider", "export_class", "namespace"},
                "export row",
            )
            if export["symbol"] != need["symbol"]:
                raise ProbeError("export row symbol changed: " + need["id"])
        map_rows = row["availability"].get("system_map_entries")
        if not isinstance(map_rows, list):
            raise ProbeError("System.map rows are malformed: " + need["id"])
        expected_availability = (
            "exported"
            if exports
            else "present_unexported"
            if map_rows
            else "absent_from_selected_build"
        )
        expected_export = (
            "unique" if len(exports) == 1 else "absent" if not exports else "ambiguous"
        )
        if (
            row["availability"].get("status") != expected_availability
            or row["export"].get("status") != expected_export
        ):
            raise ProbeError("availability/export status is stale: " + need["id"])
        if pins["config_requirements_sha256"] is None and row["configuration"].get(
            "status"
        ) != "selected_config_only_requirements_unresolved":
            raise ProbeError("unpinned CONFIG review was trusted: " + need["id"])
        if pins["consumer_contexts_sha256"] is None and row["call_context"].get(
            "status"
        ) != "compiler_backed_context_unresolved":
            raise ProbeError("unpinned context review was trusted: " + need["id"])
    coverage = evidence["coverage"]
    if coverage.get("need_count") != len(rows):
        raise ProbeError("evidence coverage total is stale")
    if coverage.get("need_ids_sha256") != sha256_bytes(canonical_bytes(actual_ids)):
        raise ProbeError("evidence need ID digest is stale")
    expected_counts = {
        "availability": dict(sorted(Counter(row["availability"]["status"] for row in rows).items())),
        "export": dict(sorted(Counter(row["export"]["status"] for row in rows).items())),
        "configuration": dict(sorted(Counter(row["configuration"]["status"] for row in rows).items())),
        "rust_callable": dict(sorted(Counter(row["rust_callable"]["status"] for row in rows).items())),
        "call_context": dict(sorted(Counter(row["call_context"]["status"] for row in rows).items())),
    }
    if coverage.get("by_status") != expected_counts:
        raise ProbeError("evidence status coverage is stale")
    readiness = evidence["readiness"]
    if (
        readiness.get("gate") != "RS-001"
        or readiness.get("gate_status") != "NOT_READY"
        or readiness.get("technical_complete") is not False
        or readiness.get("credit_eligible") is not False
        or readiness.get("review_required") is not True
        or not isinstance(readiness.get("blockers"), list)
        or not readiness["blockers"]
    ):
        raise ProbeError("evidence overclaims RS-001 readiness")
    if not any("cannot award gate credit" in blocker for blocker in readiness["blockers"]):
        raise ProbeError("independent review blocker is missing")
    forbidden = re.compile(r"^(?:PASS|READY)$", re.IGNORECASE)
    for value in readiness.values():
        if isinstance(value, str) and forbidden.match(value):
            raise ProbeError("self-attested readiness is forbidden")


def add_capture_arguments(parser):
    parser.add_argument("--source-rpm", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--source-assets", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--baseline-config", type=Path, required=True)
    parser.add_argument("--resolved-config", type=Path, required=True)
    parser.add_argument("--second-pass-config", type=Path, required=True)
    parser.add_argument("--module-symvers", type=Path, required=True)
    parser.add_argument("--system-map", type=Path, required=True)
    parser.add_argument("--rust-bindings", type=Path, required=True)
    parser.add_argument("--kernel-release", required=True)
    parser.add_argument("--config-requirements", type=Path)
    parser.add_argument("--consumer-contexts", type=Path)
    parser.add_argument("--rust-abstractions", type=Path)
    parser.add_argument("--github-head-sha")
    parser.add_argument("--github-repository")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_subparsers(dest="mode")
    modes.required = True
    modes.add_parser("check-contract")
    modes.add_parser("update-contract")
    capture = modes.add_parser("capture")
    add_capture_arguments(capture)
    capture.add_argument("--output", type=Path, required=True)
    verify = modes.add_parser("verify-evidence")
    verify.add_argument("--evidence", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    repo = args.repo.resolve()
    try:
        if not repo.is_dir():
            raise ProbeError("repository is missing: {0}".format(repo))
        contract_path = repo / CONTRACT_PATH
        if args.mode == "update-contract":
            contract = build_contract(repo)
            atomic_write(contract_path, pretty(contract))
            print(
                "updated {0}: {1} frozen needs; readiness remains NOT_READY".format(
                    contract_path, contract["frozen_needs"]["need_count"]
                )
            )
            return 0
        contract = read_json(repository_file(repo, CONTRACT_PATH, "probe contract"))
        validate_contract(contract, repo)
        if args.mode == "check-contract":
            print(
                "RS-001 exact probe contract verified: 268 needs; NOT_READY without exact capture and pinned reviews"
            )
            return 0
        needs_manifest = read_json(
            repository_file(repo, NEEDS_PATH, "Linux API needs")
        )
        if args.mode == "capture":
            evidence = build_evidence(args, repo, contract)
            atomic_write(args.output.resolve(), pretty(evidence))
            print(
                "captured {0} exact-source API rows; RS-001 remains NOT_READY; sha256={1}".format(
                    len(evidence["needs"]), evidence["evidence_sha256"]
                )
            )
            return 0
        if args.mode == "verify-evidence":
            evidence = read_json(regular_file(args.evidence, "RS-001 evidence"))
            validate_evidence(evidence, contract, needs_manifest)
            print(
                "verified immutable RS-001 evidence structure: 268 needs; gate_status=NOT_READY; sha256={0}".format(
                    evidence["evidence_sha256"]
                )
            )
            return 0
        raise ProbeError("unsupported mode")
    except ProbeError as exc:
        print("RS-001 exact API probe error: {0}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
