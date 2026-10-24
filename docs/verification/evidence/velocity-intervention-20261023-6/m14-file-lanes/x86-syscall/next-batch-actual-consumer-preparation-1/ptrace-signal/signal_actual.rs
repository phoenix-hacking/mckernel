// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(unused_imports)]
#![allow(dead_code,private_interfaces)]
#[path="abi.ACTUAL-FULL.rs"]mod abi;
use core::ffi::c_void;
use core::mem::{offset_of,size_of,align_of,MaybeUninit};
use core::ptr::{read_volatile,write_volatile,addr_of,addr_of_mut,null_mut};
use abi::{CInt,CLong,CULong,SizeT,Thread,Process,SigInfo,SigInfoChild,CpuLocalVar};
use lock_helpers::McsRwlockNodeIrqsave;
use waitq::Waitq as RuntimeWaitq;
type PtraceSignalLockFn=unsafe extern "C" fn(*mut c_void,*mut c_void);
type PtraceSaveDebugregFn=unsafe extern "C" fn(*mut c_void);
type ThreadExitWakeFn=unsafe extern "C" fn(*mut c_void);
type SyscallDoKillThreadFn=unsafe extern "C" fn(*mut c_void,CInt,CInt,CInt,*const SigInfo,CInt)->CLong;
type PtraceVoidFn=unsafe extern "C" fn();
type PtraceControlLogFn=unsafe extern "C" fn(CInt,CInt,CInt);
extern "C" {
 fn fixture_signal_cpu()->*mut CpuLocalVar;
 fn fixture_signal_lock(lock:*mut c_void,node:*mut c_void);
 fn fixture_signal_unlock(lock:*mut c_void,node:*mut c_void);
 fn fixture_signal_save(p:*mut c_void);
 fn fixture_signal_wake(p:*mut c_void);
 fn kprintf(fmt:*const i8,...)->CInt;
 fn schedule();
}
mod cls {use super::*;pub unsafe fn get_this_cpu_local_var()->*mut CpuLocalVar {fixture_signal_cpu()}}
mod lock_helpers {use super::*;pub use crate::abi::McsRwlockLock;
#[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}
pub unsafe extern "C" fn __mcs_rwlock_writer_lock(l:*mut McsRwlockLock,n:*mut McsRwlockNodeIrqsave){fixture_signal_lock(l.cast(),n.cast())}
pub unsafe extern "C" fn __mcs_rwlock_writer_unlock(l:*mut McsRwlockLock,n:*mut McsRwlockNodeIrqsave){fixture_signal_unlock(l.cast(),n.cast())}}
mod x86_cpu_helpers {use super::*;pub unsafe extern "C" fn save_debugreg(p:*mut CULong){fixture_signal_save(p.cast())}}
mod waitq {use super::*;pub type Waitq=abi::Waitq;pub unsafe extern "C" fn waitq_wakeup(p:*mut Waitq){fixture_signal_wake(p.cast())}}
mod debug {
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
}
const CLD_TRAPPED: CInt = 4;
const EINVAL: CInt = 22;
const PS_TRACED: CInt = 0x40;
const PTRACE_REPORT_SIGNAL_LOG_ENTER: CInt = 8;
const PTRACE_REPORT_SIGNAL_LOG_SLEEPING: CInt = 9;
const PTRACE_REPORT_SIGNAL_LOG_WAKE: CInt = 10;
const PT_TRACED: CInt = 0x80;
const PT_TRACE_SYSCALL: CInt = 0x200;
const SIGCHLD: CInt = 17;
const SIGNAL_STOP_STOPPED: CInt = 0x1;
const SIGSTOP: CInt = 19;
const SIGTSTP: CInt = 20;
const SIGTTIN: CInt = 21;
const SIGTTOU: CInt = 22;
include!("field_ptr.ACTUAL.inc");
include!("existing-offsets.ACTUAL.inc");
include!("existing-body.ACTUAL.inc");
include!("candidate-entry.ACTUAL.inc");
#[no_mangle]pub unsafe extern "C" fn fixture_signal_Rust_ABI(i:usize)->usize {
 let x=[size_of::<Thread>(),align_of::<Thread>(),size_of::<Process>(),align_of::<Process>(),size_of::<CpuLocalVar>(),size_of::<SigInfo>(),size_of::<McsRwlockNodeIrqsave>(),align_of::<McsRwlockNodeIrqsave>(),
 F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_proc_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_tid_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_status_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_exit_status_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_signal_flags_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_ptrace_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_ptrace_debugreg_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.thread_report_proc_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.proc_pid_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.proc_parent_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.proc_main_thread_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.proc_status_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.proc_update_lock_offset as usize,F06_PTRACE_REPORT_SIGNAL_OFFSETS.proc_waitpid_q_offset as usize];x[i]
}
