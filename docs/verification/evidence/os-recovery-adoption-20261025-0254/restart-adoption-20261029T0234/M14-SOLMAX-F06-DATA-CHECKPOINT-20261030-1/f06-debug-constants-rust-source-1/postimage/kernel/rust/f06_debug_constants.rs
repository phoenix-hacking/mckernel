//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Selected x86_64 `debug_constants` data provider, not a runtime initializer.

use core::mem::{align_of, offset_of, size_of};
use crate::abi::{CpuLocalVar, Process, Thread};

const _: () = {
    assert!(size_of::<usize>() == 8);
    assert!(align_of::<usize>() == 8);
    assert!(size_of::<[usize; 12]>() == 96);
};

/// Existing external consumers access writable static storage under their original
/// synchronization/lifetime contract. Rust must not create references to this
/// static while an external writer may access it; no runtime initialization runs.
#[export_name = "debug_constants"]
pub static mut F06_DEBUG_CONSTANTS: [usize; 12] = [
    size_of::<CpuLocalVar>(),
    offset_of!(CpuLocalVar, current),
    offset_of!(CpuLocalVar, runq),
    offset_of!(CpuLocalVar, status),
    offset_of!(CpuLocalVar, idle),
    offset_of!(Thread, ctx),
    offset_of!(Thread, sched_list),
    offset_of!(Thread, proc),
    offset_of!(Thread, status),
    offset_of!(Process, pid),
    offset_of!(Thread, tid),
    usize::MAX,
];
