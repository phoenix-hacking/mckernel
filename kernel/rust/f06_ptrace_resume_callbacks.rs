// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Genuine callbacks and stack/CPU binding for the existing ptrace resume body.

#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12,
    enable_profile, enable_perf, enable_rusage, not(enable_tofu),
    not(enable_fugaku_hacks), f03_ptrace_entry_candidate)))]
compile_error!("ptrace resume callbacks require the paired ordinary x86/Linux6.12/PROFILE/whole-F06 cohort");

use core::ffi::{c_uint, c_void};
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, read_volatile};
use crate::abi::{CInt, CLong, CULong, SigInfo, SigPending};
use crate::lock_helpers as locks;

// Exact C __FILE__, tracked-free origin and Ddebug flags from the same normal
// syscall.c producer. These are source identities, not Rust file!/line! values.
const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_DO_SYSCALL_C_FILE"), "\0").as_bytes();
const INITIAL_DEBUG_FLAGS: u32 = match env!("MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("ptrace resume Ddebug flags must match the actual C definition"),
};

#[used]
#[link_section = "__verbose"]
static mut PTRACE_WAKEUP_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: SOURCE_FILE.as_ptr().cast(),
    func: b"ptrace_wakeup_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    // Original dkprintf at logical24429 under the actual selected C profile.
    line_flags: 24429 | (INITIAL_DEBUG_FLAGS << 24),
};

/// Preserve the exact event gate, mutable Ddebug gate and two32-bit arguments.
/// # Safety
/// The original kernel debug-registration/formatter environment is live. No
/// thread/process/pending-signal pointer is retained across this synchronous log.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_log_bridge(event: CInt, value: CInt, result: CInt) {
    if event == super::PTRACE_CONTROL_LOG_WAKEUP_ENTER &&
        unsafe { read_volatile(addr_of!(PTRACE_WAKEUP_DEBUG.line_flags)) } >> 24 != 0 {
        unsafe {
            crate::debug::kprintf(
                b"ptrace_wakeup_sig,pid=%d,data=%08x\n\0".as_ptr().cast(),
                value, result as c_uint,
            )
        };
    }
}

/// Acquire the genuine process update writer lock and initialize saved IRQ state.
/// # Safety
/// lock_addr names the live aligned process update lock; node names the caller's
/// exclusive64-byte IRQ-save node. The unchanged body pairs this exact lock/node
/// with its unlock before either lifetime ends. No zero-initialization is needed.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_update_lock_bridge(lock_addr: CULong, node: *mut c_void) {
    unsafe {
        locks::__mcs_rwlock_writer_lock(lock_addr as *mut locks::McsRwlockLock,
            node.cast::<locks::McsRwlockNodeIrqsave>())
    };
}

/// Release that same writer lock and restore its node's saved IRQ state.
/// # Safety
/// The same live lock and exclusive initialized node are held by this caller;
/// no intervening owner may reuse the node. Neither pointer is retained.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_update_unlock_bridge(lock_addr: CULong, node: *mut c_void) {
    unsafe {
        locks::__mcs_rwlock_writer_unlock(lock_addr as *mut locks::McsRwlockLock,
            node.cast::<locks::McsRwlockNodeIrqsave>())
    };
}

/// Retire a taken pending-signal node through the original tracked-free provider.
/// # Safety
/// The original detach/resume caller owns this allocation and has finished all
/// reads before this once-only free. The diagnostic filename/line remain the C
/// callback's original logical identity; no new lifetime or null policy is added.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_kfree_bridge(ptr: *mut c_void) {
    unsafe { crate::mem_helpers::kfree_tracked(ptr, SOURCE_FILE.as_ptr().cast_mut().cast(), 4657) };
}

/// Bind the genuine current thread, offsets, stack node and real provider callbacks.
/// # Safety
/// Per-CPU state/current thread are initialized and remain live through this
/// synchronous entry. The unchanged body owns the borrowed find_thread result
/// until its one thread_unlock, its pending-node transfer/copy/free, and the
/// same-node writer/IRQ pair. This entry acquires no extra process/thread ref.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_sig(pid: CInt, request: CLong, data: CLong) -> CInt {
    let thread = unsafe { (*crate::cls::get_this_cpu_local_var()).current };
    let mut lock_node = MaybeUninit::<locks::McsRwlockNodeIrqsave>::uninit();
    unsafe {
        super::ptrace_wakeup_sig_body_result(
            pid, request, data, thread as CULong, offset_of!(SigPending, info) as CULong,
            addr_of!(super::F03_PTRACE_IO_OFFSETS), lock_node.as_mut_ptr().cast(),
            Some(super::f03_ptrace_io_find), Some(super::f03_ptrace_io_unlock),
            Some(ptrace_wakeup_log_bridge),
            Some(super::ptrace_wakeup_state_callbacks::ptrace_wakeup_clear_saved_bridge),
            Some(super::ptrace_wakeup_step_callback::ptrace_wakeup_set_single_step_bridge),
            Some(ptrace_wakeup_update_lock_bridge),
            Some(super::ptrace_wakeup_state_callbacks::ptrace_wakeup_trace_syscall_bridge),
            Some(ptrace_wakeup_update_unlock_bridge),
            Some(super::ptrace_wakeup_state_callbacks::ptrace_wakeup_pending_take_bridge),
            Some(ptrace_detach_kfree_bridge),
            // This already-selected genuine bridge has the body's exact typed
            // SigInfo signature and the same do_kill call/unsigned-long result
            // conversion as the unchanged opaque ptrace_detach_do_kill_bridge.
            Some(super::syscall_do_kill_thread_bridge),
            Some(crate::f03_ptrace_adapters::ptrace_detach_wakeup_bridge),
        )
    }
}

const _: super::PtraceWakeupSigFn = ptrace_wakeup_sig;
const _: super::PtraceControlLogFn = ptrace_wakeup_log_bridge;
const _: super::PtraceRwlockFn = ptrace_wakeup_update_lock_bridge;
const _: super::PtraceRwlockFn = ptrace_wakeup_update_unlock_bridge;
const _: super::PtraceFreeFn = ptrace_detach_kfree_bridge;
const _: super::PtraceDoKillThreadFn = super::syscall_do_kill_thread_bridge;
const _: super::PtraceWakeupThreadFn = crate::f03_ptrace_adapters::ptrace_detach_wakeup_bridge;
const _: unsafe extern "C" fn(*mut c_void, CInt, CInt, CInt, *const c_void, CInt) -> CLong =
    crate::f03_ptrace_adapters::ptrace_detach_do_kill_bridge;
const _: unsafe extern "C" fn(*mut c_void, *mut i8, CInt) = crate::mem_helpers::kfree_tracked;
const _: unsafe extern "C" fn(*mut locks::McsRwlockLock, *mut locks::McsRwlockNodeIrqsave) =
    locks::__mcs_rwlock_writer_lock;
const _: unsafe extern "C" fn(*mut locks::McsRwlockLock, *mut locks::McsRwlockNodeIrqsave) =
    locks::__mcs_rwlock_writer_unlock;
const _: () = {
    assert!(size_of::<CInt>() == 4 && size_of::<c_uint>() == 4);
    assert!(size_of::<CLong>() == 8 && size_of::<CULong>() == 8);
    assert!(size_of::<*mut c_void>() == 8);
    assert!(size_of::<locks::McsRwlockNodeIrqsave>() == 64);
    assert!(align_of::<locks::McsRwlockNodeIrqsave>() == 64);
    assert!(size_of::<locks::McsRwlockLock>() == 64);
    assert!(align_of::<locks::McsRwlockLock>() == 64);
    assert!(size_of::<SigInfo>() == 128 && offset_of!(SigPending, info) == 24);
    assert!(size_of::<super::PtraceIoOffsets>() == 88);
    assert!(size_of::<super::PtraceSyscallOps>() == 152);
    assert!(align_of::<super::PtraceSyscallOps>() == 8);
    assert!(offset_of!(super::PtraceSyscallOps, wakeup_fn) == 8);
    assert!(super::PTRACE_CONTROL_LOG_WAKEUP_ENTER == 4);
    assert!(size_of::<crate::debug::Ddebug>() == 32);
    assert!(align_of::<crate::debug::Ddebug>() == 8);
};
