#!/usr/bin/env python3
"""Replay the frozen Rust compiler-compatibility patch series."""

from __future__ import print_function

import os
import shutil
import subprocess
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
    REPO_ROOT
    / "host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0021-objtool-recognize-rust-1.92-panic-const.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0022-x86-pvh-annotate-noendbr.patch",
    REPO_ROOT
    / "host-kernel/rocky/patches/0023-rust-update-no-alloc-shim-marker-rust-1.92.patch",
)
PROJECT_PATCHES = (
    REPO_ROOT
    / "host-kernel/kbuild/patches/0001-drivers-misc-add-mckernel-rust-host-modules.patch",
    REPO_ROOT
    / "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch",
)
PREIMAGE = REPO_ROOT / "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs"
POSTIMAGE_SHA256 = "555ff4dff6548bb5f24087cdad737363b5694668aa462f77adfb3571498ec678"
CORE_PREIMAGE = REPO_ROOT / "scripts/tests/fixtures/rust-core-rocky-6.12"


class RustTargetCompatibilityPatchTests(unittest.TestCase):
    @staticmethod
    def seed_project_patch_preimages(root):
        makefile = root / "drivers/misc/Makefile"
        makefile.parent.mkdir(parents=True, exist_ok=True)
        makefile.write_text(
            "obj-$(CONFIG_NSM)\t\t+= nsm.o\n"
            "obj-$(CONFIG_MARVELL_CN10K_DPI)\t+= mrvl_cn10k_dpi.o\n"
            "obj-y\t\t\t\t+= keba/\n",
            encoding="utf-8",
        )
        (root / "drivers/misc/Kconfig").write_text(
            'source "drivers/misc/pvpanic/Kconfig"\n'
            'source "drivers/misc/mchp_pci1xxxx/Kconfig"\n'
            'source "drivers/misc/keba/Kconfig"\n'
            "endmenu\n",
            encoding="utf-8",
        )

    def test_exact_rocky_makefile_whitespace_is_explicitly_preserved(self):
        attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        fixture = "scripts/tests/fixtures/rust-core-rocky-6.12/Makefile"
        self.assertIn(fixture + " whitespace=-blank-at-eol", attributes)
        self.assertIn(
            b"RHEL_DRM_SUBLEVEL = \n",
            (REPO_ROOT / fixture).read_bytes(),
        )

    def test_every_patch_rejects_second_application(self):
        from scripts import linux_api_exact_probe as probe

        self.assertEqual(23, len(PATCHES))
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

    def test_patch_prefixes_are_unique_and_sequential(self):
        self.assertEqual(
            ["{0:04d}".format(index) for index in range(1, len(PATCHES) + 1)],
            [patch.name.split("-", 1)[0] for patch in PATCHES],
        )

    def test_project_retention_attributes_use_rust_1_89_semantics(self):
        expected_counts = {
            "ihk.rs": 3,
            "ihk_smp_x86_64.rs": 3,
            "mcctrl.rs": 2,
        }
        actual_total = 0
        for name, expected in expected_counts.items():
            source = (
                REPO_ROOT / "host-kernel/native-rust" / name
            ).read_text(encoding="utf-8")
            with self.subTest(source=name):
                self.assertEqual(expected, source.count("#[used(compiler)]"))
                self.assertEqual(0, source.count("#[used]"))
            actual_total += source.count("#[used(compiler)]")
        self.assertEqual(8, actual_total)

    def test_full_compatibility_then_project_series_preserves_bindings(self):
        from scripts import linux_api_exact_probe as probe

        command = ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "linux"
            shutil.copytree(str(CORE_PREIMAGE), str(root))
            (root / "scripts/generate_rust_target.rs").write_bytes(
                PREIMAGE.read_bytes()
            )
            self.seed_project_patch_preimages(root)
            for patch in PATCHES + PROJECT_PATCHES:
                probe.run_checked(command + [str(patch)], root)

            bindings = (
                root / "rust/bindings/bindings_helper.h"
            ).read_text(encoding="utf-8")
            miscdevice = "#include <linux/miscdevice.h>"
            moduleparam = "#include <linux/moduleparam.h>"
            self.assertEqual(1, bindings.count(miscdevice))
            self.assertEqual(1, bindings.count(moduleparam))
            self.assertLess(bindings.index(miscdevice), bindings.index(moduleparam))
            self.assertLess(
                bindings.index(moduleparam), bindings.index("#include <linux/phy.h>")
            )
            self.assertEqual(
                "dfdde6df9f8e8a38713cb210f7d2fe3a96fbbf19e60b262aa40de340d0059e6b",
                probe.sha256_file(root / "rust/bindings/bindings_helper.h"),
            )

    def test_stable_warning_policy_rejects_predecessor_order_mutations(self):
        from scripts import linux_api_exact_probe as probe

        command = ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i"]
        for successor, prefix_stop in ((15, 14), (17, 16)):
            with self.subTest(successor=PATCHES[successor].name):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "linux"
                    shutil.copytree(str(CORE_PREIMAGE), str(root))
                    for patch in PATCHES[2:prefix_stop]:
                        probe.run_checked(command + [str(patch)], root)
                    with self.assertRaises(probe.ProbeError):
                        probe.run_checked(command + [str(PATCHES[successor])], root)

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

    def test_core_and_bindings_series_applies_to_exact_rocky_preimages(self):
        from scripts import linux_api_exact_probe as probe

        for relative, digest in probe.RUST_CORE_COMPAT_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.RUST_BINDINGS_COMPAT_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.RUST_1_89_COMPAT_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.RUST_1_92_RECONCILIATION_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.CLANG_21_WARNING_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.CLANG_21_SOURCE_FIX_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.RUST_MISCDEVICE_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.RUST_OBJTOOL_NORETURN_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.PVH_OBJTOOL_COMPAT_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        for relative, digest in probe.RUST_ALLOC_SHIM_V2_FIXTURE_PREIMAGE_SHA256S:
            self.assertEqual(digest, probe.sha256_file(CORE_PREIMAGE / relative))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "linux"
            shutil.copytree(str(CORE_PREIMAGE), str(root))
            for patch in PATCHES[2:]:
                probe.run_checked(
                    ["patch", "-p1", "--batch", "--forward", "--fuzz=0", "-i", str(patch)],
                    root,
                )
            reconciled_paths = dict(probe.RUST_1_92_RECONCILIATION_POSTIMAGE_SHA256S)
            miscdevice_paths = dict(probe.RUST_MISCDEVICE_POSTIMAGE_SHA256S)
            allocator_paths = {
                row["path"]: row["sha256"]
                for row in probe.RUST_ALLOC_SHIM_V2_POSTIMAGES
            }
            for relative, digest in probe.RUST_CORE_COMPAT_POSTIMAGE_SHA256S:
                if relative not in reconciled_paths:
                    self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.RUST_BINDINGS_COMPAT_POSTIMAGE_SHA256S:
                self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.RUST_1_89_COMPAT_POSTIMAGE_SHA256S:
                if relative not in reconciled_paths:
                    self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.RUST_1_92_RECONCILIATION_POSTIMAGE_SHA256S:
                if relative not in miscdevice_paths:
                    self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.CLANG_21_WARNING_POSTIMAGE_SHA256S:
                self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.CLANG_21_SOURCE_FIX_POSTIMAGE_SHA256S:
                self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.RUST_MISCDEVICE_POSTIMAGE_SHA256S:
                if relative not in allocator_paths:
                    self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.RUST_OBJTOOL_NORETURN_POSTIMAGE_SHA256S:
                self.assertEqual(digest, probe.sha256_file(root / relative))
            for relative, digest in probe.PVH_OBJTOOL_COMPAT_POSTIMAGE_SHA256S:
                self.assertEqual(digest, probe.sha256_file(root / relative))
            for row in probe.RUST_ALLOC_SHIM_V2_POSTIMAGES:
                path = root / row["path"]
                self.assertEqual(row["sha256"], probe.sha256_file(path))
                self.assertEqual(row["size"], path.stat().st_size)
            ksm = (root / "mm/ksm.c").read_text(encoding="utf-8")
            advisor_show = ksm.split(
                "static ssize_t advisor_mode_show", 1
            )[1].split("static ssize_t advisor_mode_store", 1)[0]
            self.assertIn(
                "if (ksm_advisor == KSM_ADVISOR_SCAN_TIME)\n"
                "\t\toutput = \"none [scan-time]\";\n"
                "\telse\n"
                "\t\toutput = \"[none] scan-time\";",
                advisor_show,
            )
            self.assertNotIn(
                "else if (ksm_advisor == KSM_ADVISOR_SCAN_TIME)", advisor_show
            )
            cache = (root / "fs/netfs/fscache_cache.c").read_text(encoding="utf-8")
            cookie = (root / "fs/netfs/fscache_cookie.c").read_text(encoding="utf-8")
            self.assertIn(
                "fscache_cache_states[NR__FSCACHE_CACHE_STATE] __nonstring",
                cache,
            )
            self.assertIn(
                "fscache_cookie_states[FSCACHE_COOKIE_STATE__NR] __nonstring",
                cookie,
            )
            aescfb = (root / "lib/crypto/aescfb.c").read_text(encoding="utf-8")
            aesgcm = (root / "lib/crypto/aesgcm.c").read_text(encoding="utf-8")
            self.assertEqual(4, aescfb.count("__nonstring"))
            self.assertEqual(23, aesgcm.count("__nonstring"))
            ak8974 = (
                root / "drivers/iio/magnetometer/ak8974.c"
            ).read_text(encoding="utf-8")
            self.assertIn('static const char axis[] = "XYZ";', ak8974)
            self.assertIn('static const char pgaxis[] = "ZYZXYX";', ak8974)
            carl9170 = (
                root / "drivers/net/wireless/ath/carl9170/fw.c"
            ).read_text(encoding="utf-8")
            self.assertIn("otus_magic[4] __nonstring", carl9170)
            key = (root / "fs/cachefiles/key.c").read_text(encoding="utf-8")
            self.assertIn("cachefiles_charmap[64] __nonstring", key)
            magellan = (
                root / "drivers/input/joystick/magellan.c"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "static const unsigned char nibbles[16] __nonstring",
                magellan,
            )
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
            self.assertIn(
                "config RUSTC_HAS_UNNECESSARY_TRANSMUTES",
                (root / "init/Kconfig").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "#[cfg_attr(CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES, allow(unnecessary_transmutes))]",
                (root / "rust/bindings/lib.rs").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "#![cfg_attr(CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES, allow(unnecessary_transmutes))]",
                (root / "rust/uapi/lib.rs").read_text(encoding="utf-8"),
            )
            init_macros = (root / "rust/kernel/init/macros.rs").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                1,
                init_macros.count(
                    "#[allow(dead_code)]\n        trait MustNotImplDrop {}"
                ),
            )
            self.assertEqual(
                1,
                init_macros.count(
                    "#[allow(dead_code)]\n        #[allow(non_camel_case_types)]\n"
                    "        trait UselessPinnedDropImpl_you_need_to_specify_PinnedDrop {}"
                ),
            )
            self.assertIn(
                "-Zcrate-attr='feature(used_with_arg)'",
                makefile,
            )
            self.assertIn(
                "#![feature(used_with_arg)]",
                (root / "rust/kernel/lib.rs").read_text(encoding="utf-8"),
            )
            module = (root / "rust/macros/module.rs").read_text(encoding="utf-8")
            self.assertEqual(5, module.count("#[used(compiler)]"))
            self.assertNotIn("#[used]", module)
            self.assertIn(
                "rust_allowed_features := arbitrary_self_types,new_uninit,used_with_arg",
                (root / "scripts/Makefile.build").read_text(encoding="utf-8"),
            )
            kernel_lib = (root / "rust/kernel/lib.rs").read_text(encoding="utf-8")
            self.assertIn("#![feature(arbitrary_self_types)]", kernel_lib)
            self.assertNotIn("#![feature(receiver_trait)]", kernel_lib)
            for relative in ("rust/kernel/list/arc.rs", "rust/kernel/sync/arc.rs"):
                self.assertNotIn(
                    "core::ops::Receiver",
                    (root / relative).read_text(encoding="utf-8"),
                )
            self.assertNotIn(
                "BLK_MQ_F_SHOULD_MERGE",
                (root / "include/linux/blk-mq.h").read_text(encoding="utf-8"),
            )
            tag_set = (root / "rust/kernel/block/mq/tag_set.rs").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("BLK_MQ_F_SHOULD_MERGE", tag_set)
            self.assertIn("flags: 0,", tag_set)
            self.assertIn(
                "KBUILD_CFLAGS += $(call cc-disable-warning, "
                "default-const-init-unsafe)",
                (root / "scripts/Makefile.extrawarn").read_text(encoding="utf-8"),
            )
            top_makefile = (root / "Makefile").read_text(encoding="utf-8")
            extra_warnings = (root / "scripts/Makefile.extrawarn").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("unterminated-string-initialization", top_makefile)
            self.assertNotIn("CONFIG_CC_NO_STRINGOP_OVERFLOW", top_makefile)
            self.assertLess(
                extra_warnings.index("KBUILD_CFLAGS += -Wextra"),
                extra_warnings.index(
                    "$(call cc-disable-warning, unterminated-string-initialization)"
                ),
            )
            self.assertLess(
                extra_warnings.index("KBUILD_CFLAGS += -Wall"),
                extra_warnings.index("KBUILD_CFLAGS += -Wextra"),
            )
            self.assertIn(
                "$(call cc-disable-warning, stringop-overflow)", extra_warnings
            )
            self.assertIn(
                "$(call cc-disable-warning, frame-address)", extra_warnings
            )
            types = (root / "rust/kernel/types.rs").read_text(encoding="utf-8")
            self.assertIn("pub fn try_ffi_init<E>", types)
            bindings = (
                root / "rust/bindings/bindings_helper.h"
            ).read_text(encoding="utf-8")
            self.assertIn("#include <linux/miscdevice.h>", bindings)
            kernel_lib = (root / "rust/kernel/lib.rs").read_text(encoding="utf-8")
            self.assertIn("pub mod miscdevice;", kernel_lib)
            miscdevice = (
                root / "rust/kernel/miscdevice.rs"
            ).read_text(encoding="utf-8")
            self.assertIn("MISC_DYNAMIC_MINOR", miscdevice)
            self.assertIn("pub trait MiscDevice", miscdevice)
            self.assertNotIn("fn mmap", miscdevice)
            objtool = (root / "tools/objtool/check.c").read_text(encoding="utf-8")
            self.assertEqual(
                1,
                objtool.count(
                    "_4core9panicking11panic_const23panic_const_"
                ),
            )
            self.assertEqual(
                1,
                objtool.count(
                    "_4core9panicking11panic_const24panic_const_"
                ),
            )
            allocator = (
                root / "rust/kernel/alloc/allocator.rs"
            ).read_text(encoding="utf-8")
            self.assertEqual(
                1,
                allocator.count(
                    "fn __rust_no_alloc_shim_is_unstable_v2() {}"
                ),
            )
            self.assertEqual(1, allocator.count("#[rustc_std_internal_symbol]"))
            self.assertNotIn("static __rust_no_alloc_shim_is_unstable", allocator)
            self.assertEqual(
                1,
                kernel_lib.count(
                    "#![allow(internal_features)]\n#![feature(rustc_attrs)]",
                ),
            )

    def test_exact_rust_1_92_allocator_symbol_is_warning_clean_when_requested(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92")
        if not rustc:
            self.skipTest("MCKERNEL_RUSTC_1_92 is not configured")
        nm = shutil.which("llvm-nm") or shutil.which("nm")
        self.assertIsNotNone(nm, "an nm implementation is required")
        environment = os.environ.copy()
        environment["RUSTC_BOOTSTRAP"] = "1"
        version = subprocess.run(
            [rustc, "--version", "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=environment,
        )
        self.assertEqual(0, version.returncode, version.stderr)
        self.assertIn("release: 1.92.0\n", version.stdout)
        source = (
            "#![no_std]\n"
            "#![allow(internal_features)]\n"
            "#![feature(rustc_attrs)]\n\n"
            "#[rustc_std_internal_symbol]\n"
            "fn __rust_no_alloc_shim_is_unstable_v2() {}\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "allocator_shim.rs"
            object_path = root / "allocator_shim.o"
            source_path.write_text(source, encoding="utf-8")
            compile_result = subprocess.run(
                [
                    rustc,
                    "--crate-name",
                    "allocator_shim_probe",
                    "--crate-type",
                    "lib",
                    "--edition=2021",
                    "-Dwarnings",
                    "--emit=obj=" + str(object_path),
                    str(source_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=environment,
            )
            self.assertEqual(0, compile_result.returncode, compile_result.stderr)
            symbols = subprocess.run(
                [nm, "-C", "-g", "--defined-only", str(object_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=environment,
            )
            self.assertEqual(0, symbols.returncode, symbols.stderr)
            self.assertEqual(
                1,
                symbols.stdout.count(
                    "__rustc::__rust_no_alloc_shim_is_unstable_v2"
                ),
            )
            self.assertNotIn(
                "__rustc::__rust_no_alloc_shim_is_unstable\n",
                symbols.stdout,
            )

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

    def test_objtool_rust_1_92_patch_and_fixture_are_fail_closed(self):
        from scripts import linux_api_exact_probe as probe

        original = PATCHES[20].read_text(encoding="utf-8")
        for mutation in ("patch", "fixture"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    shutil.copytree(
                        str(REPO_ROOT / "host-kernel/rocky/patches"),
                        str(root / "host-kernel/rocky/patches"),
                    )
                    shutil.copytree(
                        str(CORE_PREIMAGE),
                        str(root / probe.RUST_CORE_COMPAT_FIXTURE_ROOT),
                    )
                    target_fixture = root / probe.RUST_COMPAT_FIXTURE_PATH
                    target_fixture.parent.mkdir(parents=True, exist_ok=True)
                    target_fixture.write_bytes(PREIMAGE.read_bytes())
                    if mutation == "patch":
                        patch = root / PATCHES[20].relative_to(REPO_ROOT)
                        patch.write_text(
                            original.replace(
                                "panic_const23panic_const_",
                                "panic_const22panic_const_",
                                1,
                            ),
                            encoding="utf-8",
                        )
                    else:
                        fixture = (
                            root
                            / probe.RUST_CORE_COMPAT_FIXTURE_ROOT
                            / "tools/objtool/check.c"
                        )
                        fixture.write_bytes(fixture.read_bytes() + b"\n")
                    with self.assertRaises(probe.ProbeError):
                        probe.rust_compatibility_patch_records(root)

    def test_allocator_shim_patch_and_fixture_are_fail_closed(self):
        from scripts import linux_api_exact_probe as probe

        original = PATCHES[22].read_text(encoding="utf-8")
        for mutation in ("patch", "fixture"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    shutil.copytree(
                        str(REPO_ROOT / "host-kernel/rocky/patches"),
                        str(root / "host-kernel/rocky/patches"),
                    )
                    shutil.copytree(
                        str(CORE_PREIMAGE),
                        str(root / probe.RUST_CORE_COMPAT_FIXTURE_ROOT),
                    )
                    target_fixture = root / probe.RUST_COMPAT_FIXTURE_PATH
                    target_fixture.parent.mkdir(parents=True, exist_ok=True)
                    target_fixture.write_bytes(PREIMAGE.read_bytes())
                    if mutation == "patch":
                        patch = root / PATCHES[22].relative_to(REPO_ROOT)
                        patch.write_text(
                            original.replace(
                                "+fn __rust_no_alloc_shim_is_unstable_v2() {}",
                                "+fn __rust_no_alloc_shim_is_unstable_v3() {}",
                                1,
                            ),
                            encoding="utf-8",
                        )
                    else:
                        fixture = (
                            root
                            / probe.RUST_CORE_COMPAT_FIXTURE_ROOT
                            / "rust/kernel/alloc/allocator.rs"
                        )
                        fixture.write_bytes(fixture.read_bytes() + b"\n")
                    with self.assertRaises(probe.ProbeError):
                        probe.rust_compatibility_patch_records(root)


if __name__ == "__main__":
    unittest.main()
