from __future__ import print_function

import os
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import native_rust_kconfig_policy as policy


KCONFIG = os.path.join(REPO_ROOT, "host-kernel", "kbuild", "Kconfig")
KBUILD = os.path.join(REPO_ROOT, "host-kernel", "kbuild", "Kbuild.in")
EVIDENCE_FRAGMENT = os.path.join(
    REPO_ROOT, "host-kernel", "rocky", "configs", "native-rust-evidence.config"
)


class NativeRustKconfigPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(KCONFIG, "r") as stream:
            cls.original = stream.read()

    def rejected(self, text):
        with self.assertRaises(policy.KconfigPolicyError):
            policy.validate_native_rust_kconfig(text)

    def test_repository_policy_is_provider_first_and_module_only(self):
        result = policy.validate_native_rust_kconfig(self.original)
        self.assertEqual(policy.SYMBOLS, result["symbols"])
        self.assertEqual(
            ("RUST", "X86_64", "MODULES && m"), result["menu_dependencies"]
        )
        self.assertEqual((), result["dependencies"][policy.PROVIDER])
        for symbol in policy.SYMBOLS[1:]:
            self.assertEqual((policy.PROVIDER,), result["dependencies"][symbol])

    def test_repository_kbuild_is_exact_and_comment_safe(self):
        with open(KBUILD, "r") as stream:
            original = stream.read()
        self.assertEqual(
            (
                "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o",
                "obj-$(CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST) += ihk-smp-x86_64.o",
                "ihk-smp-x86_64-y := ihk_smp_x86_64.o",
                "obj-$(CONFIG_MCKERNEL_MCCTRL_RUST) += mcctrl.o",
            ),
            policy.validate_native_rust_kbuild(original),
        )
        marker = "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o\n"
        mutations = (
            original.replace(marker, "# suppress provider mapping \\\n" + marker, 1),
            original.replace(marker, marker.rstrip("\n") + " \\\n" + "ignored.o\n", 1),
            original.replace(marker, marker.replace(" += ihk.o", " += \\\n\tihk.o"), 1),
            original.replace(marker, marker + "obj-y += legacy.o\n", 1),
            original.replace("ihk.o\nobj-", "ihk.o \nobj-", 1),
            original.rstrip("\n"),
            original.replace("\n", "\r\n", 1),
            original.replace("Rocky kernel tree.", "Rocky\u202e kernel tree.", 1),
            original.replace("Rocky kernel tree.", "Rocky\x85 kernel tree.", 1),
        )
        for index, text in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(policy.KconfigPolicyError):
                    policy.validate_native_rust_kbuild(text)

    def test_menu_dependency_order_and_spelling_are_exact(self):
        mutations = (
            self.original.replace("\tdepends on RUST\n", "", 1),
            self.original.replace("\tdepends on X86_64\n", "", 1),
            self.original.replace("\tdepends on MODULES && m\n", "", 1),
            self.original.replace(
                "\tdepends on RUST\n\tdepends on X86_64\n",
                "\tdepends on X86_64\n\tdepends on RUST\n",
                1,
            ),
            self.original.replace("MODULES && m", "MODULES", 1),
            self.original.replace("MODULES && m", "MODULES && y", 1),
        )
        for index, text in enumerate(mutations):
            with self.subTest(index=index):
                self.rejected(text)

    def test_all_symbols_must_be_prompted_tristates(self):
        for symbol in policy.SYMBOLS:
            marker = "config {0}\n\ttristate ".format(symbol)
            with self.subTest(symbol=symbol):
                self.rejected(self.original.replace(marker, marker.replace("tristate", "bool"), 1))

    def test_prompts_are_exact_ascii_policy_text(self):
        self.rejected(
            self.original.replace(
                "McKernel IHK core host module (Rust)",
                "McKernel IHK provider host module (Rust)",
                1,
            )
        )
        self.rejected(
            self.original.replace(
                "McKernel IHK core host module (Rust)",
                "McKernel IHK core host module (Rüst)",
                1,
            )
        )

    def test_provider_has_no_symbol_dependency(self):
        marker = '\ttristate "McKernel IHK core host module (Rust)"\n'
        self.rejected(
            self.original.replace(marker, marker + "\tdepends on EXPERIMENTAL\n", 1)
        )

    def test_consumers_depend_only_on_provider(self):
        consumer_dependency = "\tdepends on MCKERNEL_IHK_RUST\n"
        self.rejected(self.original.replace(consumer_dependency, "", 1))
        self.rejected(
            self.original.replace(
                consumer_dependency,
                consumer_dependency + "\tdepends on EXPERIMENTAL\n",
                1,
            )
        )
        self.rejected(
            self.original.replace(
                consumer_dependency, "\tdepends on MCKERNEL_IHK_RUST && EXPERIMENTAL\n", 1
            )
        )

    def test_hidden_and_nested_control_surfaces_are_rejected(self):
        marker = "\nconfig MCKERNEL_IHK_RUST\n"
        directives = (
            "if EXPERIMENTAL",
            "choice",
            'menu "nested"',
            'menuconfig EXTRA',
            'source "drivers/misc/other/Kconfig"',
            'rsource "other/Kconfig"',
            'osource "optional/Kconfig"',
            'orsource "optional-relative/Kconfig"',
            "config EXTRA",
        )
        for directive in directives:
            with self.subTest(directive=directive):
                self.rejected(
                    self.original.replace(marker, "\n" + directive + marker, 1)
                )

    def test_implicit_and_visible_properties_are_rejected(self):
        marker = '\ttristate "McKernel IHK core host module (Rust)"\n'
        properties = (
            "default m",
            "def_bool y",
            "def_tristate m",
            "select EXPERIMENTAL",
            "imply EXPERIMENTAL",
            "visible if EXPERIMENTAL",
            "range 1 2",
            "option modules",
            'prompt "second prompt"',
        )
        for item in properties:
            with self.subTest(item=item):
                self.rejected(
                    self.original.replace(marker, marker + "\t" + item + "\n", 1)
                )

    def test_misplaced_or_empty_help_is_rejected(self):
        self.rejected(self.original.replace("\thelp\n", "", 1))
        self.rejected(
            self.original.replace(
                "\thelp\n\t  Build the native Rust-for-Linux IHK provider module.  This module\n",
                "\thelp\n",
                1,
            ).replace(
                "\t  contains no project-owned C implementation objects.\n", "", 1
            )
        )
        self.rejected(
            self.original.replace(
                "\t  Build the native Rust-for-Linux IHK provider module.  This module",
                "\tBuild the native Rust-for-Linux IHK provider module.  This module",
                1,
            )
        )

    def test_trailing_directives_and_noncanonical_bytes_are_rejected(self):
        self.rejected(self.original + "config EXTRA\n")
        self.rejected(self.original.rstrip("\n"))
        self.rejected(self.original.replace("\n", "\r\n", 1))
        self.rejected(self.original + "\x00")

    def test_controls_and_unicode_separators_cannot_hide_syntax(self):
        disallowed = [
            chr(codepoint)
            for codepoint in list(range(0x00, 0x20)) + list(range(0x7F, 0xA0))
            if codepoint not in (0x09, 0x0A)
        ]
        disallowed.extend(("\u2028", "\u2029", "\u202e"))
        positions = (
            ("# SPDX-License-Identifier: GPL-2.0", "# SPDX-License-Identifier: GPL-2.0{0}if EVIL"),
            ("McKernel IHK core host module (Rust)", "McKernel IHK core{0} host module (Rust)"),
            (
                "Build the native Rust-for-Linux IHK provider module.",
                "Build the native Rust-for-Linux IHK provider module.{0}source EVIL",
            ),
        )
        for character in disallowed:
            for marker, replacement in positions:
                with self.subTest(codepoint="U+{0:04X}".format(ord(character)), marker=marker):
                    self.rejected(
                        self.original.replace(marker, replacement.format(character), 1)
                    )

    def test_config_looking_comments_and_help_remain_semantically_inert(self):
        text = self.original.replace(
            "# SPDX-License-Identifier: GPL-2.0\n",
            "# config COMMENT_ONLY\n# if COMMENT_ONLY\n"
            "# SPDX-License-Identifier: GPL-2.0\n",
            1,
        )
        text = text.replace(
            "\t  Build the native Rust-for-Linux IHK provider module.  This module\n",
            "\t  config HELP_TEXT_ONLY\n"
            "\t  depends on HELP_TEXT_ONLY\n"
            "\t  Build the native Rust-for-Linux IHK provider module.  This module\n",
            1,
        )
        text = text + "# menuconfig COMMENT_AFTER_ENDMENU\n"
        result = policy.validate_native_rust_kconfig(text)
        self.assertEqual(policy.SYMBOLS, result["symbols"])

    def test_evidence_fragment_enables_modules_before_exact_module_selection(self):
        with open(EVIDENCE_FRAGMENT, "r") as stream:
            assignments = policy.validate_native_rust_evidence_fragment(stream.read())
        self.assertEqual(
            policy.EVIDENCE_FRAGMENT_ASSIGNMENTS,
            assignments,
        )

    def test_evidence_fragment_rejects_missing_reordered_or_non_module_values(self):
        with open(EVIDENCE_FRAGMENT, "r") as stream:
            original = stream.read()
        mutations = (
            original.replace("CONFIG_MODULES=y\n", "", 1),
            original.replace("CONFIG_MODULES=y", "CONFIG_MODULES=m", 1),
            original.replace("CONFIG_MCKERNEL_IHK_RUST=m", "CONFIG_MCKERNEL_IHK_RUST=y", 1),
            original.replace(
                "CONFIG_MCKERNEL_IHK_RUST=m\nCONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m\n",
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m\nCONFIG_MCKERNEL_IHK_RUST=m\n",
                1,
            ),
            original + "CONFIG_MCKERNEL_EXTRA_RUST=m\n",
            original + "CONFIG_MCKERNEL_IHK_RUST=m\n",
            original.replace("CONFIG_MODULES=y", "# CONFIG_MODULES=y", 1),
            original.replace("CONFIG_MODULES=y", " CONFIG_MODULES=y", 1),
            original.replace("CONFIG_MODULES=y", "CONFIG_MODULES=y ", 1),
            original.replace("CONFIG_MODULES=y", "\tCONFIG_MODULES=y", 1),
            original.replace("CONFIG_MODULES=y", "CONFIG_MODULES=y # accepted", 1),
        )
        for index, text in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(policy.KconfigPolicyError):
                    policy.validate_native_rust_evidence_fragment(text)

    def test_evidence_fragment_rejects_comment_substrings_and_non_ascii_controls(self):
        with open(EVIDENCE_FRAGMENT, "r") as stream:
            original = stream.read()
        comment_only = "# CONFIG_MODULES=y\n" + original.replace(
            "CONFIG_MODULES=y\n", "", 1
        )
        with self.assertRaises(policy.KconfigPolicyError):
            policy.validate_native_rust_evidence_fragment(comment_only)
        for character in ("\x00", "\x1f", "\x7f", "\x85", "\u2028", "\u202e"):
            with self.subTest(codepoint="U+{0:04X}".format(ord(character))):
                with self.assertRaises(policy.KconfigPolicyError):
                    policy.validate_native_rust_evidence_fragment(
                        original.replace("CONFIG_MODULES", "CONFIG" + character + "_MODULES", 1)
                    )

    def test_evidence_fragment_rejects_semantic_unset_rows_and_extra_comments(self):
        with open(EVIDENCE_FRAGMENT, "r") as stream:
            original = stream.read()
        symbols = (
            "MODULES",
            "MCKERNEL_IHK_RUST",
            "MCKERNEL_IHK_SMP_X86_64_RUST",
            "MCKERNEL_MCCTRL_RUST",
            "UNRELATED",
        )
        for symbol in symbols:
            unset = "# CONFIG_{0} is not set\n".format(symbol)
            mutations = (
                unset + original,
                original + unset,
                " " + unset + original,
            )
            for index, text in enumerate(mutations):
                with self.subTest(symbol=symbol, index=index):
                    with self.assertRaises(policy.KconfigPolicyError):
                        policy.validate_native_rust_evidence_fragment(text)
        for comment in ("# extra comment\n", "\n", " \n"):
            with self.subTest(comment=repr(comment)):
                with self.assertRaises(policy.KconfigPolicyError):
                    policy.validate_native_rust_evidence_fragment(original + comment)


if __name__ == "__main__":
    unittest.main()
