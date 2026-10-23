#![no_std]
#![allow(dead_code)]
#[path = "baseline/kernel/rust/abi.rs"]
mod abi;
#[path = "baseline/kernel/rust/page_helpers.rs"]
mod page_helpers;
#[path = "candidate/kernel/rust/x86_memory_helpers.rs"]
mod x86_memory_helpers;
// Unselected boot diagnostics need names when type-checking the real module;
// these functions are unreachable from the focused exported callback.
mod x86_setup {
    pub fn early_phase(_tag: u8) {}
    pub fn early_panic() {
        loop { core::hint::spin_loop(); }
    }
}
