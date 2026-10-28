#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod cls {
    unsafe extern "C" { pub fn get_this_cpu_local_var()->*mut crate::abi::CpuLocalVar; }
}
mod policy {
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use core::ffi::c_void;
    const EINVAL:CInt=22;
    type SyscallDoSyscall3Fn=unsafe extern "C" fn(CInt,CULong,CULong,CULong)->CLong;
    type ClearHostPteLogFn=unsafe extern "C" fn(CLong);
    unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe { base.add(offset).cast() } }
    // Preserve the genuine canonical foreign declaration alongside the new export.
    unsafe extern "C" {
        fn clear_host_pte(addr:CULong,len:SizeT,holding_lock:CInt)->CLong;
        fn syscall_get_processor_id_bridge()->CInt;
    }
    include!("clear-host-pte-body.current.Rust.inc");
    include!("clear-host-pte-entry.fixture.Rust.inc");
}
