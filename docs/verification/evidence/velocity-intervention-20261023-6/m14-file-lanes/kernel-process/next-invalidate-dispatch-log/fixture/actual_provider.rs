// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
mod object_helpers { include!("object_dispatch.ACTUAL-RUST.inc"); }
use core::ffi::c_void;
use abi::{CInt,CULong,SizeT,Memobj};
unsafe extern "C" { fn kprintf(format: *const i8, ...) -> CInt; }
include!("callbacks.ACTUAL-RUST.inc");
#[no_mangle]
pub unsafe extern "C" fn fixture_layout(out: *mut usize) {
    let values=[core::mem::size_of::<Memobj>(),core::mem::align_of::<Memobj>(),
        core::mem::offset_of!(Memobj,ops),core::mem::size_of::<abi::MemobjOps>(),
        core::mem::offset_of!(abi::MemobjOps,invalidate_page)];
    core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
