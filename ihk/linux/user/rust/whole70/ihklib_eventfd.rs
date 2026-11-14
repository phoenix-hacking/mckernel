//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Owned-FD correctness successor. The earlier 960-vector C-parity source is frozen.

use core::ffi::{c_int, c_uint, c_ulong};

#[repr(C)]
struct EventfdDesc {
    fd: c_int,
    kind: c_int,
}

const REGISTER_EVENT: c_ulong = 0x112a15;
const _: () = {
    assert!(core::mem::size_of::<EventfdDesc>() == 8);
    assert!(core::mem::offset_of!(EventfdDesc, kind) == 4);
};

unsafe extern "C" {
    fn ihklib_os_open(index: c_int) -> c_int;
    fn eventfd(initial: c_uint, flags: c_int) -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
}

unsafe fn close_owned(fd: c_int) {
    if fd >= 0 {
        // SAFETY: callers pass only a descriptor acquired by this call, once.
        // Linux close is not retried: EINTR must not cause a reused FD to close.
        unsafe { close(fd) };
    }
}

unsafe fn finish(device: c_int, failed_event: c_int, result: c_int) -> c_int {
    // SAFETY: libc supplies this thread's valid errno slot. Capture the primary
    // operation's errno before either one-shot close can replace it.
    let saved_errno = unsafe { *__errno_location() };

    // SAFETY: a nonnegative failed_event is the original eventfd we created;
    // device is the separate descriptor owned by OS-open. They cannot alias
    // under the selected fresh-descriptor libc/provider contract.
    unsafe {
        close_owned(failed_event);
        close_owned(device);
        *__errno_location() = saved_errno;
    }
    result
}

/// Register an event, transferring its owned eventfd only on successful ioctl.
///
/// # Safety
/// The selected Linux LP64 OS-open, eventfd and ioctl providers must have their
/// actual ABI. OS-open returns an owned FD or encoded negative errno; eventfd
/// returns a fresh FD or -1 with errno. REGISTER_EVENT reads the input descriptor
/// and retains a kernel eventfd reference, without replacing the caller's FD.
/// The OS/device lifetime must satisfy the existing public registration contract.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_eventfd(index: c_int, kind: c_int) -> c_int {
    // SAFETY: the public provider accepts the unchanged integer OS index.
    let device = unsafe { ihklib_os_open(index) };
    if device < 0 {
        // Encoded errors are not acquired descriptors, including values below -1.
        return device;
    }
    if kind != 0 && kind != 2 && kind != 101 {
        // SAFETY: only device is owned; there is no eventfd to release.
        return unsafe { finish(device, -1, -22) };
    }

    // SAFETY: exact libc ABI, initial counter zero and original flags zero.
    let event = unsafe { eventfd(0, 0) };
    if event < 0 {
        // SAFETY: read libc's thread-local errno before closing device. Values
        // below -1 are non-libc provider errors: retain their encoding without
        // treating them as descriptors or issuing a malformed registration.
        let result = if event == -1 {
            unsafe { -*__errno_location() }
        } else {
            event
        };
        // SAFETY: the failed eventfd acquired nothing; only device is owned.
        return unsafe { finish(device, -1, result) };
    }

    let descriptor = EventfdDesc { fd: event, kind };
    // SAFETY: device is owned, descriptor is live/aligned for the whole call,
    // and the actual REGISTER_EVENT consumer only copies this input structure.
    let registered = unsafe { ioctl(device, REGISTER_EVENT, &descriptor as *const EventfdDesc) };
    if registered != 0 {
        // SAFETY: capture the primary ioctl errno before releasing both owned FDs.
        let result = unsafe { -*__errno_location() };
        // SAFETY: registration failed, so event ownership has not transferred.
        return unsafe { finish(device, event, result) };
    }

    // SAFETY: success transfers event to our caller. Only device is closed here;
    // the kernel's retained eventfd reference does not own the caller's FD number.
    unsafe { finish(device, -1, event) }
}

#[cfg(ihklib_eventfd_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_eventfd_desc_size() -> usize {
    core::mem::size_of::<EventfdDesc>()
}

#[cfg(ihklib_eventfd_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_eventfd_type_offset() -> usize {
    core::mem::offset_of!(EventfdDesc, kind)
}
