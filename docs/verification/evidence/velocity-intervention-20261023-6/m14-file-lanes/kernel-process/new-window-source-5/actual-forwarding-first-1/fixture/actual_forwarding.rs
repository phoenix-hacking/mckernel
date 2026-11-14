// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path = "../source/kernel/rust/abi.rs"]
pub mod abi;
const IHK_MC_AP_NOWAIT: abi::CULong = 2;
mod mem_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, CULong};
    unsafe extern "C" {
        fn fixture_tracked_alloc(size: CInt, flags: CULong, file: *mut i8, line: CInt) -> *mut c_void;
        fn fixture_tracked_free(ptr: *mut c_void, file: *mut i8, line: CInt);
    }
    pub unsafe fn kmalloc_tracked(size: CInt, flags: CULong, file: *mut i8, line: CInt) -> *mut c_void {
        unsafe { fixture_tracked_alloc(size, flags, file, line) }
    }
    pub unsafe fn kfree_tracked(ptr: *mut c_void, file: *mut i8, line: CInt) {
        unsafe { fixture_tracked_free(ptr, file, line) };
    }
}
include!("tracked_allocator_providers.ACTUAL-RUST.inc");
