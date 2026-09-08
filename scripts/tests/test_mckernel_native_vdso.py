"""Actual native descriptor, publication and Linux clock arithmetic bodies."""
from pathlib import Path
import os
import re
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

    def test_actual_mapping_bodies_and_native_supplemental_pages(self):
        rustc, cc = shutil.which("rustc"), shutil.which("cc")
        if rustc is None:
            self.skipTest("Rust compiler unavailable")
        self.assertIsNotNone(cc)
        rust = (ROOT / "kernel/rust/syscall_policy.rs").read_text()
        generated = '#![allow(dead_code)]\n'
        generated += '#[path = ' + repr(str(ROOT / "kernel/rust/abi.rs")).replace("'", '"') + '] mod abi;\n'
        generated += 'use abi::{CInt, CLong, CULong, SizeT, ProcessVm, VmRange};\nuse core::{ffi::c_void, ptr::null_mut};\n'
        generated += '#[repr(C)]\n' + function(rust, "pub struct ArchVdso {") + '\n'
        generated += rust[rust.index("type ArchVdsoGetInfoFn"):rust.index('unsafe extern "C" {', rust.index("type ArchVdsoGetInfoFn"))]
        names = ('EINVAL', 'EFAULT', 'PAGE_SIZE', 'VR_REMOTE', 'VR_PROT_READ', 'VR_PROT_EXEC', 'VR_PROT_MASK',
                 'PTATTR_ACTIVE', 'PTATTR_USER', 'PTATTR_NO_EXECUTE', 'PTATTR_UNCACHABLE')
        for name in names:
            generated += re.search(r'^const ' + name + r':[^;]+;', rust, re.M).group(0) + '\n'
        generated += '\n'.join(re.findall(r'^const ARCH_VDSO_MAP_LOG_[^;]+;', rust, re.M)) + '\n'
        for signature in ['fn arch_vdso_container(', 'fn arch_vdso_addr_add(', 'fn arch_vdso_maxprot(',
                          'pub unsafe extern "C" fn arch_map_vdso_body_result(', 'unsafe fn arch_map_vdso_with_pages(']:
            generated += function(rust, signature) + '\n'
        generated += (ROOT / "scripts/tests/fixtures/mckernel_native_vdso_mapping.rs").read_text()
        c = r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define dkprintf(...) ((void)0)
#define ekprintf(...) ((void)0)
#define kprintf(...) ((void)0)
#define PAGE_SIZE 4096
#define PAGE_SHIFT 12
#define NOPHYS (~0UL)
#define VR_REMOTE 0x200UL
#define VR_PROT_READ 0x10000UL
#define VR_PROT_EXEC 0x40000UL
#define VRFLAG_PROT_TO_MAXPROT(f) (((f) & 0x70000UL) << 4)
enum ihk_mc_pt_attribute { PTATTR_ACTIVE=1, PTATTR_USER=4,
    PTATTR_NO_EXECUTE=0x8000000000000000UL, PTATTR_UNCACHABLE=0x10000 };
typedef void *page_table_t;
struct vm_range { int unused; };
struct address_space { page_table_t page_table; };
struct process_vm {
    struct address_space *address_space;
    struct { unsigned long map_end; } region;
    void *vdso_addr, *vvar_addr;
};
struct descriptor {
    long busy; int vdso_npages;
    char vvar_is_global, hpet_is_global, pvti_is_global, padding;
    long vdso_physlist[2];
    void *vvar_virt; long vvar_phys;
    void *hpet_virt; long hpet_phys;
    void *pvti_virt; long pvti_phys;
    void *vgtod_virt;
};
_Static_assert(sizeof(struct descriptor) == 88, "legacy descriptor");
struct outcome { int error; unsigned count; uint64_t map_end, vdso_addr, vvar_addr, calls[16][6]; };
static struct outcome trace;
static struct descriptor vdso;
static size_t container_size;
static intptr_t vdso_offset;
static int fail_at;
static int record(uint64_t kind, uint64_t start, uint64_t end, uint64_t physical, uint64_t attr)
{
    uint64_t row[6] = {kind, start, end, physical, attr, 0};
    memcpy(trace.calls[trace.count++], row, sizeof row);
    return trace.count == fail_at ? -12 : 0;
}
static int add_process_memory_range(struct process_vm *vm, unsigned long start, unsigned long end,
    unsigned long phys, unsigned long flags, void *obj, unsigned long offset, unsigned long shift,
    void *policy, struct vm_range **range)
{
    *range = (struct vm_range *)0x1000;
    return record(1, start, end, 0, flags);
}
static int ihk_mc_pt_set_range(page_table_t pt, struct process_vm *vm, void *start, void *end,
    unsigned long phys, enum ihk_mc_pt_attribute attr, int p2align, struct vm_range *range, int overwrite)
{
    return record(2, (uintptr_t)start, (uintptr_t)end, phys, attr);
}
'''
        c += function((ROOT / "arch/x86_64/kernel/syscall.c").read_text(),
                      'int arch_map_vdso(struct process_vm *vm)\n')
        c += r'''
void reference_map(const struct descriptor *input, size_t size, intptr_t offset, int failure, struct outcome *output)
{
    struct address_space as = {(void *)0x4000};
    struct process_vm vm = {&as, {0x100000}, NULL, NULL};
    memset(&trace, 0, sizeof trace);
    memcpy(&vdso, input, sizeof vdso);
    container_size = size; vdso_offset = offset; fail_at = failure;
    trace.error = arch_map_vdso(&vm);
    trace.map_end = vm.region.map_end;
    trace.vdso_addr = (uintptr_t)vm.vdso_addr;
    trace.vvar_addr = (uintptr_t)vm.vvar_addr;
    memcpy(output, &trace, sizeof trace);
}
'''
        with tempfile.TemporaryDirectory(prefix="native-vdso-map-") as temporary:
            directory = Path(temporary)
            (directory / "mapping.rs").write_text(generated)
            (directory / "reference.c").write_text(c)
            reference = directory / "reference.o"
            self.run_checked([cc, "-O2", "-fPIC", "-Wall", "-Werror", "-c",
                              str(directory / "reference.c"), "-o", str(reference)])
            output = directory / "map-tests"
            self.run_checked([rustc, "--edition=2021", "--test", "-Dwarnings", "-O",
                              str(directory / "mapping.rs"), "-C", "link-arg=" + str(reference), "-o", str(output)])
            self.assertIn("actual C/Rust mapping scenarios=144", self.run_checked(
                [str(output), "--test-threads=1", "--nocapture"]))

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
