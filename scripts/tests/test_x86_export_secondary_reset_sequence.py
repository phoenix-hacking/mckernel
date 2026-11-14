#!/usr/bin/env python3
"""Apply and verify the focused x86 secondary-reset export patch."""

from pathlib import Path
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
PATCH = REPO_ROOT / "host-kernel/kbuild/patches/0010-x86-export-secondary-reset-sequence.patch"


class X86SecondaryResetExportTests(unittest.TestCase):
    def test_patch_applies_and_only_exports_reset_helper(self):
        source = SOURCE_ROOT / "arch/x86/kernel/smpboot.c"
        header = SOURCE_ROOT / "arch/x86/include/asm/smp.h"
        self.assertTrue(source.is_file(), source)
        self.assertTrue(header.is_file(), header)

        before = source.read_text(encoding="utf-8")
        body_match = re.search(
            r"static void send_init_sequence\(u32 phys_apicid\)\n"
            r"(?P<body>\{.*?\n\})\n\n/\*",
            before,
            re.DOTALL,
        )
        self.assertIsNotNone(body_match)
        original_body = body_match.group("body")

        with tempfile.TemporaryDirectory(prefix="x86-reset-export-") as directory:
            tree = Path(directory)
            for relative in (
                Path("arch/x86/kernel/smpboot.c"),
                Path("arch/x86/include/asm/smp.h"),
            ):
                target = tree / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(SOURCE_ROOT / relative), str(target))

            result = subprocess.run(
                ["patch", "-p1", "--batch", "--forward", "-i", str(PATCH)],
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
            self.assertIn("void send_init_sequence(u32 phys_apicid);", patched_header)
            self.assertIn("void send_init_sequence(u32 phys_apicid)", patched_source)
            self.assertNotIn("static void send_init_sequence", patched_source)
            self.assertEqual(patched_source.count("EXPORT_SYMBOL_GPL(send_init_sequence);"), 1)
            patched_body = re.search(
                r"void send_init_sequence\(u32 phys_apicid\)\n"
                r"(?P<body>\{.*?\n\})\nEXPORT_SYMBOL_GPL",
                patched_source,
                re.DOTALL,
            )
            self.assertIsNotNone(patched_body)
            self.assertEqual(patched_body.group("body"), original_body)


if __name__ == "__main__":
    unittest.main()
