#!/usr/bin/env python3
"""Parse the fail-closed Kconfig/Kbuild policy for native Rust host modules."""

from __future__ import print_function


MENU_TITLE = 'menu "McKernel native Rust host modules"'
MENU_DEPENDENCIES = (
    "RUST",
    "X86_64",
    "MODULES && m",
)
SYMBOLS = (
    "MCKERNEL_IHK_RUST",
    "MCKERNEL_IHK_SMP_X86_64_RUST",
    "MCKERNEL_MCCTRL_RUST",
)
PROVIDER = SYMBOLS[0]
PROMPTS = {
    SYMBOLS[0]: "McKernel IHK core host module (Rust)",
    SYMBOLS[1]: "McKernel IHK x86_64 SMP host module (Rust)",
    SYMBOLS[2]: "McKernel control host module (Rust)",
}
DEPENDENCIES = {
    SYMBOLS[0]: (),
    SYMBOLS[1]: (PROVIDER,),
    SYMBOLS[2]: (PROVIDER,),
}
EVIDENCE_FRAGMENT_ASSIGNMENTS = (
    "CONFIG_MODULES=y",
    "CONFIG_MCKERNEL_IHK_RUST=m",
    "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m",
    "CONFIG_MCKERNEL_MCCTRL_RUST=m",
)
EVIDENCE_FRAGMENT_LINES = (
    "# SPDX-License-Identifier: GPL-2.0-only",
    "# CONFIG fragment for compiler evidence only; it is not a production-ready",
    "# Rocky policy assertion and cannot award tracker credit.",
) + EVIDENCE_FRAGMENT_ASSIGNMENTS
KBUILD_LINES = (
    "# SPDX-License-Identifier: GPL-2.0",
    "",
    "# Staged as drivers/misc/mckernel/Kbuild in the selected Rocky kernel tree.",
    "# Linux Kbuild owns every Rust compiler and module linker invocation.",
    "",
    "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o",
    "obj-$(CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST) += ihk-smp-x86_64.o",
    "ihk-smp-x86_64-y := ihk_smp_x86_64.o",
    "obj-$(CONFIG_MCKERNEL_MCCTRL_RUST) += mcctrl.o",
)


class KconfigPolicyError(Exception):
    """Raised when the native Rust Kconfig escapes the locked grammar."""


def _is_ignorable(line):
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _next_directive(lines, cursor, label):
    while cursor < len(lines) and _is_ignorable(lines[cursor]):
        cursor += 1
    if cursor >= len(lines):
        raise KconfigPolicyError("missing {0}".format(label))
    return cursor, lines[cursor]


def _ascii_lf_lines(text, label):
    if not isinstance(text, str):
        raise KconfigPolicyError("{0} must be decoded text".format(label))
    for character in text:
        codepoint = ord(character)
        if character not in ("\t", "\n") and not 0x20 <= codepoint <= 0x7E:
            raise KconfigPolicyError(
                "{0} contains unsupported code point U+{1:04X}".format(
                    label, codepoint
                )
            )
    if text and not text.endswith("\n"):
        raise KconfigPolicyError("{0} must end with a newline".format(label))
    return text[:-1].split("\n") if text else []


def validate_native_rust_kconfig(text):
    """Validate one deliberately small Kconfig grammar and return its graph.

    The accepted surface contains one menu, three ordered ``config`` entries,
    and no other Kconfig directives.  ASCII help bodies and full-line comments
    are the only free-form text; config-looking text there is semantically
    inert and never parsed as a directive.  This makes hidden
    ``if``/``choice``/``source`` edges and implicit defaults structurally
    impossible instead of trying to enumerate every spelling.
    """

    lines = _ascii_lf_lines(text, "Kconfig")
    cursor, line = _next_directive(lines, 0, "menu declaration")
    if line != MENU_TITLE:
        raise KconfigPolicyError("menu declaration differs from the locked policy")
    cursor += 1

    for dependency in MENU_DEPENDENCIES:
        cursor, line = _next_directive(
            lines, cursor, "menu dependency {0}".format(dependency)
        )
        if line != "\tdepends on {0}".format(dependency):
            raise KconfigPolicyError(
                "menu dependencies must be RUST, X86_64, then MODULES && m"
            )
        cursor += 1

    for symbol in SYMBOLS:
        cursor, line = _next_directive(lines, cursor, "config {0}".format(symbol))
        if line != "config {0}".format(symbol):
            raise KconfigPolicyError(
                "config entries must be exactly the three locked symbols in provider-first order"
            )
        cursor += 1

        cursor, line = _next_directive(lines, cursor, symbol + " tristate")
        if line != '\ttristate "{0}"'.format(PROMPTS[symbol]):
            raise KconfigPolicyError("{0} must have exactly one prompted tristate".format(symbol))
        cursor += 1

        for dependency in DEPENDENCIES[symbol]:
            cursor, line = _next_directive(lines, cursor, symbol + " dependency")
            if line != "\tdepends on {0}".format(dependency):
                raise KconfigPolicyError(
                    "{0} must depend only on {1}".format(symbol, dependency)
                )
            cursor += 1

        cursor, line = _next_directive(lines, cursor, symbol + " help")
        if line != "\thelp":
            if DEPENDENCIES[symbol]:
                detail = "must depend only on {0} and then provide help".format(PROVIDER)
            else:
                detail = "must have no symbol-level dependencies and then provide help"
            raise KconfigPolicyError("{0} {1}".format(symbol, detail))
        cursor += 1

        help_lines = 0
        terminator = (
            "config {0}".format(SYMBOLS[SYMBOLS.index(symbol) + 1])
            if symbol != SYMBOLS[-1]
            else "endmenu"
        )
        while cursor < len(lines):
            line = lines[cursor]
            if line == terminator:
                break
            if _is_ignorable(line):
                cursor += 1
                continue
            if not line.startswith("\t  ") or not line.strip():
                raise KconfigPolicyError(
                    "{0} contains a forbidden or misplaced Kconfig directive".format(symbol)
                )
            help_lines += 1
            cursor += 1
        if not help_lines:
            raise KconfigPolicyError("{0} must have a non-empty help body".format(symbol))

    cursor, line = _next_directive(lines, cursor, "endmenu")
    if line != "endmenu":
        raise KconfigPolicyError("extra or nested Kconfig directives are forbidden")
    cursor += 1
    while cursor < len(lines) and _is_ignorable(lines[cursor]):
        cursor += 1
    if cursor != len(lines):
        raise KconfigPolicyError("content after endmenu is forbidden")

    return {
        "dependencies": dict((symbol, DEPENDENCIES[symbol]) for symbol in SYMBOLS),
        "menu_dependencies": MENU_DEPENDENCIES,
        "prompts": dict((symbol, PROMPTS[symbol]) for symbol in SYMBOLS),
        "symbols": SYMBOLS,
    }


def validate_native_rust_evidence_fragment(text):
    """Require the exact module prerequisite and three module selections."""

    lines = _ascii_lf_lines(text, "native Rust evidence fragment")
    if tuple(lines) != EVIDENCE_FRAGMENT_LINES:
        raise KconfigPolicyError(
            "evidence fragment must contain only the three locked header comments, CONFIG_MODULES=y, and the three ordered =m selections"
        )
    return EVIDENCE_FRAGMENT_ASSIGNMENTS


def validate_native_rust_kbuild(text):
    """Require the exact comment-safe three-module Kbuild authority."""

    lines = _ascii_lf_lines(text, "native Rust Kbuild")
    if tuple(lines) != KBUILD_LINES:
        raise KconfigPolicyError(
            "Kbuild must contain only the locked header and ordered three-module graph"
        )
    return tuple(line for line in KBUILD_LINES if line.startswith(("obj-", "ihk-")))
