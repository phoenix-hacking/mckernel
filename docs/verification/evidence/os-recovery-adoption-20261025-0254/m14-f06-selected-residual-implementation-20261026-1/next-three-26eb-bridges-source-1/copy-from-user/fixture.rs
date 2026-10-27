// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
#[path = "abi.rs"] mod abi;
#[path = "bridge.rs"] mod bridge;
#[panic_handler] fn panic(_: &core::panic::PanicInfo<'_>) -> ! { loop {} }
mod x86_memory_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, SizeT};
    extern "C" {
        #[link_name = "fixture_provider"]
        pub fn copy_from_user(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt;
    }
}
