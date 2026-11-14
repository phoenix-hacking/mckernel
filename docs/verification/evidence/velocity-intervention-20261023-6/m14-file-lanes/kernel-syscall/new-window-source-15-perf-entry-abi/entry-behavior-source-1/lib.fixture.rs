// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::{read_volatile,write_volatile};
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
use abi::{AbiListHead,CInt,CLong,CULong,SizeT,SyscallRequest};
const EINVAL:CInt=22; const EFAULT:CInt=14; const ENOENT:CInt=2; const ENOMEM:CInt=12;
type SyscallCopyFromUserFn = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type PerfAttrFreqFn = unsafe extern "C" fn(*const c_void) -> CInt;
type PerfOpenAllocEventFn = unsafe extern "C" fn(*mut *mut c_void, *mut c_void) -> CInt;
type PerfCounterAllocFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type PerfOpenSyscallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type SyscallPolicyAllocFn = unsafe extern "C" fn(SizeT, CULong) -> *mut c_void;
type SyscallMckfdLongFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CLong;
type SyscallMckfdIntFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type SyscallMckfdLockFn = unsafe extern "C" fn(*mut c_void) -> CLong;
type SyscallMckfdUnlockFn = unsafe extern "C" fn(*mut c_void, CLong);
unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut abi::CpuLocalVar;
 fn ihk_mc_get_processor_id()->CInt;
}
include!("ACTUAL-EXISTING-PERF-HELPERS.rs.inc");
mod x86_cpu_helpers {use crate::abi::{X86UserContext,CInt,CULong};use core::ptr::read_volatile;
unsafe fn x86_syscall_read(uctx: *const X86UserContext, selector: CInt) -> CULong {
    if uctx.is_null() {
        return 0;
    }

    unsafe {
        match selector {
            0 => read_volatile(&(*uctx).gpr.rdi),
            1 => read_volatile(&(*uctx).gpr.rsi),
            2 => read_volatile(&(*uctx).gpr.rdx),
            3 => read_volatile(&(*uctx).gpr.r10),
            4 => read_volatile(&(*uctx).gpr.r8),
            5 => read_volatile(&(*uctx).gpr.r9),
            6 => read_volatile(&(*uctx).gpr.rax),
            7 => read_volatile(&(*uctx).gpr.orig_rax),
            8 => read_volatile(&(*uctx).gpr.rip),
            9 => read_volatile(&(*uctx).gpr.rsp),
            _ => 0,
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg0(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 0) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg1(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 1) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg2(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 2) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg3(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 3) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg4(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 4) }
}
}
mod x86_perfctr { #[repr(C,align(8))]
pub struct PerfEventAttrOpaque {
    data: [u8; 104],
}
}
include!("ENTRY-UNCHANGED-BODY-WITH-FIXTURE-ABI.rs.inc");
