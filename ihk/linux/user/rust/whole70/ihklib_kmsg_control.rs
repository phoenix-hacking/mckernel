//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Remaining public kernel-message control APIs; reuse the Rust OS-open provider.

use core::ffi::{c_int, c_ulong};

const KMSG_SIZE: c_int = (4 << 20) - 4096;
const CLEAR_KMSG: c_ulong = 0x112a21;

unsafe extern "C" {
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
}

unsafe fn finish(fd: c_int, result: c_int) -> c_int {
    if fd != -1 {
        // SAFETY: close accepts any integer descriptor. Positive descriptors come
        // from this call's owned OS-open result; negative errors preserve the C
        // cleanup condition. The already captured result survives any close errno.
        unsafe { close(fd) };
    }
    result
}

/// Return the fixed public message-buffer size after the original access check.
///
/// # Safety
/// The selected Rust OS-open provider and libc symbols must satisfy their public
/// Linux LP64 contracts. This function transfers no descriptor to the caller.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_kmsg_size(index: c_int) -> c_int {
    // SAFETY: the existing provider accepts every int index, checks access, and
    // returns an owned descriptor or negative error. No pointer is supplied here.
    let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
    let result = if fd < 0 { fd } else { KMSG_SIZE };

    // SAFETY: fd is this call's exact OS-open result, and result is captured first.
    unsafe { finish(fd, result) }
}

/// Clear the selected OS message ring with the original public ioctl contract.
///
/// # Safety
/// The selected Rust OS-open provider and libc ioctl must implement the existing
/// Linux LP64 ABI. The provider's returned descriptor belongs exclusively to this
/// call until finish closes it; callers retain their ordinary OS index lifetime.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_clear_kmsg(index: c_int) -> c_int {
    // SAFETY: index is passed unchanged to the existing public OS-open provider.
    let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
    if fd < 0 {
        // SAFETY: preserve the exact baseline cleanup for the failed open result.
        return unsafe { finish(fd, fd) };
    }

    // SAFETY: fd is owned here, the request is the exact UAPI CLEAR_KMSG value,
    // and the variadic third argument has the same promoted int-zero ABI as C.
    let value = unsafe { ioctl(fd, CLEAR_KMSG, 0 as c_int) };
    let result = if value != 0 {
        // SAFETY: libc returns this thread's valid errno pointer. Read it before
        // close can replace it; the original maps every nonzero ioctl result.
        unsafe { -*__errno_location() }
    } else {
        value
    };

    // SAFETY: no other owner or path has closed this call's descriptor.
    unsafe { finish(fd, result) }
}
