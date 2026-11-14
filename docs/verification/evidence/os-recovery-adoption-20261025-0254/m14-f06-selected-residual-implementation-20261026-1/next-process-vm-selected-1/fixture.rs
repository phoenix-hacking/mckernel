//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! HOST fixture for the one adapter, with the existing CPU-provider effect controlled.
#![no_std]

mod abi {
    pub type CInt = i32;
    pub type CULong = u64;
}

mod x86_cpu_helpers {
    use crate::abi::{CInt, CULong};

    unsafe extern "C" {
        pub fn ihk_mc_arch_set_special_register(reg_type: CInt, value: CULong) -> CInt;
    }
}

#[cfg(f06_prctl_set_register_candidate)]
#[path = "f06_prctl_set_register.rs"]
mod bridge;

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo<'_>) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
