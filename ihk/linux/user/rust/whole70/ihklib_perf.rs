//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! PERF controls and rusage page-size metadata. Include in the current libihk Rust root.

use core::ffi::{c_int, c_long, c_ulong, c_void};

mod abi {
    include!(env!("MCKERNEL_PERF_PAGES_ABI_RS"));
}

#[cfg(not(all(target_os = "linux", target_arch = "x86_64", target_pointer_width = "64")))]
compile_error!("current PERF/page-size qualification covers Linux x86_64 LP64 only");
#[cfg(ihklib_debug)]
compile_error!("DEBUG diagnostics require the existing libihk logging owner's join");

unsafe extern "C" {
    fn ihklib_os_open(index: c_int) -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
}

unsafe fn neg_errno() -> c_int {
    // SAFETY: libc supplies the current thread's initialized errno cell.
    unsafe { -*__errno_location() }
}

unsafe fn finish(fd: c_int, result: c_int) -> c_int {
    if fd != -1 {
        // SAFETY: preserve the C provider's exact descriptor cleanup contract,
        // including close of a negative open error other than -1. No retry occurs.
        unsafe { close(fd) };
    }
    // Cleanup may change errno, but never replaces the previously captured return.
    result
}

/// Configure existing performance events using the library's public pointer ABI.
///
/// # Safety
/// A nonnull `attr` points to the selected header's ihk_perf_event_attr array,
/// valid for synchronous ioctl access. Its bitfields are opaque to this module.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_setperfevent(index: c_int, attr: *mut c_void, n: c_int) -> c_int {
    if attr.is_null() {
        return -abi::EFAULT;
    }
    // SAFETY: scalar index is forwarded to the existing Rust library provider.
    let fd = unsafe { ihklib_os_open(index) };
    if fd < 0 {
        return unsafe { finish(fd, fd) };
    }
    if n <= 0 {
        return unsafe { finish(fd, -abi::EINVAL) };
    }
    // SAFETY: the live descriptor receives the original promoted-int vararg, not a pointer.
    let count_result = unsafe { ioctl(fd, abi::PERF_NUM, n) };
    if count_result != 0 {
        let result = unsafe { neg_errno() };
        return unsafe { finish(fd, result) };
    }
    // SAFETY: caller supplies the header-ABI event array through this synchronous request.
    let result = unsafe { ioctl(fd, abi::PERF_SET, attr) };
    // SET alone passes positive results through; NUM/GET/controls map any nonzero result.
    let result = if result < 0 { unsafe { neg_errno() } } else { result };
    unsafe { finish(fd, result) }
}

/// Enable, disable or destroy existing performance-event state.
#[no_mangle]
pub extern "C" fn ihk_os_perfctl(index: c_int, command: c_int) -> c_int {
    // SAFETY: scalar index is forwarded unchanged to the existing library provider.
    let fd = unsafe { ihklib_os_open(index) };
    if fd < 0 {
        return unsafe { finish(fd, fd) };
    }
    let request = match command {
        abi::PERF_ENABLE => abi::PERF_ENABLE_REQUEST,
        abi::PERF_DISABLE => abi::PERF_DISABLE_REQUEST,
        abi::PERF_DESTROY => abi::PERF_DESTROY_REQUEST,
        _ => return unsafe { finish(fd, -abi::EINVAL) },
    };
    // SAFETY: live OS descriptor, witnessed request and the original promoted-int zero vararg.
    let result = unsafe { ioctl(fd, request, 0 as c_int) };
    let result = if result != 0 { unsafe { neg_errno() } } else { result };
    unsafe { finish(fd, result) }
}

/// Read existing performance counters with the original count-validation behavior.
///
/// # Safety
/// A nonnull `counter` must be writable for the selected device's synchronous GET.
/// A null pointer is deliberately forwarded when n > 0, matching the public C API.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_getperfevent(index: c_int, counter: *mut c_ulong,
    n: c_int) -> c_int {
    // SAFETY: scalar index is forwarded unchanged to the existing library provider.
    let fd = unsafe { ihklib_os_open(index) };
    if fd < 0 {
        return unsafe { finish(fd, fd) };
    }
    if n <= 0 {
        return unsafe { finish(fd, -abi::EINVAL) };
    }
    // SAFETY: buffer validity is the caller/provider contract; null forwarding is intentional.
    let result = unsafe { ioctl(fd, abi::PERF_GET, counter) };
    let result = if result != 0 { unsafe { neg_errno() } } else { result };
    unsafe { finish(fd, result) }
}

/// Return the current header's number of rusage page-size categories.
#[no_mangle]
pub extern "C" fn ihk_os_get_num_pagesizes(index: c_int) -> c_int {
    // SAFETY: preserve the original accessibility/open probe before returning static metadata.
    let fd = unsafe { ihklib_os_open(index) };
    let result = if fd < 0 { fd } else { abi::IHK_MAX_NUM_PGSIZES };
    unsafe { finish(fd, result) }
}

/// Copy the selected header's rusage page-size categories in their original enum order.
///
/// # Safety
/// A nonnull `sizes` must be writable/aligned for `count` c_long values when count
/// equals IHK_MAX_NUM_PGSIZES. The storage is exclusively writable during this call.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_pagesizes(index: c_int, sizes: *mut c_long,
    count: c_int) -> c_int {
    // SAFETY: preserve open before pointer/count validation, even for invalid output arguments.
    let fd = unsafe { ihklib_os_open(index) };
    if fd < 0 {
        return unsafe { finish(fd, fd) };
    }
    if sizes.is_null() {
        return unsafe { finish(fd, -abi::EFAULT) };
    }
    if count != abi::IHK_MAX_NUM_PGSIZES {
        return unsafe { finish(fd, -abi::EINVAL) };
    }
    for (index, size) in abi::PAGE_SIZES.iter().enumerate() {
        // SAFETY: validated count equals witnessed array length; caller grants output storage.
        unsafe { sizes.add(index).write(*size) };
    }
    unsafe { finish(fd, 0) }
}
