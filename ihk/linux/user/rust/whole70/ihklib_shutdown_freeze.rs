//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Exact supported DEBUG=OFF lifecycle leaf contracts; no rollback or new policy.

use core::ffi::{c_char, c_int, c_ulong};

unsafe extern "C" {
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
    fn snprintf(text: *mut c_char, size: usize, format: *const c_char, ...) -> c_int;
}

unsafe fn finish(fd: c_int, result: c_int) -> c_int {
    if fd != -1 {
        // SAFETY: preserve the C fd != -1 cleanup condition, including encoded
        // negative open errors. Only a nonnegative result actually owns an FD.
        unsafe { close(fd) };
    }
    result
}

/// Request normal shutdown without changing the existing ioctl/error ordering.
///
/// # Safety
/// The selected OS-open and libc providers must implement the current LP64 ABI.
/// The caller must retain the selected OS instance for this synchronous request.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_shutdown(index: c_int) -> c_int {
    // SAFETY: the existing provider takes the unmodified integer OS index.
    let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
    if fd < 0 {
        // SAFETY: the shared logger owns its bounded buffer and diagnostic FD;
        // this exact fixed message has no extra variadic arguments.
        unsafe {
            super::ihklib_cli_parsers::log(|text, size| {
                snprintf(
                    text,
                    size,
                    b"ihk_os_shutdown: error: ihklib_os_open\n\0".as_ptr().cast(),
                );
            });
            return finish(fd, fd);
        }
    }
    // SAFETY: fd is this call's owned OS descriptor; UAPI SHUTDOWN receives the
    // original promoted int-zero argument, not a pointer or unsigned long.
    let value = unsafe { ioctl(fd, 0x112a02, 0 as c_int) };
    let result = if value == 0 {
        value
    } else {
        // SAFETY: read thread-local errno before close can replace it.
        unsafe { -*__errno_location() }
    };
    // SAFETY: result is captured and this function is the only descriptor owner.
    unsafe { finish(fd, result) }
}

unsafe fn change_set(os_set: *mut c_ulong, n: c_int, request: c_ulong) -> c_int {
    if n <= 0 {
        return -22;
    }
    for index in 0..n {
        // SAFETY: caller supplies ceil(n/64) readable aligned LP64 bitset words.
        let selected = unsafe { os_set.add((index / 64) as usize).read() };
        if selected & ((1 as c_ulong) << (index % 64)) == 0 {
            continue;
        }
        // SAFETY: selected indices are passed in ascending order to the existing
        // provider. Each owned FD is closed before advancing to the next index.
        let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
        if fd < 0 {
            // SAFETY: preserve baseline negative-result cleanup and first error.
            return unsafe { finish(fd, fd) };
        }
        // SAFETY: request is one of the two fixed UAPI values supplied below;
        // fd is owned, and the third argument retains the original int-zero ABI.
        let value = unsafe { ioctl(fd, request, 0 as c_int) };
        if value != 0 {
            // SAFETY: libc's errno pointer is valid in the calling thread.
            let result = unsafe { -*__errno_location() };
            // SAFETY: the original result is captured before the single close.
            return unsafe { finish(fd, result) };
        }
        // SAFETY: successful ioctl does not transfer this call's owned FD.
        unsafe { close(fd) };
    }
    0
}

/// Freeze selected indices in ascending order, retaining earlier successful effects.
///
/// # Safety
/// For n > 0, os_set must address ceil(n/64) readable aligned unsigned-long words.
/// The caller retains the OS instances and the bitset for the call's duration.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_freeze(os_set: *mut c_ulong, n: c_int) -> c_int {
    // SAFETY: caller supplies the documented bitset; request is exactly FREEZE.
    unsafe { change_set(os_set, n, 0x112a30) }
}

/// Thaw selected indices with the same partial-completion contract as the C API.
///
/// # Safety
/// For n > 0, os_set must address ceil(n/64) readable aligned unsigned-long words.
/// The caller retains the OS instances and the bitset for the call's duration.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_thaw(os_set: *mut c_ulong, n: c_int) -> c_int {
    // SAFETY: caller supplies the documented bitset; request is exactly THAW.
    unsafe { change_set(os_set, n, 0x112a31) }
}
