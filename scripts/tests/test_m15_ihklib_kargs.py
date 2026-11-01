"""Actual C/Rust kargs ownership with explicit synthetic OS/ioctl observers.

Only ihk_os_kargs is compiled, with real libc strings/allocation underneath
tracked strdup/free calls. No device, complete library, SDK or module is used.
"""

from pathlib import Path
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
C_SOURCE = REPO / "ihk/linux/user/ihklib.c"
RUST_SOURCE = REPO / "ihk/linux/user/rust/whole70/ihklib_os_kargs.rs"

OBSERVER = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#ifdef RUST_OBSERVER
extern void __real_free(void *);
#define real_free __real_free
#define observation_reset internal_reset
#define observation_expect internal_expect
#define observation_counts internal_counts
#define observation_discard internal_discard
#else
#define real_free free
#endif
static void *allocation;
static int open_result, ioctl_result, allocation_failure;
static int allocated, released, closed, submitted;
static const char *expected_argument;
void observation_reset(int opened, int ioctled, int failed) {
    allocation = NULL;
    open_result = opened; ioctl_result = ioctled; allocation_failure = failed;
    allocated = released = closed = submitted = 0;
    expected_argument = NULL;
}
void observation_expect(const char *argument) { expected_argument = argument; }
int observation_open(int index) { return open_result; }
char *observation_strdup(const char *text) {
    if (allocation_failure) { errno = ENOMEM; return NULL; }
    allocation = malloc(strlen(text) + 1);
    if (allocation) { memcpy(allocation, text, strlen(text) + 1); ++allocated; }
    return allocation;
}
void observation_free(void *pointer) {
    if (pointer && pointer == allocation) { ++released; allocation = NULL; }
    real_free(pointer);
    errno = EBUSY; /* Cleanup must not replace the saved return value. */
}
int observation_close(int fd) { ++closed; errno = EBUSY; return 0; }
int observation_ioctl(int fd, unsigned long request, ...) {
    va_list arguments;
    va_start(arguments, request);
    char *argument = va_arg(arguments, char *);
    va_end(arguments);
    if (fd != open_result || request != 0x112a04 || argument != expected_argument)
        abort();
    ++submitted;
    errno = EIO;
    return ioctl_result;
}
int observation_counts(int kind) {
    return kind == 0 ? allocated : kind == 1 ? released : kind == 2 ? closed : submitted;
}
void observation_discard(void) { real_free(allocation); allocation = NULL; }
#ifdef RUST_OBSERVER
char *__wrap_strdup(const char *p) { return observation_strdup(p); }
void __wrap_free(void *p) { observation_free(p); }
int __wrap_close(int fd) { return observation_close(fd); }
int __wrap_ioctl(int fd, unsigned long request, ...) {
    va_list arguments;
    va_start(arguments, request);
    char *argument = va_arg(arguments, char *);
    va_end(arguments);
    return observation_ioctl(fd, request, argument);
}
#endif
'''

RUST_ROOT = r'''
unsafe extern "C" { fn observation_open(index: core::ffi::c_int) -> core::ffi::c_int; }
unsafe extern "C" {
    fn internal_reset(opened: i32, ioctled: i32, failed: i32);
    fn internal_expect(argument: *const core::ffi::c_char);
    fn internal_counts(kind: i32) -> i32;
    fn internal_discard();
}
#[no_mangle]
pub unsafe extern "C" fn observation_reset(opened: i32, ioctled: i32, failed: i32) {
    unsafe { internal_reset(opened, ioctled, failed); }
}
#[no_mangle]
pub unsafe extern "C" fn observation_expect(argument: *const core::ffi::c_char) {
    unsafe { internal_expect(argument); }
}
#[no_mangle]
pub unsafe extern "C" fn observation_counts(kind: i32) -> i32 {
    unsafe { internal_counts(kind) }
}
#[no_mangle]
pub unsafe extern "C" fn observation_discard() { unsafe { internal_discard(); } }
mod ihklib_mcstat {
    pub unsafe fn ihklib_os_open(index: core::ffi::c_int) -> core::ffi::c_int {
        unsafe { super::observation_open(index) }
    }
}
#[path = "__SOURCE__"]
mod actual;
'''


def function(source, signature):
    start = source.index(signature)
    body = source.index("{", start)
    depth, end = 1, body + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


class IhklibKargsTests(unittest.TestCase):
    def run_command(self, arguments):
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def observe(self, library):
        actual = ctypes.CDLL(str(library))
        actual.observation_reset.argtypes = [ctypes.c_int] * 3
        actual.observation_expect.argtypes = [ctypes.c_char_p]
        actual.observation_counts.argtypes = [ctypes.c_int]
        actual.ihk_os_kargs.argtypes = [ctypes.c_int, ctypes.c_char_p]
        actual.ihk_os_kargs.restype = ctypes.c_int
        # Input, open result, ioctl result, strdup failure, expected return,
        # expected allocations/frees/closes/ioctls. Space-only grammar is kept.
        cases = [
            (b"hidos", 9, 0, 0, 0, (1, 1, 1, 1)),
            (b"  console=ttyS0  hidos debug  ", 0, 0, 0, 0, (1, 1, 1, 1)),
            (b"hidos hidos", 9, 0, 0, 0, (1, 1, 1, 1)),
            (b"hidos", 9, -1, 0, -5, (1, 1, 1, 1)),
            (b"console=ttyS0", 9, 0, 0, -22, (1, 1, 1, 0)),
            (b"", 9, 0, 0, -22, (1, 1, 1, 0)),
            (b"prefixhidos", 9, 0, 0, -22, (1, 1, 1, 0)),
            (b"hidos\tdebug", 9, 0, 0, -22, (1, 1, 1, 0)),
            (b"hidos", 9, 0, 1, -12, (0, 0, 1, 0)),
            (None, 9, 0, 0, -14, (0, 0, 1, 0)),
            (b"hidos", -1, 0, 0, -1, (0, 0, 0, 0)),
            (b"hidos", -2, 0, 0, -2, (0, 0, 1, 0)),
            (b"hidos " + b"x" * ((1 << 20) - 7), 9, 0, 0, 0, (1, 1, 1, 1)),
            (b"hidos " + b"x" * ((1 << 20) - 6), 9, 0, 0, -22, (0, 0, 1, 0)),
        ]
        for number, (text, opened, ioctled, failed, expected, counts) in enumerate(cases):
            with self.subTest(case=number):
                original = ctypes.create_string_buffer(text) if text is not None else None
                before = bytes(original) if original is not None else None
                actual.observation_reset(opened, ioctled, failed)
                actual.observation_expect(original)
                try:
                    self.assertEqual(actual.ihk_os_kargs(3, original), expected)
                    self.assertEqual(tuple(actual.observation_counts(i) for i in range(4)), counts)
                    if original is not None:
                        self.assertEqual(bytes(original), before, "caller input was tokenized")
                finally:
                    actual.observation_discard()

    def test_actual_retained_c_kargs(self):
        compiler = shutil.which(os.environ.get("CC") or "cc")
        self.assertIsNotNone(compiler, "bind CC to a C compiler")
        with tempfile.TemporaryDirectory(prefix="m15-kargs-c-") as temporary:
            directory = Path(temporary)
            source = directory / "actual.c"
            source.write_text(OBSERVER + r'''
#define ihklib_os_open observation_open
#define strdup observation_strdup
#define free observation_free
#define close observation_close
#define ioctl observation_ioctl
#define dprintf(...) ((void)0)
#define dnprintk(...) ((void)0)
#define IHKLIB_MAX_SIZE_KARGS (1 << 20)
#define IHK_OS_SET_KARGS 0x112a04
''' + function(C_SOURCE.read_text(), "int ihk_os_kargs("))
            library = directory / "actual.so"
            self.run_command([compiler, "-std=gnu11", "-shared", "-fPIC", str(source), "-o", str(library)])
            self.observe(library)

    def test_actual_rust_kargs(self):
        compiler = shutil.which(os.environ.get("CC") or "cc")
        rustc = shutil.which(os.environ.get("RUSTC") or "rustc")
        self.assertIsNotNone(compiler, "bind CC to a C compiler")
        self.assertIsNotNone(rustc, "bind RUSTC to the qualified compiler")
        with tempfile.TemporaryDirectory(prefix="m15-kargs-rust-") as temporary:
            directory = Path(temporary)
            observer, object_file = directory / "observer.c", directory / "observer.o"
            observer.write_text(OBSERVER)
            self.run_command([compiler, "-DRUST_OBSERVER", "-fPIC", "-c", str(observer), "-o", str(object_file)])
            source, library = directory / "root.rs", directory / "actual.so"
            source.write_text(RUST_ROOT.replace("__SOURCE__", str(RUST_SOURCE)))
            self.run_command([
                rustc, "--edition=2021", "--crate-type=cdylib", str(source), "-o", str(library),
                "-C", "link-arg=" + str(object_file),
                *sum((["-C", "link-arg=-Wl,--wrap=" + name] for name in ("strdup", "free", "close", "ioctl")), []),
            ])
            self.observe(library)


if __name__ == "__main__":
    unittest.main()
