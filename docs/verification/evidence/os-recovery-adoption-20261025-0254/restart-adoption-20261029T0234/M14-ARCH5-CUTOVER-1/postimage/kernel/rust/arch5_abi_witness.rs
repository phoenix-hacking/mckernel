//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Compile-only actual shared Rust types; compare against same ordered C array.
use core::mem::{size_of, align_of, offset_of};
use crate::abi::{CInt, CLong, CULong, SigInfo, SigInfoChild, Thread, SigPending,
    Process, SigCommon, X86UserContext, XsaveStruct, X86CpuLocalVariables, Tss64};
const _: unsafe extern "C" fn(*mut core::ffi::c_void) = super::syscall_signal_leaf_adapters::arch_rt_sigreturn_xrstor_bridge;
const _: unsafe extern "C" fn(CLong)->CLong = super::syscall_signal_leaf_adapters::arch_native_signal_bad_frame_bridge;
const _: unsafe extern "C" fn(*mut *mut Thread,*mut *mut X86UserContext,*mut CInt) = super::f06_signal_context_candidate::arch_rt_sigreturn_context_bridge;
const _: unsafe extern "C" fn(CULong,*mut core::ffi::c_void,*mut Thread,*mut SigPending,CInt)->CInt = super::f06_do_signal_whole_candidate::do_signal;
const _: extern "C" fn(CInt,CLong) = super::syscall_regset_defined_logger::arch_ptrace_regset_log_bridge;
#[used]
#[no_mangle]
#[link_section = ".arch5_abi_rust"]
pub static arch5_rust_abi_geometry: [u64; 61] = [
    (size_of::<CInt>()) as u64, // 0 int.size
    (align_of::<CInt>()) as u64, // 1 int.align
    (size_of::<CLong>()) as u64, // 2 long.size
    (align_of::<CLong>()) as u64, // 3 long.align
    (size_of::<CULong>()) as u64, // 4 ulong.size
    (align_of::<CULong>()) as u64, // 5 ulong.align
    (size_of::<*mut core::ffi::c_void>()) as u64, // 6 pointer.size
    (align_of::<*mut core::ffi::c_void>()) as u64, // 7 pointer.align
    (size_of::<SigInfo>()) as u64, // 8 siginfo.size
    (align_of::<SigInfo>()) as u64, // 9 siginfo.align
    (size_of::<Thread>()) as u64, // 10 thread.size
    (align_of::<Thread>()) as u64, // 11 thread.align
    (size_of::<SigPending>()) as u64, // 12 pending.size
    (align_of::<SigPending>()) as u64, // 13 pending.align
    (size_of::<Process>()) as u64, // 14 process.size
    (align_of::<Process>()) as u64, // 15 process.align
    (size_of::<SigCommon>()) as u64, // 16 sigcommon.size
    (align_of::<SigCommon>()) as u64, // 17 sigcommon.align
    (size_of::<X86UserContext>()) as u64, // 18 context.size
    (align_of::<X86UserContext>()) as u64, // 19 context.align
    (size_of::<XsaveStruct>()) as u64, // 20 xsave.size
    (align_of::<XsaveStruct>()) as u64, // 21 xsave.align
    (size_of::<crate::native_signal::Frame>()) as u64, // 22 frame.size
    (align_of::<crate::native_signal::Frame>()) as u64, // 23 frame.align
    (offset_of!(Thread,tid)) as u64, // 24 thread.tid
    (offset_of!(Thread,exit_status)) as u64, // 25 thread.exit_status
    (offset_of!(Thread,status)) as u64, // 26 thread.status
    (offset_of!(Thread,proc)) as u64, // 27 thread.proc
    (offset_of!(Thread,report_proc)) as u64, // 28 thread.report_proc
    (offset_of!(Thread,sigcommon)) as u64, // 29 thread.sigcommon
    (offset_of!(Thread,sigmask)) as u64, // 30 thread.sigmask
    (offset_of!(Thread,sigstack)) as u64, // 31 thread.sigstack
    (offset_of!(Thread,ptrace)) as u64, // 32 thread.ptrace
    (offset_of!(Thread,coredump_regs)) as u64, // 33 thread.coredump_regs
    (offset_of!(SigPending,info)) as u64, // 34 pending.info
    (offset_of!(SigPending,ptracecont)) as u64, // 35 pending.ptracecont
    (offset_of!(Process,parent)) as u64, // 36 process.parent
    (offset_of!(Process,main_thread)) as u64, // 37 process.main_thread
    (offset_of!(Process,update_lock)) as u64, // 38 process.update_lock
    (offset_of!(Process,pid)) as u64, // 39 process.pid
    (offset_of!(Process,status)) as u64, // 40 process.status
    (offset_of!(Process,group_exit_status)) as u64, // 41 process.group_exit_status
    (offset_of!(SigCommon,lock)) as u64, // 42 sigcommon.lock
    (offset_of!(SigCommon,action)) as u64, // 43 sigcommon.action
    (offset_of!(crate::native_signal::Frame,info)) as u64, // 44 frame.info
    (offset_of!(crate::native_signal::Frame,fpregs)) as u64, // 45 frame.fpregs
    (offset_of!(crate::native_signal::Frame,sigstack)) as u64, // 46 frame.sigstack
    (offset_of!(SigInfo,si_signo)) as u64, // 47 siginfo.si_signo
    (offset_of!(SigInfo,si_code)) as u64, // 48 siginfo.si_code
    (offset_of!(SigInfo,sifields)) as u64, // 49 siginfo._sifields
    (offset_of!(SigInfo,sifields)+offset_of!(SigInfoChild,si_pid)) as u64, // 50 siginfo.child.si_pid
    (offset_of!(SigInfo,sifields)+offset_of!(SigInfoChild,si_status)) as u64, // 51 siginfo.child.si_status
    (offset_of!(SigInfo,sifields)+offset_of!(SigInfoChild,si_uid)) as u64, // 52 siginfo.child.si_uid
    (offset_of!(SigInfo,sifields)+offset_of!(SigInfoChild,si_utime)) as u64, // 53 siginfo.child.si_utime
    (offset_of!(SigInfo,sifields)+offset_of!(SigInfoChild,si_stime)) as u64, // 54 siginfo.child.si_stime
    (offset_of!(X86CpuLocalVariables,tss)+offset_of!(Tss64,rsp0)) as u64, // 55 GS.rsp0
    (17) as u64, // 56 SIGCHLD
    (4) as u64, // 57 CLD_TRAPPED
    (5) as u64, // 58 SIGTRAP
    (11) as u64, // 59 SIGSEGV
    (14) as u64, // 60 EFAULT
];
