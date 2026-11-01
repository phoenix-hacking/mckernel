"""Actual C/Rust sigaltstack helpers must snapshot aliased input before output.

The same C observer consumes both actual-source implementations and the real
x86 stack_t/Rust SigStack ABI. User-copy callbacks observe bounded local buffers;
they are not production providers. The separate Linux syscall control installs no handler
and restores its process's original alternate stack before exit.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m14_f03_wait_results import function

ROOT = Path(__file__).resolve().parents[2]


def c_function(source, name):
    match = re.search(r"^(?:static inline void \*|(?:SYSCALL_POLICY_HELPER_SCOPE )?(?:int|long)\s*)"
                      + re.escape(name) + r"\(", source, re.M)
    if not match:
        raise ValueError("Missing C helper: " + name)
    opening = source.index("{", match.start())
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end]


CASES = r'''
static int reads, writes;
static long fail_read, fail_write;
static long observe_from(void *dst, unsigned long src, size_t bytes)
{
    reads++;
    if (fail_read) return fail_read;
    memcpy(dst, (void *)src, bytes);
    return 0;
}
static long observe_to(unsigned long dst, const void *src, size_t bytes)
{
    writes++;
    if (fail_write) return fail_write;
    memcpy((void *)dst, src, bytes);
    return 0;
}
static int same(const stack_t *left, const stack_t *right)
{
    return left->ss_sp == right->ss_sp && left->ss_flags == right->ss_flags &&
        left->ss_size == right->ss_size;
}
int main(void)
{
    const stack_t old = {.ss_sp = (void *)0x10000, .ss_size = 8192};
    const stack_t want = {.ss_sp = (void *)0x20000, .ss_size = 16384};
    const stack_t disabled = {.ss_sp = 0, .ss_flags = SS_DISABLE, .ss_size = 0};
    struct { unsigned long prefix[3]; stack_t stack; } thread;
    union { unsigned long align; unsigned char bytes[96]; } buffer;
    const int shifts[] = {0, 8, -8, 32};
    /* Same pointer, both partial-overlap directions, disjoint output; each for
       installation and disable. Only local byte arrays serve as user memory. */
    for (unsigned index = 0; index < sizeof(shifts) / sizeof(shifts[0]); index++) {
        for (int disable = 0; disable < 2; disable++) {
            thread.stack = old;
            stack_t input = disable ? disabled : want;
            unsigned char *ss = buffer.bytes + 24;
            unsigned char *oss = ss + shifts[index];
            memset(&buffer, 0xa5, sizeof(buffer));
            memcpy(ss, &input, sizeof(input));
            reads = writes = 0;
            long rc = sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack),
                (unsigned long)ss, (unsigned long)oss, observe_from, observe_to);
            if (rc || !same(&thread.stack, &input)) return 10 + index * 2 + disable;
            stack_t observed;
            memcpy(&observed, oss, sizeof(observed));
            if (!same(&observed, &old) || reads != 1 || writes != 1) return 20;
        }
    }
    thread.stack = old;
    stack_t output;
    reads = writes = 0;
    if (sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack), 0,
            (unsigned long)&output, 0, observe_to) || !same(&output, &old) ||
            reads || writes != 1 || !same(&thread.stack, &old)) return 21;
    for (long failure = -14; failure <= 1; failure += 15) {
        stack_t input = want;
        reads = writes = 0;
        fail_read = failure;
        if (sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack),
                (unsigned long)&input, (unsigned long)&input, observe_from, observe_to)
                != -14 || reads != 1 || writes || !same(&thread.stack, &old) ||
                !same(&input, &want)) return 22;
        fail_read = 0;
        fail_write = failure;
        reads = writes = 0;
        if (sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack),
                (unsigned long)&input, (unsigned long)&input, observe_from, observe_to)
                != -14 || reads != 1 || writes != 1 || !same(&thread.stack, &old)) return 23;
        fail_write = 0;
    }
    stack_t input = want;
    reads = writes = 0;
    if (sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack),
            (unsigned long)&input, (unsigned long)&input, 0, observe_to) != -14 ||
            reads || writes || !same(&thread.stack, &old) || !same(&input, &want)) return 24;
    if (sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack),
            (unsigned long)&input, (unsigned long)&input, observe_from, 0) != -14 ||
            reads != 1 || writes || !same(&thread.stack, &old)) return 25;
    reads = writes = 0;
    if (sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack), 0, 0, 0, 0) ||
            reads || writes || !same(&thread.stack, &old)) return 26;
    if (sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack),
            (unsigned long)&input, 0, observe_from, 0) || reads != 1 || writes ||
            !same(&thread.stack, &want)) return 27;
    for (int invalid = 0; invalid < 2; invalid++) {
        input = want;
        if (invalid) input.ss_size = MINSIGSTKSZ - 1;
        else input.ss_flags = SS_ONSTACK;
        thread.stack = old;
        reads = writes = 0;
        long rc = sigaltstack_body_result(&thread, offsetof(__typeof__(thread), stack),
            (unsigned long)&input, (unsigned long)&output, observe_from, observe_to);
        if (rc != (invalid ? -ENOMEM : -EINVAL) || reads != 1 || writes != 1 ||
                !same(&thread.stack, &old) || !same(&output, &old)) return 28;
    }
    return 0;
}
'''


class SigaltstackAliasTests(unittest.TestCase):
    def test_actual_c_and_rust_aliasing(self):
        cc = os.environ.get("CC") or shutil.which("gcc")
        rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        self.assertIsNotNone(cc, "C compiler required")
        self.assertIsNotNone(rustc, "Rust compiler required")
        source = (ROOT / "kernel/syscall.c").read_text()
        names = ("sigaltstack_validate", "sigaltstack_is_disable", "sigaltstack_body_result")
        c_bodies = "\n".join(c_function(source, name) for name in names)
        preamble = r'''
#include <stddef.h>
#include <string.h>
#include <signal.h>
#define EINVAL 22
#define EFAULT 14
#define ENOMEM 12
#define SYSCALL_POLICY_HELPER_SCOPE
typedef long (*syscall_copy_from_user_fn_t)(void *, unsigned long, size_t);
typedef long (*syscall_copy_to_user_fn_t)(unsigned long, const void *, size_t);
'''
        rust = (ROOT / "kernel/rust/syscall_policy.rs").read_text()
        declarations = "\n".join(re.search(r"^const " + name + r": [^;]+;", rust, re.M).group(0)
                                 for name in ("EINVAL", "EFAULT", "ENOMEM", "SS_DISABLE", "MINSIGSTKSZ"))
        aliases = "\n".join(re.search(r"^type " + name + r"\s*=[^;]+;", rust, re.M).group(0)
                            for name in ("SyscallCopyFromUserFn", "SyscallCopyToUserFn"))
        rust_unit = '''#![no_std]
#[path = "@ABI@"] mod abi;
use abi::{CInt, CLong, CULong, SizeT, SigStack};
use core::{mem::{size_of, MaybeUninit}, ptr::copy_nonoverlapping};
@DECLARATIONS@
@ALIASES@
@FIELD@
@BODIES@
'''.replace("@ABI@", str(ROOT / "kernel/rust/abi.rs")).replace(
            "@DECLARATIONS@", declarations).replace("@ALIASES@", aliases).replace(
            "@FIELD@", rust[rust.index("unsafe fn field_ptr<T>"):
                            rust.index("\n}", rust.index("unsafe fn field_ptr<T>")) + 2]).replace(
            "@BODIES@", "\n".join("#[no_mangle]\n" + function(rust, name) for name in names))
        with tempfile.TemporaryDirectory(prefix="m14-sigaltstack-alias-") as directory:
            path = Path(directory)
            rust_path, rust_object = path / "unit.rs", path / "rust.o"
            rust_path.write_text(rust_unit)
            compiled = subprocess.run([rustc, "--edition=2021", "--crate-type=lib", "--emit=obj",
                "-C", "panic=abort", "-C", "opt-level=1", "-A", "dead_code", str(rust_path),
                "-o", str(rust_object)], capture_output=True, text=True, timeout=30)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            for language in ("c", "rust"):
                with self.subTest(language=language):
                    unit, binary = path / (language + ".c"), path / language
                    bodies = (c_function(source, "syscall_offset_ptr") + "\n" + c_bodies
                              if language == "c" else
                              "long sigaltstack_body_result(void *, size_t, unsigned long, unsigned long, "
                              "syscall_copy_from_user_fn_t, syscall_copy_to_user_fn_t);")
                    unit.write_text(preamble + bodies + CASES)
                    command = [cc, "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined", "-fno-sanitize-recover=all",
                        "-I", str(ROOT / "arch/x86_64/kernel/include"),
                        str(unit)]
                    if language == "rust":
                        command.append(str(rust_object))
                    compiled = subprocess.run(command + ["-o", str(binary)], capture_output=True,
                                              text=True, timeout=30)
                    self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
                    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0,
                        f"{language} aliased sigaltstack case failed with {result.returncode}: "
                        + result.stdout + result.stderr)

    def test_real_linux_syscall_alias_control(self):
        cc = os.environ.get("CC") or shutil.which("gcc")
        self.assertIsNotNone(cc, "C compiler required")
        control = r'''
#include <signal.h>
#include <unistd.h>
#include <sys/syscall.h>
static unsigned char alternate[65536];
int main(void) {
    stack_t original, current;
    if (sigaltstack(0, &original)) return 1;
    stack_t both = {.ss_sp = alternate, .ss_size = sizeof(alternate)};
    if (syscall(SYS_sigaltstack, &both, &both)) return 2;
    int result = 0;
    if (sigaltstack(0, &current)) result = 3;
    else if (current.ss_sp != alternate || current.ss_size != sizeof(alternate) ||
            current.ss_flags || both.ss_sp != original.ss_sp ||
            both.ss_flags != original.ss_flags || both.ss_size != original.ss_size) result = 4;
    if (sigaltstack(&original, 0)) return 5;
    return result;
}
'''
        with tempfile.TemporaryDirectory(prefix="m14-sigaltstack-libc-") as directory:
            path = Path(directory)
            source, binary = path / "control.c", path / "control"
            source.write_text(control)
            result = subprocess.run([cc, "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
