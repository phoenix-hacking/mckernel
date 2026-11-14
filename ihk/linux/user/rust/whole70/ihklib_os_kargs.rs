//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Space-token mandatory-hidos rule with owned temporary argument storage.

use core::ffi::{c_char, c_int, c_ulong, c_void};
use core::ptr::null_mut;

unsafe extern "C" {
    fn strdup(text: *const c_char) -> *mut c_char;
    fn strsep(cursor: *mut *mut c_char, delimiters: *const c_char) -> *mut c_char;
    fn strcmp(first: *const c_char, second: *const c_char) -> c_int;
    fn free(pointer: *mut c_void);
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
}

unsafe fn finish(fd: c_int, allocation: *mut c_char, result: c_int) -> c_int {
    // SAFETY: allocation is the unchanged strdup base or NULL. The separate
    // tokenization cursor never transfers or replaces ownership of this storage.
    unsafe { free(allocation.cast()) };
    if fd != -1 {
        // SAFETY: preserve the exact C cleanup predicate, including negative
        // encoded open errors. Successful open transfers one FD to this call.
        unsafe { close(fd) };
    }
    result
}

/// Set kernel arguments after the existing bounded string and mandatory-token check.
///
/// # Safety
/// Nonnull kargs must be readable through its NUL or the first 1MiB bytes, whichever
/// comes first. The caller retains that original buffer through the ioctl. libc
/// and the synchronous UAPI provider must implement the selected Linux LP64 ABI.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_kargs(index: c_int, kargs: *mut c_char) -> c_int {
    // SAFETY: unchanged integer index is accepted by the selected OS-open helper.
    let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
    if fd < 0 {
        // SAFETY: no allocation exists; preserve the captured open error.
        return unsafe { finish(fd, null_mut(), fd) };
    }
    if kargs.is_null() {
        // SAFETY: no allocation exists and no null input read has occurred.
        return unsafe { finish(fd, null_mut(), -14) };
    }
    let mut length = 0;
    loop {
        // SAFETY: caller supplies the readable prefix; length never reaches 1MiB.
        if unsafe { kargs.add(length).read() } == 0 {
            break;
        }
        length += 1;
        if length >= 1 << 20 {
            // SAFETY: reject immediately after the original maximum non-NUL byte.
            return unsafe { finish(fd, null_mut(), -22) };
        }
    }
    // SAFETY: the preceding scan established a readable NUL-terminated input.
    let allocation = unsafe { strdup(kargs) };
    if allocation.is_null() {
        // SAFETY: read the thread's errno before any free/close call.
        let result = unsafe { -*__errno_location() };
        // SAFETY: allocation failed and fd remains this call's responsibility.
        return unsafe { finish(fd, allocation, result) };
    }
    let mut cursor = allocation;
    let mut found = false;
    loop {
        // SAFETY: cursor points into the live strdup allocation, or is NULL after
        // its last token. The delimiter is the original single space, not tabs.
        let token = unsafe { strsep(&mut cursor, b" \0".as_ptr().cast()) };
        if token.is_null() {
            break;
        }
        // SAFETY: strsep returns a NUL-terminated token inside its allocation.
        if unsafe { token.read() } != 0
            && unsafe { strcmp(token, b"hidos\0".as_ptr().cast()) } == 0
        {
            found = true;
        }
    }
    if !found {
        // SAFETY: allocation retains its base; fd is still owned by this call.
        return unsafe { finish(fd, allocation, -22) };
    }
    // SAFETY: pass the original caller buffer, never the tokenized strdup copy.
    let value = unsafe { ioctl(fd, 0x112a04, kargs) };
    let result = if value == 0 {
        value
    } else {
        // SAFETY: capture thread-local errno before free/close can alter it.
        unsafe { -*__errno_location() }
    };
    // SAFETY: fd and the unchanged allocation base remain owned by this call.
    unsafe { finish(fd, allocation, result) }
}
