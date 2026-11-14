//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Reserve-policy reporting only; unrelated to the separately owned memory dump.

use core::ffi::{c_char, c_int, c_void};
use core::ptr::addr_of;

unsafe extern "C" {
    fn geteuid() -> u32;
    fn snprintf(text: *mut c_char, size: usize, format: *const c_char, ...) -> c_int;
    fn open(path: *const c_char, flags: c_int, ...) -> c_int;
    fn strnlen(text: *const c_char, size: usize) -> usize;
    fn write(fd: c_int, text: *const c_void, size: usize) -> isize;
    fn close(fd: c_int) -> c_int;
}

unsafe fn report(format: &'static [u8], field: *const c_int) {
    // SAFETY: libc geteuid has no pointer or ownership preconditions.
    if unsafe { geteuid() } != 0 {
        return;
    }
    // printk intentionally does not consult loglevel; eprintf's shared logger
    // cannot implement this policy. Each call retains its own bounded stack text.
    let mut text = [0 as c_char; 3840];
    // SAFETY: caller serialization protects the aligned global field read; the
    // fixed format contains exactly one int conversion and a terminating NUL.
    unsafe {
        snprintf(text.as_mut_ptr(), text.len(), format.as_ptr().cast(), field.read());
    }
    // SAFETY: the constant NUL-terminated path and O_WRONLY match current printk.
    let fd = unsafe { open(b"/dev/kmsg\0".as_ptr().cast(), 1) };
    // SAFETY: snprintf leaves a NUL in the nonempty bounded array. The original
    // includes that NUL in its write length and still attempts writes on open error.
    let length = unsafe { strnlen(text.as_ptr(), text.len() - 1) } + 1;
    let mut offset = 0;
    while offset < length {
        // SAFETY: offset and remaining length describe the initialized text array;
        // libc write never writes into it and returns no more than supplied size.
        let count = unsafe { write(fd, text.as_ptr().add(offset).cast(), length - offset) };
        if count <= 0 {
            break;
        }
        offset += count as usize;
    }
    // SAFETY: preserve printk's unconditional single close, including invalid fd.
    unsafe { close(fd) };
}

/// Print the six current policy values with the original printk order and policy.
///
/// # Safety
/// Callers must serialize all accesses to the existing non-atomic configuration
/// global, just as in the original C implementation. libc must satisfy its ABI.
#[no_mangle]
pub unsafe extern "C" fn dump_reserve_mem_conf() {
    use super::runtime_state::reserve_mem_conf;
    // SAFETY: raw field addresses introduce no references to mutable static data.
    // Each report checks effective UID before reading its field, matching printk;
    // the caller's serialization contract prevents concurrent configuration writes.
    unsafe {
        report(
            b"dump_reserve_mem_conf: IHK_RESERVE_MEM_BALANCED_ENABLE=%d\n\0",
            addr_of!(reserve_mem_conf.balanced_enable),
        );
        report(
            b"dump_reserve_mem_conf: IHK_RESERVE_MEM_BALANCED_BEST_EFFORT=%d\n\0",
            addr_of!(reserve_mem_conf.balanced_best_effort),
        );
        report(
            b"dump_reserve_mem_conf: IHK_RESERVE_MEM_BALANCED_VARIANCE_LIMIT=%d\n\0",
            addr_of!(reserve_mem_conf.balanced_variance_limit),
        );
        report(
            b"dump_reserve_mem_conf: IHK_RESERVE_MEM_MIN_CHUNK_SIZE=%d\n\0",
            addr_of!(reserve_mem_conf.min_chunk_size),
        );
        report(
            b"dump_reserve_mem_conf: IHK_RESERVE_MEM_MAX_SIZE_RATIO_ALL=%d\n\0",
            addr_of!(reserve_mem_conf.max_size_ratio_all),
        );
        report(
            b"dump_reserve_mem_conf: IHK_RESERVE_MEM_TIMEOUT=%d\n\0",
            addr_of!(reserve_mem_conf.timeout),
        );
    }
}
