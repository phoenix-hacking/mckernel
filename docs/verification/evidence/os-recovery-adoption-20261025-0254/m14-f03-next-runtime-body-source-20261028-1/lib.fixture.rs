#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod x86_cpu_helpers {
    use crate::abi::{CInt,CULong,X86UserContext};
    use core::ptr::read_volatile;
    include!("syscall-getters.current.Rust.inc");
}
mod policy {
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use core::ffi::c_void;
    use core::ptr::{read_volatile,write_volatile};
    const EINVAL:CInt=22;
    type PerfDoMmapFn=unsafe extern "C" fn(CULong,SizeT,CInt,CInt,CInt,CLong,CInt,*mut c_void)->CLong;
    unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe { base.add(offset).cast() } }
    include!("perf-mmap-body.current.Rust.inc");
    include!("perf-mmap-entry.fixture.Rust.inc");
}
