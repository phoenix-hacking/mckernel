"""Isolated behavioral checks of the actual F06 signal/ptrace Rust adapters.

The complete production abi.rs and adapter modules are compiled unchanged into
a local unit-test executable. C kprintf/terminate implementations below are
observation providers and unit-test doubles only: they do not qualify production
provider ownership, final linkage, kernel execution or native signal delivery.

Run with the repository-pinned nightly-2026-02-19 compiler on PATH, or select its
ordinary rustc executable through RUSTC. No production build/install is invoked.
"""

import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


C_OBSERVATION_PROVIDERS = r'''
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Unit-test doubles, never production kernel provider replacements. */
_Static_assert(sizeof(int) == 4, "expected x86 C int width");
_Static_assert(sizeof(long) == 8, "expected x86_64 C long width");
static unsigned prints, terminations, event_count, events[4];
static unsigned last_unsigned;
static long last_error;
static int last_status, last_signal;
static char last_format[256], last_text[256];

void f06_test_reset(void)
{
    prints = terminations = event_count = last_unsigned = 0;
    last_error = 0;
    last_status = last_signal = -999;
    memset(events, 0, sizeof events);
    memset(last_format, 0, sizeof last_format);
    memset(last_text, 0, sizeof last_text);
}

int kprintf(const char *format, ...)
{
    va_list args, observe;
    va_start(args, format);
    va_copy(observe, args);
    if (strcmp(format, "ptrace_read_regset: not supported type 0x%x\n") == 0 ||
        strcmp(format, "ptrace_write_regset: not supported type 0x%x\n") == 0) {
        /* Consume exactly the unsigned-int argument required by %x. */
        last_unsigned = va_arg(observe, unsigned int);
    } else if (strcmp(format, "native signal return rejected: %ld\n") == 0) {
        last_error = va_arg(observe, long);
    }
    va_end(observe);
    snprintf(last_format, sizeof last_format, "%s", format);
    int result = vsnprintf(last_text, sizeof last_text, format, args);
    va_end(args);
    prints++;
    if (event_count < 4)
        events[event_count++] = 1;
    return result;
}

void terminate(int status, int signal)
{
    /* Deliberately returns so the adapter's documented -EFAULT is observable. */
    last_status = status;
    last_signal = signal;
    terminations++;
    if (event_count < 4)
        events[event_count++] = 2;
}

unsigned f06_test_prints(void) { return prints; }
unsigned f06_test_terminations(void) { return terminations; }
unsigned f06_test_event_count(void) { return event_count; }
unsigned f06_test_event(unsigned index) { return index < 4 ? events[index] : 0; }
unsigned f06_test_unsigned(void) { return last_unsigned; }
long f06_test_error(void) { return last_error; }
int f06_test_status(void) { return last_status; }
int f06_test_signal(void) { return last_signal; }
const char *f06_test_format(void) { return last_format; }
const char *f06_test_text(void) { return last_text; }
'''


RUST_BEHAVIOR_TESTS = r'''
// Only observation providers are doubled. The production modules above and their
// complete actual ABI definitions are included by path without body extraction.
mod debug {
    unsafe extern "C" {
        pub fn kprintf(format: *const i8, ...) -> i32;
    }
}

unsafe extern "C" {
    fn f06_test_reset();
    fn f06_test_prints() -> u32;
    fn f06_test_terminations() -> u32;
    fn f06_test_event_count() -> u32;
    fn f06_test_event(index: u32) -> u32;
    fn f06_test_unsigned() -> u32;
    fn f06_test_error() -> i64;
    fn f06_test_status() -> i32;
    fn f06_test_signal() -> i32;
    fn f06_test_format() -> *const i8;
    fn f06_test_text() -> *const i8;
}

unsafe fn observed_text() -> String {
    unsafe { std::ffi::CStr::from_ptr(f06_test_text()).to_str().unwrap().to_owned() }
}

#[test]
fn notification_initializes_all_bytes_with_signed_values_and_canaries() {
    #[repr(C, align(8))]
    struct Guarded {
        before: [u8; 16],
        payload: [u8; 128],
        after: [u8; 16],
    }
    assert_eq!(core::mem::size_of::<abi::SigInfo>(), 128);
    assert_eq!(core::mem::align_of::<abi::SigInfo>(), 8);
    let mut guarded = Guarded {
        before: [0xc3; 16], payload: [0xa5; 128], after: [0x5a; 16],
    };
    let signed_values = [i32::MIN, -4095, -1, 0, 5, 73, i32::MAX];
    let mut calls = 0;
    for tid in signed_values {
        for status in signed_values {
            // Alternate poisoned input with immediate reuse of previous output.
            if calls % 3 == 0 {
                guarded.payload.fill(0xa5 ^ calls as u8);
            }
            let info = guarded.payload.as_mut_ptr().cast::<abi::SigInfo>();
            assert_eq!((info as usize) % core::mem::align_of::<abi::SigInfo>(), 0);
            unsafe {
                f06_signal_trap_info::arch_do_signal_trap_info_bridge(info, tid, status);
            }
            // Independent x86_64 siginfo wire expectation includes every unused
            // byte and padding byte, rather than just the four written fields.
            let mut expected = [0u8; 128];
            expected[0..4].copy_from_slice(&17i32.to_ne_bytes());
            expected[8..12].copy_from_slice(&4i32.to_ne_bytes());
            expected[16..20].copy_from_slice(&tid.to_ne_bytes());
            expected[24..28].copy_from_slice(&status.to_ne_bytes());
            assert_eq!(guarded.payload, expected, "tid={tid}, status={status}");
            assert_eq!(guarded.before, [0xc3; 16]);
            assert_eq!(guarded.after, [0x5a; 16]);
            calls += 1;
        }
    }
    assert_eq!(calls, 49);
}

#[test]
fn regset_diagnostic_event_selection_and_unsigned_int_payload() {
    for event in [i32::MIN, -1, 0, 3, i32::MAX] {
        unsafe { f06_test_reset() };
        f06_signal_ptrace_diagnostics::arch_ptrace_regset_log_bridge(event, -1);
        unsafe {
            assert_eq!(f06_test_prints(), 0);
            assert_eq!(f06_test_terminations(), 0);
            assert_eq!(f06_test_event_count(), 0);
            assert_eq!(observed_text(), "");
        }
    }
    for (event, operation) in [(1, "read"), (2, "write")] {
        for value in [0i64, -1, 0x0123_4567_feed_beef, i64::MIN + 0x89ab_cdef,
                      i64::MAX, -0x1_0000_0001] {
            unsafe { f06_test_reset() };
            f06_signal_ptrace_diagnostics::arch_ptrace_regset_log_bridge(event, value);
            let expected_format = format!("ptrace_{operation}_regset: not supported type 0x%x\n");
            let expected_text = format!("ptrace_{operation}_regset: not supported type 0x{:x}\n",
                                        value as u32);
            unsafe {
                assert_eq!(f06_test_prints(), 1);
                assert_eq!(f06_test_terminations(), 0);
                assert_eq!(f06_test_event_count(), 1);
                assert_eq!(f06_test_event(0), 1);
                assert_eq!(f06_test_unsigned(), value as u32);
                assert_eq!(std::ffi::CStr::from_ptr(f06_test_format()).to_str().unwrap(),
                           expected_format);
                assert_eq!(observed_text(), expected_text);
            }
        }
    }
}

#[test]
fn bad_frame_logs_error_then_terminates_and_preserves_return_if_endpoint_returns() {
    for error in [i64::MIN, -4095, -14, -1, 0, 17, i64::MAX] {
        unsafe {
            f06_test_reset();
            assert_eq!(f06_signal_ptrace_diagnostics::arch_native_signal_bad_frame_bridge(error),
                       -14);
            assert_eq!(f06_test_prints(), 1);
            assert_eq!(f06_test_error(), error);
            assert_eq!(observed_text(), format!("native signal return rejected: {error}\n"));
            assert_eq!(f06_test_terminations(), 1);
            assert_eq!(f06_test_status(), 0);
            assert_eq!(f06_test_signal(), 11);
            assert_eq!(f06_test_event_count(), 2);
            assert_eq!([f06_test_event(0), f06_test_event(1)], [1, 2]);
        }
    }
}
'''


class F06SignalAdapterTests(unittest.TestCase):
    def checked_run(self, command, timeout=60):
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.returncode, 0,
                         " ".join(map(str, command)) + "\n" + result.stdout + result.stderr)
        return result

    def test_actual_signal_adapter_behavior(self):
        rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        if not rustc:
            self.skipTest("Rust compiler unavailable; set RUSTC or put rustc on PATH")
        if platform.machine().lower() not in ("x86_64", "amd64"):
            self.skipTest("The selected F06 ABI fixture requires an x86_64 host")
        cc = shutil.which("gcc")
        if not cc:
            self.skipTest("GCC unavailable for the unit-test varargs observation provider")

        with tempfile.TemporaryDirectory(prefix="f06-signal-adapters-") as temporary:
            directory = Path(temporary)
            c_source = directory / "observation_providers.c"
            c_object = directory / "observation_providers.o"
            rust_source = directory / "signal_adapter_tests.rs"
            binary = directory / "signal_adapter_tests"
            c_source.write_text(C_OBSERVATION_PROVIDERS)
            modules = ""
            for module, relative in (
                ("abi", "kernel/rust/abi.rs"),
                ("f06_signal_trap_info", "kernel/rust/f06_signal_trap_info.rs"),
                ("f06_signal_ptrace_diagnostics", "kernel/rust/f06_signal_ptrace_diagnostics.rs"),
            ):
                modules += f"#[path = {json.dumps(str(ROOT / relative))}] mod {module};\n"
            rust_source.write_text(modules + RUST_BEHAVIOR_TESTS)
            self.checked_run([cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                              "-c", str(c_source), "-o", str(c_object)])
            self.checked_run([rustc, "--edition=2021", "--test", "-Dwarnings",
                              "--cfg", "native_linux_irq_work_v6_12",
                              "-C", "opt-level=1", "-C", "linker=" + cc,
                              "-C", "link-arg=" + str(c_object),
                              str(rust_source), "-o", str(binary)])
            result = self.checked_run([str(binary), "--test-threads=1", "--nocapture"])
            self.assertIn("3 passed", result.stdout)
            print(result.stdout, end="")


if __name__ == "__main__":
    unittest.main()
