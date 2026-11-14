//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Current PAGE_SIZE=4096, WITH_KRM=OFF, DEBUG=OFF library state and public setters.

use core::ffi::{c_int, c_uint, c_void};
use core::ptr::addr_of_mut;

use super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf;

#[cfg(any(ihklib_fugaku_hacks, ihklib_debug))]
compile_error!("Qualify the selected optional defaults/diagnostics before enabling them");

// The original library requires callers to serialize configuration, reservation,
// logging and setters. These ABI globals intentionally preserve that contract;
// atomics or locks would change the existing C-accessible storage ABI.
#[no_mangle]
pub static mut loglevel: c_int = 1;

#[no_mangle]
pub static mut reserve_mem_conf: ReserveMemConf = ReserveMemConf {
    balanced_enable: 0,
    balanced_best_effort: 0,
    balanced_variance_limit: 0,
    min_chunk_size: 4096,
    max_size_ratio_all: 98,
    timeout: 30,
};

const _: () = {
    assert!(core::mem::size_of::<ReserveMemConf>() == 24);
    assert!(core::mem::align_of::<ReserveMemConf>() == 4);
    assert!(core::mem::offset_of!(ReserveMemConf, timeout) == 20);
};

/// Set the existing public logging level without introducing a new validation rule.
///
/// # Safety
/// Callers must serialize this write with all C and Rust accesses to loglevel,
/// exactly as required by the original non-atomic global configuration contract.
#[no_mangle]
pub unsafe extern "C" fn ihk_set_loglevel(level: c_uint) -> c_int {
    // SAFETY: caller serialization excludes concurrent non-atomic accesses; the
    // raw address avoids creating a reference to mutable static storage.
    unsafe { addr_of_mut!(loglevel).write(level as c_int) };
    0
}

/// Set one existing reserve-memory policy field with the original ordering.
///
/// # Safety
/// For a recognized key, nonnull value must point to a readable aligned C int.
/// The caller must serialize this call with reservation and all configuration
/// accesses. This function borrows value synchronously and never takes ownership.
#[no_mangle]
pub unsafe extern "C" fn ihk_reserve_mem_conf(
    index: c_int,
    key: c_int,
    value: *mut c_void,
) -> c_int {
    if value.is_null() {
        return -14;
    }

    // SAFETY: this is the unchanged Rust device-access helper, given an int index.
    let readable = unsafe { super::accepted_cpu_memory::device_readable(index) };
    if readable != 0 {
        return readable;
    }
    if !(0..=5).contains(&key) {
        // The original default branch never dereferences an unrecognized value.
        return -22;
    }

    // SAFETY: for a recognized key the caller supplies an aligned, readable int.
    let supplied = unsafe { value.cast::<c_int>().read() };
    if key == 4 && (supplied <= 0 || supplied > 98) {
        return -22;
    }

    // SAFETY: caller serialization excludes concurrent mutation/read; every field
    // belongs to the single ABI global with the reused repr(C) six-int layout.
    unsafe {
        let destination = match key {
            0 => addr_of_mut!(reserve_mem_conf.balanced_enable),
            1 => addr_of_mut!(reserve_mem_conf.balanced_best_effort),
            2 => addr_of_mut!(reserve_mem_conf.balanced_variance_limit),
            3 => addr_of_mut!(reserve_mem_conf.min_chunk_size),
            4 => addr_of_mut!(reserve_mem_conf.max_size_ratio_all),
            5 => addr_of_mut!(reserve_mem_conf.timeout),
            _ => return -22,
        };
        destination.write(supplied);
    }
    0
}
