#![no_std]
#![allow(dead_code,unused_imports,unused_variables)]
use core::{ffi::{c_char,c_void},mem::{size_of,offset_of},ptr::write_volatile};
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
use abi::*;
mod cls { use super::*;
type CUInt=u32;

unsafe extern "C" {
pub fn get_this_cpu_local_var() -> *mut CpuLocalVar;
}
}
mod mem_helpers { use super::*;
type CUInt=u32;

unsafe extern "C" {
pub fn kmalloc_tracked(
    size: CInt,
    flag: CULong,
    file: *mut i8,
    line: CInt,
) -> *mut c_void;
pub fn kfree_tracked(ptr: *mut c_void, file: *mut i8, line: CInt);
}
}
mod sched_helpers { use super::*;
type CUInt=u32;

unsafe extern "C" {
pub fn check_need_resched();
}
}
mod string { use super::*;
type CUInt=u32;

unsafe extern "C" {
pub fn memcpy(
    dest: *mut c_void,
    src: *const c_void,
    n: SizeT,
) -> *mut c_void;
pub fn __inline_memset(
    s: *mut c_void,
    c: CULong,
    count: SizeT,
) -> *mut c_void;
}
}
mod lock_helpers { use super::*;
type CUInt=u32;
#[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}
unsafe extern "C" {
pub fn __mcs_rwlock_writer_lock(
    lock: *mut McsRwlockLock,
    node: *mut McsRwlockNodeIrqsave,
);
pub fn __mcs_rwlock_writer_unlock(
    lock: *mut McsRwlockLock,
    node: *mut McsRwlockNodeIrqsave,
);
}
}
mod waitq { use super::*;
type CUInt=u32;
#[repr(C)]
pub(crate) struct IhkSpinlock {
    head_tail: CUInt,
}
#[repr(C)]
pub(crate) struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}
#[repr(C)]
pub(crate) struct Waitq {
    lock: IhkSpinlock,
    waitq: ListHead,
}
unsafe extern "C" {
pub fn waitq_wakeup(waitq: *mut Waitq);
}
}
mod debug { use super::*;
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
unsafe extern "C" { pub fn kprintf(format: *const i8, ...) -> CInt; }
}
mod x86_cpu_helpers { use super::*; use core::arch::asm;
unsafe extern "C" {
pub fn get_xsave_size() -> CInt;
pub fn get_xsave_mask() -> CULong;
}
pub(crate) unsafe fn x86_save_xstate(state: *mut c_void, mask: CULong) {
    unsafe {
        core::arch::asm!(
            "xsave [{state}]",
            state = in(reg) state,
            in("eax") mask as u32,
            in("edx") (mask >> 32) as u32,
            options(nostack, preserves_flags),
        );
    }
}
pub(crate) unsafe fn x86_restore_xstate(state: *const c_void, mask: CULong) {
    unsafe {
        core::arch::asm!(
            "xrstor [{state}]",
            state = in(reg) state,
            in("eax") mask as u32,
            in("edx") (mask >> 32) as u32,
            options(nostack, preserves_flags),
        );
    }
}
}
const CLD_STOPPED: CInt = 5;
const EBUSY: CInt = 16;
const EFAULT: CInt = 14;
const ENOMEM: CInt = 12;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const PS_DELAY_STOPPED: CInt = 0x200;
const PS_DELAY_TRACED: CInt = 0x400;
const PS_STOPPED: CInt = 0x20;
const PS_TRACED: CInt = 0x40;
const PT_TRACED: CInt = 0x80;
const RFLAGS_TF: CULong = 1 << 8;
const SIGCHLD: CInt = 17;
const SIGCONT: CInt = 18;
const SIGKILL: CInt = 9;
const SIGNAL_STOP_STOPPED: CInt = 0x1;
const SIGSTOP: CInt = 19;
const SIGTRAP: CInt = 5;
const SIGTSTP: CInt = 20;
const SIGTTIN: CInt = 21;
const SIGTTOU: CInt = 22;
const SIGURG: CInt = 23;
const TRAP_TRACE: CInt = 2;
const EINTR: CInt = 4;
const SYS_EPOLL_WAIT: CULong = 232;
const SYS_NANOSLEEP: CInt = 35;
const SYS_PPOLL: CInt = 271;
const SYS_PSELECT6: CInt = 270;
unsafe fn rt_sigreturn_zero_siginfo(info: *mut SigInfo) {
    let dst = info.cast::<u8>();
    let mut offset = 0usize;

    while offset < size_of::<SigInfo>() {
        write_volatile(dst.add(offset), 0);
        offset += 1;
    }
}
pub extern "C" fn sigmask_to_signal_number(mask: CULong) -> CInt {
    let mut signal = 0;
    let mut bits = mask;

    while bits != 0 {
        signal += 1;
        bits >>= 1;
    }

    signal
}
unsafe extern "C" {
fn arch_copy_from_user_bridge(dst: *mut u8, src_addr: CULong, bytes: SizeT) -> CLong;
fn arch_copy_to_user_bridge(dst_addr: CULong, src: *const u8, bytes: SizeT) -> CLong;
fn kprintf(format: *const i8, ...) -> CInt;
pub fn ptrace_report_signal(thread: *mut Thread, sig: CInt);
fn schedule();
}
#[path="/home/holden/mckernel/kernel/rust/f06_signal_trap_info.rs"] mod f06_signal_trap_info;
#[path="/home/holden/mckernel/kernel/rust/f06_rt_sigreturn_xrstor.rs"] mod f06_rt_sigreturn_xrstor;
#[path="/home/holden/mckernel/kernel/rust/f06_signal_tail.rs"] mod f06_signal_tail;

mod native_signal { use super::*;
pub(crate) type CopyFrom = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type CopyTo = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
#[repr(C)]
pub struct Frame {
    pub(crate) flags: CULong,
    pub(crate) link: *mut c_void,
    pub(crate) sigstack: SigStack,
    pub(crate) regs: [CULong; 23],
    pub(crate) fpregs: *mut c_void,
    pub(crate) reserve: [CULong; 8],
    pub(crate) sigmask: [CULong; 16],
    pub(crate) info: SigInfo,
}
const _: () = {
    assert!(offset_of!(Frame, sigstack) == 16);
    assert!(offset_of!(Frame, regs) == 40);
    assert!(offset_of!(Frame, fpregs) == 224);
    assert!(offset_of!(Frame, sigmask) == 296);
    assert!(offset_of!(Frame, info) == 424);
    assert!(size_of::<Frame>() == 552);
};
unsafe extern "C" {
pub fn native_signal_entry_targets_result(
    handler: CULong,
    restorer: CULong,
    user_start: CULong,
    user_end: CULong,
) -> CLong;
pub fn native_signal_context_prepare_result(
    regs: *const X86UserContext,
    saved_mask: CULong,
    result: CULong,
    number: CInt,
    restart: CInt,
    frame: *mut Frame,
    copy_from: Option<CopyFrom>,
) -> CLong;
pub fn native_signal_action_mask_result(
    previous: CULong,
    action_mask: CULong,
    signal: CInt,
    flags: CULong,
) -> CULong;
pub fn native_signal_stack_prepare_result(
    stack: *const SigStack,
    saved: *mut SigStack,
    sp: CULong,
    flags: CULong,
    xsave_size: CInt,
    frame_size: SizeT,
    user_start: CULong,
    user_end: CULong,
    frame_out: *mut CULong,
    fpregs_out: *mut CULong,
) -> CLong;
pub fn native_signal_stack_publish_result(
    stack: *mut SigStack,
    frame: CULong,
    restorer: CULong,
    copy_to: Option<CopyTo>,
) -> CLong;
}
}

#[path="/home/holden/mckernel/kernel/rust/f06_signal_ptrace_diagnostics.rs"] mod f06_signal_ptrace_diagnostics;
