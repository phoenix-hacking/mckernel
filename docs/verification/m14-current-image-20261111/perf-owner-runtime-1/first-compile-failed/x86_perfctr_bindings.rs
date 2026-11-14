pub(crate) use crate::host_perf_bindings::x86_perfctr::*;
// Byte-identical existing function bodies; names only isolated for typed tracing.
mod host_genuine_x86_primitives {
use core::{ffi::c_void,ptr::read_volatile};
use crate::abi::{CInt,CULong,Thread};
use super::{McPerfEvent,ihk_mc_perf_get_num_counters};
const EINVAL:CInt=22;
fn counter_bit(counter:CInt)->CULong { 1_u64.wrapping_shl(counter as u32) as CULong }
pub unsafe extern "C" fn host_actual_legacy_perfctr_alloc(thread: *mut Thread, _event: *mut c_void) -> CInt {
    let mut ret = -EINVAL;
    let counters = unsafe { ihk_mc_perf_get_num_counters() };
    let mut i = 0;
    while i < counters {
        if unsafe { read_volatile(&(*thread).pmc_alloc_map) } & counter_bit(i) == 0 {
            ret = i;
            break;
        }
        i += 1;
    }
    ret
}

pub unsafe extern "C" fn host_actual_hw_perf_event_init(_event: *mut McPerfEvent) -> CInt {
    0
}

pub unsafe extern "C" fn host_actual_ihk_mc_event_set_period(_event: *mut McPerfEvent) -> CInt {
    0
}

pub unsafe extern "C" fn host_actual_ihk_mc_event_update(_event: *mut McPerfEvent) -> u64 {
    0
}
}
pub use host_genuine_x86_primitives::*;
