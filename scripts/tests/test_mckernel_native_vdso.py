"""Actual native descriptor, publication and Linux clock arithmetic bodies."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


class NativeVdsoTests(unittest.TestCase):
    def run_checked(self, command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, str(command) + "\n" + result.stdout + result.stderr)
        print(result.stdout, end="", flush=True)
        return result.stdout

    def test_protocol_publication_and_clock_reader(self):
        rustc = shutil.which("rustc")
        if rustc is None:
            self.skipTest("Rust compiler unavailable")
        with tempfile.TemporaryDirectory(prefix="native-vdso-") as temporary:
            output = Path(temporary) / "protocol"
            self.run_checked([rustc, "--edition=2021", "--test", "-Dwarnings", "-O",
                              str(ROOT / "scripts/tests/fixtures/mckernel_native_vdso_compile.rs"),
                              "-o", str(output)])
            self.run_checked([str(output), "--test-threads=1", "--nocapture"])

    def test_pinned_linux_arithmetic_equivalence(self):
        location = os.environ.get("MCKERNEL_NATIVE_LINUX_SOURCE")
        if not location:
            self.skipTest("Exact configured Linux source must be provided explicitly")
        linux = Path(location)
        rustc, cc = shutil.which("rustc"), shutil.which("cc")
        self.assertIsNotNone(rustc)
        self.assertIsNotNone(cc)
        # Complete unmodified Linux function bodies, with only their scalar
        # declarations/attributes replaced for the standalone fixture. The
        # configured native target selects the original INT128 implementation.
        source = (linux / "arch/x86/include/asm/vdso/gettimeofday.h").read_text()
        math = (linux / "include/vdso/math64.h").read_text()
        c = """
#include <stdint.h>
#include <limits.h>
#undef __always_inline
#define __always_inline inline __attribute__((always_inline))
#define unlikely(x) __builtin_expect(!!(x), 0)
#define S64_MAX INT64_MAX
typedef uint64_t u64;
typedef uint32_t u32;
struct vdso_clock { u64 cycle_last, max_cycles; u32 mult, shift; };
"""
        c += function(math, "static __always_inline u64 mul_u64_u32_add_u64_shr(") + "\n"
        c += function(source, "static __always_inline u64 vdso_calc_ns(") + "\n"
        c += """
u64 reference_ns(u64 cycles, u64 last, u64 max, u32 mult, u32 shift, u64 base)
{
    const struct vdso_clock clock = {last, max, mult, shift};
    return vdso_calc_ns(&clock, cycles, base);
}
"""
        with tempfile.TemporaryDirectory(prefix="native-vdso-linux-") as temporary:
            directory = Path(temporary)
            (directory / "reference.c").write_text(c)
            reference = directory / "reference.o"
            self.run_checked([cc, "-O2", "-fPIC", "-Wall", "-Werror", "-c",
                              str(directory / "reference.c"), "-o", str(reference)])
            output = directory / "linux-clock"
            self.run_checked([rustc, "--edition=2021", "--test", "-Dwarnings", "-O",
                              str(ROOT / "scripts/tests/fixtures/mckernel_native_vdso_compile.rs"),
                              "--cfg", "linux_clock_reference", "-C", "link-arg=" + str(reference),
                              "-o", str(output)])
            self.assertIn("exact Linux clock cases=77824", self.run_checked(
                [str(output), "exact_pinned_linux_clock_arithmetic", "--nocapture"]))


if __name__ == "__main__":
    unittest.main()
