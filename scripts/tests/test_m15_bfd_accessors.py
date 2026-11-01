"""Isolated ABI/dispatch checks for the actual four Rust BFD adapters.

The callback/header fixture is an observation double, not the selected Rocky
BFD header/library. These checks establish adapter behavior only: they do not
qualify real BFD layouts, mcinspect/eclair consumers, or a native McKernel.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "executer/user"


HEADER = r"""
#ifndef TEST_BFD_H
#define TEST_BFD_H
#include <stdint.h>
typedef struct bfd bfd;
/* Only data consumed by the expanded typed witness use the pinned prefix.
 * Callback table/object positions below remain explicitly synthetic. */
typedef struct bfd_section { unsigned char prefix[48]; unsigned long vma; } asection;
typedef struct asymbol {
    void *the_bfd;
    const char *name;
    uintptr_t value;
    unsigned int flags;
    asection *section;
} asymbol;
typedef struct bfd_target {
    uintptr_t prefix[5];
    long (*_bfd_canonicalize_symtab)(bfd *, asymbol **);
    uintptr_t between[3];
    long (*_bfd_get_symtab_upper_bound)(bfd *);
} bfd_target;
struct bfd {
    uintptr_t prefix[3];
    const bfd_target *xvec;
    uintptr_t suffix[2];
};
#define bfd_get_symtab_upper_bound(b) ((b)->xvec->_bfd_get_symtab_upper_bound(b))
#define bfd_canonicalize_symtab(b, s) ((b)->xvec->_bfd_canonicalize_symtab((b), (s)))
#endif
"""


HARNESS = r"""
#include <bfd.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#define DECLARE(prefix) \
    long prefix##_bfd_get_symtab_upper_bound_bridge(bfd *); \
    long prefix##_bfd_canonicalize_symtab_bridge(bfd *, asymbol **)
DECLARE(mcinspect);
DECLARE(eclair);
DECLARE(reference_mcinspect);
DECLARE(reference_eclair);

static bfd *expected_bfd;
static asymbol **expected_location;
static asymbol symbol = { .value = 0xdeadbeef80000000UL };
static long callback_result;
static int observed_calls, observed_error, bad_arguments;
static long upper(bfd *object)
{
    ++observed_calls;
    bad_arguments |= object != expected_bfd;
    observed_error = 61;
    return callback_result;
}
static long canonicalize(bfd *object, asymbol **location)
{
    ++observed_calls;
    bad_arguments |= object != expected_bfd || location != expected_location;
    if (location)
        location[0] = &symbol;
    observed_error = 62;
    return callback_result;
}
typedef long (*upper_type)(bfd *);
typedef long (*canonicalize_type)(bfd *, asymbol **);
static const upper_type uppers[] = {
    mcinspect_bfd_get_symtab_upper_bound_bridge,
    eclair_bfd_get_symtab_upper_bound_bridge,
    reference_mcinspect_bfd_get_symtab_upper_bound_bridge,
    reference_eclair_bfd_get_symtab_upper_bound_bridge,
};
static const canonicalize_type canonicalizers[] = {
    mcinspect_bfd_canonicalize_symtab_bridge,
    eclair_bfd_canonicalize_symtab_bridge,
    reference_mcinspect_bfd_canonicalize_symtab_bridge,
    reference_eclair_bfd_canonicalize_symtab_bridge,
};
int main(void)
{
    const bfd_target target = {
        ._bfd_get_symtab_upper_bound = upper,
        ._bfd_canonicalize_symtab = canonicalize,
    };
    bfd object = { .xvec = &target };
    const long results[] = {0, -1, 0x100000001L, -0x100000001L, LONG_MAX, LONG_MIN};
    expected_bfd = &object;
    unsigned cases = 0;
    for (unsigned index = 0; index < 4; ++index) {
        for (unsigned result = 0; result < sizeof(results) / sizeof(results[0]); ++result) {
            callback_result = results[result];
            observed_calls = observed_error = bad_arguments = 0;
            if (uppers[index](&object) != callback_result ||
                observed_calls != 1 || observed_error != 61 || bad_arguments)
                return 10 + index;
            ++cases;
            for (unsigned null_location = 0; null_location < 2; ++null_location) {
                asymbol *table[] = {NULL};
                expected_location = null_location ? NULL : table;
                observed_calls = observed_error = bad_arguments = 0;
                if (canonicalizers[index](&object, expected_location) != callback_result ||
                    observed_calls != 1 || observed_error != 62 || bad_arguments ||
                    (!null_location && table[0] != &symbol))
                    return 20 + index;
                ++cases;
            }
        }
    }
    printf("%u C/Rust callback behavior cases passed\n", cases);
    return 0;
}
"""


class BfdAccessorTests(unittest.TestCase):
    def test_actual_rust_and_c_adapters_preserve_callback_abi(self):
        compiler = os.environ.get("CC") or shutil.which("gcc")
        rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        if not compiler or not rustc:
            self.skipTest("GCC and Rust compiler required")
        with tempfile.TemporaryDirectory(prefix="m15-bfd-accessors-") as directory:
            work = Path(directory)
            (work / "bfd.h").write_text(HEADER)
            # Run the actual layout-witness body against this deliberately
            # nonproduction header, with only its fixed header selector changed.
            witness = (USER / "cmake/bfd_layout_witness.c").read_text()
            self.assertEqual(witness.count('#include "/usr/include/bfd.h"'), 1)
            (work / "witness.c").write_text(witness.replace(
                '#include "/usr/include/bfd.h"', '#include <bfd.h>'))
            subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(work), str(work / "witness.c"), "-o", str(work / "witness")],
                           check=True, capture_output=True, text=True)
            layout = subprocess.check_output([str(work / "witness")], text=True)
            (work / "bfd_layout.rs").write_text(layout)
            subprocess.run([rustc, "--crate-name", "bfd_accessors", "--crate-type", "lib",
                            "--edition=2021", "-Dwarnings", "-C", "panic=abort", "-C", "opt-level=2",
                            "--emit=obj=" + str(work / "rust.o"), str(USER / "rust/bfd_accessors.rs")],
                           env={**os.environ, "MCKERNEL_BFD_LAYOUT_RS": str(work / "bfd_layout.rs")},
                           check=True, capture_output=True, text=True)
            objects = [str(work / "rust.o")]
            for prefix in ("mcinspect", "eclair"):
                obj = work / (prefix + ".o")
                subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                                "-I", str(work),
                                "-D" + prefix + "_bfd_get_symtab_upper_bound_bridge=reference_" + prefix + "_bfd_get_symtab_upper_bound_bridge",
                                "-D" + prefix + "_bfd_canonicalize_symtab_bridge=reference_" + prefix + "_bfd_canonicalize_symtab_bridge",
                                "-c", str(USER / (prefix + "_bfd_shim.c")), "-o", str(obj)],
                               check=True, capture_output=True, text=True)
                objects.append(str(obj))
            (work / "harness.c").write_text(HARNESS)
            subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-Werror=incompatible-pointer-types", "-I", str(work),
                            str(work / "harness.c"), *objects, "-o", str(work / "harness")],
                           check=True, capture_output=True, text=True)
            completed = subprocess.run([str(work / "harness")], check=True,
                                       capture_output=True, text=True)
            self.assertEqual(completed.stdout, "72 C/Rust callback behavior cases passed\n")


if __name__ == "__main__":
    unittest.main()
