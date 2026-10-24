// SPDX-License-Identifier: GPL-2.0
// Exact-SDK leaf codegen probe only: no module metadata/load/init, no execution.
#![no_std]
extern crate kernel;
#[path = "mcctrl_mm_write_candidate.rs"]
mod candidate;
#[no_mangle]
pub unsafe extern "C" fn m15_probe_lock(mm: *mut kernel::bindings::mm_struct) {
    unsafe { candidate::mmap_write_lock(mm); }
}
#[no_mangle]
pub unsafe extern "C" fn m15_probe_unlock(mm: *mut kernel::bindings::mm_struct) {
    unsafe { candidate::mmap_write_unlock(mm); }
}
#[no_mangle]
pub unsafe extern "C" fn m15_probe_vma(vma: *mut kernel::bindings::vm_area_struct) {
    unsafe { candidate::vma_start_write(vma); }
}
