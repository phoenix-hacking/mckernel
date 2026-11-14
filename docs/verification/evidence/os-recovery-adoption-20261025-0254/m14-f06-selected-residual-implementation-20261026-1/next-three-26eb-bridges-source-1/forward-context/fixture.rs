// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
#[path = "abi.rs"] mod abi;
#[path = "bridge.rs"] mod bridge;
#[panic_handler] fn panic(_: &core::panic::PanicInfo<'_>) -> ! { loop {} }
extern "C" {
    #[link_name = "fixture_provider"]
    fn syscall_generic_forwarding(number: abi::CInt, context: *mut abi::X86UserContext) -> abi::CLong;
}
