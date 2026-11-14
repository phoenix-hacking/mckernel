// SPDX-License-Identifier: GPL-2.0
//! Inert exact-SDK leaf codegen probe; no module init or execution.
#![no_std]
extern crate kernel;
#[path = "mcctrl_mm_write.rs"]
mod candidate;
/// Acquire the exact pinned mmap write epoch.
///
/// # Safety
/// The caller must satisfy the corresponding Linux MM operation preconditions.
#[no_mangle]
pub unsafe extern "C" fn m15_probe_lock(mm: *mut kernel::bindings::mm_struct) {
    unsafe { candidate::mmap_write_lock(mm); }
}
/// Release the exact pinned mmap write epoch.
///
/// # Safety
/// The caller must satisfy the corresponding Linux MM operation preconditions.
#[no_mangle]
pub unsafe extern "C" fn m15_probe_unlock(mm: *mut kernel::bindings::mm_struct) {
    unsafe { candidate::mmap_write_unlock(mm); }
}
/// Publish one pinned VMA write epoch.
///
/// # Safety
/// The caller must satisfy the corresponding Linux MM operation preconditions.
#[no_mangle]
pub unsafe extern "C" fn m15_probe_vma(vma: *mut kernel::bindings::vm_area_struct) {
    unsafe { candidate::vma_start_write(vma); }
}
