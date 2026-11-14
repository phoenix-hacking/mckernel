// SPDX-License-Identifier: GPL-2.0
#![no_std]
#![allow(unexpected_cfgs)]
mod fixture_bindings;
#[path = "mcctrl_mm_write_candidate.rs"]
mod candidate;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! {
    loop { core::hint::spin_loop(); }
}
#[no_mangle]
pub unsafe extern "C" fn m15_rust_mmap_write_lock(mm: *mut fixture_bindings::mm_struct) {
    unsafe { candidate::mmap_write_lock(mm); }
}
#[no_mangle]
pub unsafe extern "C" fn m15_rust_mmap_write_unlock(mm: *mut fixture_bindings::mm_struct) {
    unsafe { candidate::mmap_write_unlock(mm); }
}
#[no_mangle]
pub unsafe extern "C" fn m15_rust_vma_start_write(vma: *mut fixture_bindings::vm_area_struct) {
    unsafe { candidate::vma_start_write(vma); }
}
