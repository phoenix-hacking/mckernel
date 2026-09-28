#!/usr/bin/env python3
"""Verify the preempt-protected x86 secondary-reset export patch."""

from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path(
    "/home/holden/mckernel-work/scratch/native-source/"
    "linux-6.12.0-211.44.1.el10_2"
)
PATCH = REPO_ROOT / (
    "host-kernel/kbuild/patches/"
    "0010-v2-x86-export-preempt-protected-secondary-reset.patch"
)


def helper_body(text):
    signature = "static void send_init_sequence(u32 phys_apicid)\n"
    start = text.find(signature)
    if start < 0:
        raise AssertionError("raw send_init_sequence helper not found")
    brace = text.index("{", start + len(signature))
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace:index + 1]
    raise AssertionError("raw send_init_sequence helper is unbalanced")


class X86PreemptProtectedSecondaryResetTests(unittest.TestCase):
    def test_exact_wrapper_applies_without_mutating_pinned_source(self):
        source = SOURCE_ROOT / "arch/x86/kernel/smpboot.c"
        header = SOURCE_ROOT / "arch/x86/include/asm/smp.h"
        self.assertTrue(source.is_file(), source)
        self.assertTrue(header.is_file(), header)
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        header_hash = hashlib.sha256(header.read_bytes()).hexdigest()
        original_source = source.read_text(encoding="utf-8")
        original_header = header.read_text(encoding="utf-8")
        original_body = helper_body(original_source)
        self.assertNotIn("native_reset_secondary_cpu_via_init", original_source)
        self.assertNotIn("native_reset_secondary_cpu_via_init", original_header)

        with tempfile.TemporaryDirectory(prefix="x86-reset-v2-") as directory:
            tree = Path(directory)
            for relative in (
                Path("arch/x86/kernel/smpboot.c"),
                Path("arch/x86/include/asm/smp.h"),
            ):
                target = tree / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(SOURCE_ROOT / relative), str(target))

            result = subprocess.run(
                [
                    "patch", "-p1", "--fuzz=0", "--batch", "--forward",
                    "-i", str(PATCH),
                ],
                cwd=str(tree),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)

            patched_source = (tree / "arch/x86/kernel/smpboot.c").read_text(
                encoding="utf-8"
            )
            patched_header = (tree / "arch/x86/include/asm/smp.h").read_text(
                encoding="utf-8"
            )
            self.assertEqual(helper_body(patched_source), original_body)
            self.assertIn(
                "void native_reset_secondary_cpu_via_init(u32 phys_apicid);",
                patched_header,
            )
            wrapper = re.search(
                r"void native_reset_secondary_cpu_via_init\(u32 phys_apicid\)\n"
                r"(?P<body>\{.*?\n\})\nEXPORT_SYMBOL_GPL",
                patched_source,
                re.DOTALL,
            )
            self.assertIsNotNone(wrapper)
            self.assertEqual(
                wrapper.group("body"),
                "{\n\tpreempt_disable();\n"
                "\tsend_init_sequence(phys_apicid);\n"
                "\tpreempt_enable();\n}",
            )
            self.assertEqual(
                patched_source.count(
                    "EXPORT_SYMBOL_GPL(native_reset_secondary_cpu_via_init);"
                ),
                1,
            )
            self.assertNotIn("EXPORT_SYMBOL_GPL(send_init_sequence);", patched_source)
            self.assertNotIn("startup_ipi", wrapper.group("body"))
            self.assertNotIn("smp", wrapper.group("body"))
            self.assertNotIn("apic_", wrapper.group("body"))
            self.assertNotIn("udelay", wrapper.group("body"))

        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_hash)
        self.assertEqual(hashlib.sha256(header.read_bytes()).hexdigest(), header_hash)


if __name__ == "__main__":
    unittest.main()
