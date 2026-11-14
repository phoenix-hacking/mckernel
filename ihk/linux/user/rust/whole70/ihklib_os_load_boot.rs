//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Public load/boot source port with bounded polling through the first terminal result.

use core::ffi::{c_char, c_int, c_uint, c_ulong};

const LOAD: c_ulong = 0x112a00;
const BOOT: c_ulong = 0x112a01;
const STATUS: c_ulong = 0x112a14;

unsafe extern "C" {
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn usleep(usec: c_uint) -> c_int;
    fn __errno_location() -> *mut c_int;
}

unsafe fn finish(fd: c_int, result: c_int) -> c_int {
    if fd != -1 {
        // SAFETY: close accepts an integer FD. Preserve the exact C cleanup for
        // negative encoded errors too; this parity port does not claim that fix.
        unsafe { close(fd) };
    }
    result
}

/// Load the OS image designated by the caller's original C filename pointer.
///
/// # Safety
/// A nonnull filename must satisfy the existing ioctl caller contract: a readable
/// NUL-terminated C string alive for the synchronous LOAD request. This function
/// borrows it unchanged, without encoding conversion, allocation or ownership transfer.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_load(index: c_int, filename: *mut c_char) -> c_int {
    // SAFETY: the selected public Rust OS-open accepts the unchanged integer index.
    let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
    let result = if fd < 0 {
        fd
    } else if filename.is_null() {
        -22
    } else {
        // SAFETY: fd is owned here; the caller guarantees filename validity. The
        // actual LP64 C ioctl casts that same pointer to unsigned long.
        let value = unsafe { ioctl(fd, LOAD, filename as c_ulong) };
        if value != 0 {
            // SAFETY: libc returns the current thread's valid errno slot. Capture
            // it before finish can change errno while closing the OS descriptor.
            unsafe { -*__errno_location() }
        } else {
            value
        }
    };

    // SAFETY: result is captured and fd is this call's original OS-open result.
    unsafe { finish(fd, result) }
}

/// Issue BOOT and poll at most fifty times, stopping at a terminal status or error.
///
/// # Safety
/// The selected OS-open and libc providers must implement the public Linux LP64
/// ABI. The OS lifetime must satisfy the existing boot caller contract.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_boot(index: c_int) -> c_int {
    // SAFETY: the existing provider accepts every int OS index and returns its FD.
    let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
    if fd < 0 {
        // SAFETY: keep the existing failed-open return and cleanup condition.
        return unsafe { finish(fd, fd) };
    }

    // SAFETY: BOOT uses the exact UAPI request and original promoted int-zero arg.
    let mut value = unsafe { ioctl(fd, BOOT, 0 as c_int) };
    if value == -1 {
        // SAFETY: read thread-local errno before any descriptor close.
        let result = unsafe { -*__errno_location() };
        // SAFETY: fd is still this call's exact owned OS descriptor.
        return unsafe { finish(fd, result) };
    }

    for _ in 0..50 {
        // SAFETY: STATUS is the existing argument-free ioctl on the owned FD.
        value = unsafe { ioctl(fd, STATUS) };
        if value == 2 || value == 3 || value == 4 {
            // SAFETY: libc usleep takes unsigned int microseconds. Its return and
            // errno do not replace the original status; C ignores sleep failure.
            unsafe { usleep(200_000) };
        } else {
            break;
        }
    }

    let result = if value == -1 {
        // SAFETY: capture the last status/sleep errno before closing the owned FD.
        unsafe { -*__errno_location() }
    } else if value != 5 {
        -22
    } else {
        0
    };

    // SAFETY: no other path has closed this call's OS descriptor.
    unsafe { finish(fd, result) }
}
