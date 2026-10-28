#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod cls {
    unsafe extern "C" { pub fn get_this_cpu_local_var()->*mut crate::abi::CpuLocalVar; }
}
mod policy {
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use core::ffi::c_void;
    include!("do-munmap-types.current.Rust.inc");
    unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe { base.add(offset).cast() } }
    include!("do-munmap-body.current.Rust.inc");
    include!("do-munmap-entry.fixture.Rust.inc");
}
