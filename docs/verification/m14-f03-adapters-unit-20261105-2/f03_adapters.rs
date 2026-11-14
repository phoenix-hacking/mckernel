#![no_std]
#![allow(dead_code,unused_imports)]
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
mod lock_helpers { use crate::abi::*;
#[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}
}
mod cls { use crate::abi::*; unsafe extern "C" {
pub fn get_this_cpu_local_var() -> *mut CpuLocalVar;
}}
mod x86_local { use crate::abi::*; unsafe extern "C" {
pub fn ihk_mc_get_processor_id() -> CInt;
}}
mod syscall_policy { use crate::abi::*; use core::ffi::c_void;
type SyscallFindProcessFn = unsafe extern "C" fn(CInt, *mut c_void) -> *mut c_void;
type SyscallProcessUnlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type TerminateHostRefSetFn = unsafe extern "C" fn(*mut c_void, CInt);
type WaitThreadSideEffectFn = unsafe extern "C" fn(*mut c_void);
type SyscallDoKillThreadFn =
    unsafe extern "C" fn(*mut c_void, CInt, CInt, CInt, *const SigInfo, CInt) -> CLong;
type SyscallRequestCallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type SyscallGetcredFn = unsafe extern "C" fn(*mut CInt) -> *mut CInt;
unsafe extern "C" {
pub fn syscall_generic_forwarding_body_result(
    request: *mut SyscallRequest,
    n: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
    arg3: CULong,
    arg4: CULong,
    arg5: CULong,
    cpu: CInt,
    do_syscall_fn: Option<SyscallRequestCallFn>,
) -> CLong;
pub fn terminate_host_body_result(
    pid: CInt,
    detached_thread: *mut c_void,
    current_thread: *mut c_void,
    lock_arg: *mut c_void,
    proc_nohost_offset: SizeT,
    thread_proc_offset: SizeT,
    thread_refcount_offset: SizeT,
    find_fn: Option<SyscallFindProcessFn>,
    unlock_fn: Option<SyscallProcessUnlockFn>,
    ref_set_fn: Option<TerminateHostRefSetFn>,
    release_thread_fn: Option<WaitThreadSideEffectFn>,
    release_process_fn: Option<WaitThreadSideEffectFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
) -> CLong;
pub fn syscall_refresh_cred_fields_body_result(
    thread: *mut c_void,
    scratch: *mut CInt,
    thread_proc_offset: SizeT,
    field0_offset: SizeT,
    field1_offset: SizeT,
    field2_offset: SizeT,
    field3_offset: SizeT,
    value0_index: SizeT,
    value1_index: SizeT,
    value2_index: SizeT,
    value3_index: SizeT,
    getcred_fn: Option<SyscallGetcredFn>,
) -> CInt;
pub fn getcred(raw_buf: *mut CInt) -> *mut CInt;
}}
#[path="/home/holden/mckernel/kernel/rust/f03_forward_adapters.rs"] mod f03_forward_adapters;
#[path="/home/holden/mckernel/kernel/rust/f03_ptrace_adapters.rs"] mod f03_ptrace_adapters;
#[path="/home/holden/mckernel/kernel/rust/f03_host_cleanup.rs"] mod f03_host_cleanup;
#[path="/home/holden/mckernel/kernel/rust/f03_credential_refresh.rs"] mod f03_credential_refresh;
