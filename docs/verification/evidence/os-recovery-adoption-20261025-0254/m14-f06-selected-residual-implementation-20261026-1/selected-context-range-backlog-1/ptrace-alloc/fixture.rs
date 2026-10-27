//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Only raw pointer/scalar ABI is covered; no production CPU/allocator/VM provider.
#![no_std]
mod abi {
    pub type CInt = i32;
    pub type CLong = i64;
    pub type CULong = u64;
    pub type SizeT = usize;
    #[repr(C)] pub struct Thread { _opaque: [u8; 0] }
    #[repr(C)] pub struct X86UserContext { _opaque: [u8; 0] }
    #[repr(C)] pub struct ProcessVm { _opaque: [u8; 0] }
    #[repr(C)] pub struct VmRange { _opaque: [u8; 0] }
    #[repr(C)] pub struct MemObj { _opaque: [u8; 0] }
}
mod mem_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, CULong};
    unsafe extern "C" {
        pub fn kmalloc_tracked(size: CInt, flags: CULong, file: *mut i8, line: CInt) -> *mut c_void;
    }
}
#[cfg(f06_ptrace_alloc_candidate)]
#[path = "f06_ptrace_alloc.rs"]
mod adapter;
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo<'_>) -> ! {
    loop { core::hint::spin_loop(); }
}
