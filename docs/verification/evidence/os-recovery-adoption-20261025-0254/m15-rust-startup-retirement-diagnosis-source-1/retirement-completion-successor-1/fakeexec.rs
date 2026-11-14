// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Ordinary HOST-only fake launcher. It inspects actual execve argc/argv/envp,
//! including the empty argument and final NULL. Never stage as real mcexec.
#![no_main]
use std::ffi::{c_char, c_int, c_void, CStr};
unsafe extern "C" {
    fn write(fd: c_int, data: *const c_void, count: usize) -> isize;
}
const EXPECTED_ARGV: [&[u8]; 8] = [b"/bin/mcexec", b"-t", b"1", b"0", b"app", b"A", b"", b"B"];
const EXPECTED_ENV: [&[u8]; 2] = [b"PATH=/usr/bin:/bin", b"COKERNEL_PATH=/apps"];
const EXPECTED_OUTPUT: &[u8] = b"{\"case\":\"startup.argv-empty\",\"argc\":4,\"argv\":[\"app\",\"A\",\"\",\"B\"],\"terminator_is_null\":true}\n";
unsafe fn exact_vector(pointer: *const *const c_char, expected: &[&[u8]]) -> bool {
    if pointer.is_null() {
        return false;
    }
    for (index, bytes) in expected.iter().enumerate() {
        // libc main supplies argc+1 live argv pointers and a NULL-terminated
        // environment. Read each expected pointer before its C string and do
        // not index past a NULL. Fixed vectors bound all reads in this helper.
        let value = unsafe { pointer.add(index).read() };
        if value.is_null() || unsafe { CStr::from_ptr(value) }.to_bytes() != *bytes {
            return false;
        }
    }
    unsafe { pointer.add(expected.len()).read().is_null() }
}
#[no_mangle]
pub unsafe extern "C" fn main(
    argc: c_int,
    argv: *const *const c_char,
    envp: *const *const c_char,
) -> c_int {
    if argc != 8
        || !unsafe { exact_vector(argv, &EXPECTED_ARGV) }
        || !unsafe { exact_vector(envp, &EXPECTED_ENV) }
    {
        let error = b"unexpected argc or argv terminator\n";
        let _ = unsafe { write(2, error.as_ptr().cast(), error.len()) };
        return 41;
    }
    if unsafe { write(1, EXPECTED_OUTPUT.as_ptr().cast(), EXPECTED_OUTPUT.len()) }
        == EXPECTED_OUTPUT.len() as isize
    {
        0
    } else {
        42
    }
}
