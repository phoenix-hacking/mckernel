#![no_std]
#![allow(dead_code)]
#[path = "baseline/kernel/rust/abi.rs"] mod abi;
#[path = "baseline/kernel/rust/page_helpers.rs"] mod page_helpers;
#[path = "candidate/kernel/rust/x86_memory_helpers.rs"] mod x86_memory_helpers;
mod x86_setup {
    pub fn early_phase(_tag: u8) {}
    pub fn early_panic() { loop { core::hint::spin_loop(); } }
}
// Compile-time ABI witness for the actual complete Rust module's exported callback.
const _: unsafe extern "C" fn(abi::CULong) -> *mut core::ffi::c_void =
    x86_memory_helpers::x86_clear_phys_to_virt_bridge;
