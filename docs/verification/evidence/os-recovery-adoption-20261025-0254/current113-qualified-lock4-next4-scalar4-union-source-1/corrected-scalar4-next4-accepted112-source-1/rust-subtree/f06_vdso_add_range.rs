// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing adapter; current-stack/allocation/VM ownership remains with provider.
use core::ptr::null_mut;

use crate::abi::{CInt, CULong, ProcessVm, VmRange};

use super::PAGE_SHIFT;

/// # Safety
/// Same live VM, exclusion, range and writable output requirements as the real
/// add_process_memory_range entry. This adapter performs one synchronous call;
/// ownership and partial-failure behavior belong to that existing provider.
#[no_mangle]
pub unsafe extern "C" fn arch_vdso_add_range_bridge(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    flags: CULong,
    range: *mut *mut VmRange,
) -> CInt {
    // SAFETY: preserve all ten original arguments, including NOPHYS, null
    // memobj/private_data, zero offset and base PAGE_SHIFT; no extra validation.
    unsafe {
        crate::process_helpers::add_process_memory_range(
            vm, start, end, CULong::MAX, flags, null_mut(), 0,
            PAGE_SHIFT as CInt, null_mut(), range,
        )
    }
}
