// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Genuine current-process, diagnostic and termination edges of sys_exit_group.

#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12, enable_profile)))]
compile_error!("exit_group bridges require the paired x86_64/linux-6.12/PROFILE profile");

use core::ptr::{addr_of, read_volatile};
use crate::abi::CInt;

// Reuse the same actual syscall.c spelling and DDEBUG_DEFAULT binding already
// asserted by the selected real outer-entry C recipe. No Rust file!/line! origin.
const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_DO_SYSCALL_C_FILE"), "\0").as_bytes();
const INITIAL_DEBUG_FLAGS: u32 = match env!("MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("exit_group DDEBUG flags must match the C definition"),
};

#[used]
#[link_section = "__verbose"]
static mut EXIT_GROUP_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: SOURCE_FILE.as_ptr().cast(),
    func: b"exit_group_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    // Original dkprintf logical line under actual OFFLOAD/POLICY/DISPATCH.
    line_flags: 5682 | (INITIAL_DEBUG_FLAGS << 24),
};

unsafe extern "C" {
    // Genuine current project provider. Its C ownership remains explicit until
    // the separately reviewed complete Rust terminate port is actually selected.
    fn terminate(status: CInt, group: CInt);
}

/// Preserve the original debug gate and exact signed-int diagnostic.
/// # Safety
/// The existing kernel formatter/debug-registration environment is live. This
/// retains no process/thread pointer or reference across the formatter.
#[no_mangle]
pub unsafe extern "C" fn exit_group_log_bridge(pid: CInt) {
    if unsafe { read_volatile(addr_of!(EXIT_GROUP_DEBUG.line_flags)) } >> 24 != 0 {
        unsafe { crate::debug::kprintf(b"sys_exit_group,pid=%d\n\0".as_ptr().cast(), pid) };
    }
}

/// Forward the two original C-int arguments to the real termination endpoint.
/// # Safety
/// Current CPU/thread/process, caller stack, locks and IRQ/preemption state obey
/// terminate's existing complete contract. No refcount or lifecycle authority is
/// created here. The endpoint is void, so preserve a possible ordinary return.
#[no_mangle]
pub unsafe extern "C" fn exit_group_terminate_bridge(status: CInt, group: CInt) {
    unsafe { terminate(status, group) };
}

/// Read the original current CPU -> thread -> process -> signed PID chain once.
/// # Safety
/// Actual per-CPU state/current thread/process are initialized, nonnull and live
/// through these original synchronous loads. No process reference is acquired,
/// released or retained, and no lock/IRQ/preemption policy is changed.
#[no_mangle]
pub unsafe extern "C" fn exit_group_current_pid_bridge() -> CInt {
    let thread = unsafe { (*crate::cls::get_this_cpu_local_var()).current };
    unsafe { (*(*thread).proc).pid }
}

const _: unsafe extern "C" fn(CInt) = exit_group_log_bridge;
const _: unsafe extern "C" fn(CInt, CInt) = exit_group_terminate_bridge;
const _: unsafe extern "C" fn() -> CInt = exit_group_current_pid_bridge;
