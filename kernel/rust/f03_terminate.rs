//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Genuine supported-profile process termination, over existing real providers.
use core::ffi::c_void;
use core::mem::{offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, null, null_mut, read_volatile};
use crate::abi::{AbiListHead, CInt, CLong, CULong, Process, SigInfo, SyscallRequest, Thread, TimeSpec, PROCESS_HASH_SIZE};
use crate::lock_helpers::{self as locks, McsRwlockNodeIrqsave};
use crate::process_helpers as process;
use crate::syscall_policy::{self as policy, McsRwlockNode};

#[cfg(any(not(target_arch = "x86_64"), not(native_linux_irq_work_v6_12), not(enable_profile), enable_tofu, dcfa_kmod))]
compile_error!("terminate requires the selected x86_64 Linux6.12 PROFILE non-TOFU non-DCFA profile");

const PS_EXITED: CInt = 0x10;
const SIGKILL: CInt = 9;
const SYS_EXIT_GROUP: CInt = 231;
const IHK_MC_AP_NOWAIT: CULong = 2;
const CHILD_FREE_ZOMBIE: CInt = 1;
const CHILD_REPARENT: CInt = 2;
const CHILD_REPARENT_PTRACED: CInt = 3;
const SOURCE_FILE: *const i8 = concat!(env!("MCKERNEL_TERMINATE_C_FILE"), "\0").as_ptr().cast();
const FUNCTION: *const i8 = b"terminate\0".as_ptr().cast();

// The three original DDEBUG_NONE records, with actual selected syscall.c lines.
#[used]
#[link_section = "__verbose"]
static mut TERMINATE_DEBUG: [crate::debug::Ddebug; 3] = [
    crate::debug::Ddebug { file: SOURCE_FILE, func: FUNCTION, fmt: null(), line_flags: 5271 },
    crate::debug::Ddebug { file: SOURCE_FILE, func: FUNCTION, fmt: null(), line_flags: 5292 },
    crate::debug::Ddebug { file: SOURCE_FILE, func: FUNCTION, fmt: null(), line_flags: 5511 },
];

unsafe extern "C" {
    fn sync_child_event(event: *mut c_void);
    fn schedule();
    fn ihk_mc_get_processor_id() -> CInt;
    fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;
    fn do_kill(thread: *mut Thread, pid: CInt, tid: CInt, sig: CInt, info: *mut SigInfo, ptracecont: CInt) -> CULong;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn panic(message: *const i8);
}

unsafe fn debug_enabled(index: usize) -> bool {
    unsafe { read_volatile(addr_of!(TERMINATE_DEBUG[index].line_flags)) >> 24 != 0 }
}

unsafe fn thread_from_siblings(link: *mut AbiListHead) -> *mut Thread {
    unsafe { link.cast::<u8>().sub(offset_of!(Thread, siblings_list)).cast() }
}

// Preserve the real C terminate_mcexec transaction at this call boundary, rather
// than calling the remaining project-C wrapper. Existing body/provider ABIs and
// ignored long result remain unchanged. No new callback mechanism is introduced.
/// Notify the existing Linux executor of the original process exit transaction.
///
/// # Safety
/// The original initialized per-CPU current Thread and its Process remain live
/// throughout the synchronous selected body/offload call. The pending-signal
/// caller has released its reader IRQ lock before entry. This entry adds no
/// lock, reference, context change, request publication, or retained pointer.
/// The body owns its existing field initialization and CAS/nohost protocol;
/// its signed long result remains deliberately ignored by this void C ABI.
#[cfg_attr(f03_terminate_host_provider_candidate, no_mangle)]
pub unsafe extern "C" fn terminate_mcexec(rc: CInt, sig: CInt) {
    let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
    let current = unsafe { addr_of!((*cpu).current).read() };
    let proc = unsafe { addr_of!((*current).proc).read() };
    // The actual terminal callers released their original IRQ/hash/update
    // locks. Drain only this current Process before its real exit-group/nohost
    // transition; nonlast do_exit never enters this Process-wide hook.
    #[cfg(f03_perf_owner_protocol)]
    unsafe { policy::f03_perf_owner::terminal_current_process() };
    let mut request = MaybeUninit::<SyscallRequest>::uninit();
    let _ = unsafe {
        policy::terminate_mcexec_body_result(
            proc.cast(), request.as_mut_ptr(), rc, sig, ihk_mc_get_processor_id(), SYS_EXIT_GROUP,
            offset_of!(Process, group_exit_status), offset_of!(Process, nohost),
            Some(crate::atomic_helpers::atomic_cmpxchg_ulong), Some(do_syscall),
        )
    };
}

// Actual production types, with no callback-address cast or stub provider.
const _: unsafe extern "C" fn(CInt, CInt) = terminate_mcexec;
const _: unsafe extern "C" fn(*mut CULong, CULong, CULong) -> CULong =
    crate::atomic_helpers::atomic_cmpxchg_ulong;
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = do_syscall;

#[cfg(all(f03_terminate_host_provider_candidate, any(not(enable_perf),
    not(enable_rusage), enable_fugaku_hacks, f03_forward_adapters_candidate,
    f03_signal_forward_defined_candidate)))]
compile_error!("terminate_mcexec public provider requires the paired ordinary profile");

#[cfg(f03_terminate_host_provider_candidate)]
const _: () = {
    use core::mem::align_of;
    use crate::abi::CpuLocalVar;
    assert!(size_of::<CInt>() == 4 && size_of::<CLong>() == 8
        && size_of::<CULong>() == 8 && size_of::<*mut c_void>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8
        && offset_of!(SyscallRequest, rtid) == 0 && offset_of!(SyscallRequest, ttid) == 4
        && offset_of!(SyscallRequest, valid) == 8 && offset_of!(SyscallRequest, number) == 16
        && offset_of!(SyscallRequest, args) == 24);
    assert!(size_of::<CpuLocalVar>() == 8128 && align_of::<CpuLocalVar>() == 64
        && offset_of!(CpuLocalVar, current) == 7848);
    assert!(size_of::<Thread>() == 5568 && align_of::<Thread>() == 64
        && offset_of!(Thread, proc) == 4304);
    assert!(size_of::<Process>() == 1728 && align_of::<Process>() == 64
        && offset_of!(Process, group_exit_status) == 424 && offset_of!(Process, nohost) == 500);
};

/// Preserve the original supported terminate transaction and void return ABI.
///
/// # Safety
/// The caller owns the original live current Thread/Process/VM/resource-set/pid1,
/// initialized accounting/perf state and intrusive lists. Genuine helpers retain
/// their original lock/IRQ/reference contracts. In particular, finalization and
/// thread release do not permit use of a destroyed Process/VM/current stack.
/// This entry acquires no new reference or native/current-stack authority. There
/// is no RAII guard whose destructor could change release or schedule ordering.
#[no_mangle]
pub unsafe extern "C" fn terminate(rc: CInt, sig: CInt) {
    // Keep both original current-CPU lookups and their read order.
    let resource_cpu = unsafe { crate::cls::get_this_cpu_local_var() };
    let resources = unsafe { addr_of!((*resource_cpu).resource_set).read() };
    let current_cpu = unsafe { crate::cls::get_this_cpu_local_var() };
    let current = unsafe { addr_of!((*current_cpu).current).read() };
    let proc = unsafe { addr_of!((*current).proc).read() };
    let pid1 = unsafe { addr_of!((*resources).pid1).read() };
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let mut update = MaybeUninit::<McsRwlockNode>::uninit();
    let mut children = MaybeUninit::<McsRwlockNode>::uninit();
    let mut init_children = MaybeUninit::<McsRwlockNode>::uninit();
    let mut accounting = MaybeUninit::<TimeSpec>::uninit();

    #[cfg(f03_perf_owner_protocol)]
    unsafe{crate::f03_perf_owner::sync_monitor(proc,current);}
    #[cfg(not(f03_perf_owner_protocol))]
    if !unsafe { addr_of!((*proc).monitoring_event).read() }.is_null() {
        // The C code reloads this field at the actual call.
        unsafe { sync_child_event(addr_of!((*proc).monitoring_event).read()) };
    }
    // The ABI field and runtime provider use distinct Rust nominal types for the
    // same selected C mcs_rwlock_lock: repr(C), align64, one four-byte ticket lock
    // at offset0. Existing provider-module assertions bind its private slock and
    // atomic head_tail offsets; the local assertions below and paired C guard bind
    // the ABI view. Cast only these lock addresses at the existing unsafe calls;
    // never copy the lock, borrow it across a call, or change its provider/state.
    unsafe {
        locks::__mcs_rwlock_writer_lock_noirq(addr_of_mut!((*proc).update_lock).cast::<locks::McsRwlockLock>(), update.as_mut_ptr().cast());
        locks::__mcs_rwlock_writer_lock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
    }
    if policy::terminate_process_exited_result(unsafe { addr_of!((*proc).status).read() }) != 0 {
        if unsafe { debug_enabled(0) } {
            unsafe { kprintf(b"%s: PID: %d, TID: %d PS_EXITED already\n\0".as_ptr().cast(), FUNCTION, addr_of!((*proc).pid).read(), addr_of!((*current).tid).read()); }
        }
        unsafe {
            crate::cls::preempt_disable();
            policy::tsc_to_ts(addr_of!((*current).user_tsc).read(), accounting.as_mut_ptr());
            crate::timer::ts_add(addr_of_mut!((*proc).utime), accounting.as_ptr());
            policy::tsc_to_ts(addr_of!((*current).system_tsc).read(), accounting.as_mut_ptr());
            crate::timer::ts_add(addr_of_mut!((*proc).stime), accounting.as_ptr());
            addr_of_mut!((*current).user_tsc).write(0);
            addr_of_mut!((*current).system_tsc).write(0);
            addr_of_mut!((*current).status).write(PS_EXITED);
            addr_of_mut!((*current).exit_status).write(addr_of!((*proc).group_exit_status).read() as CInt);
            policy::f03_thread_exit_signal_v1(current);
            locks::__mcs_rwlock_writer_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
            locks::__mcs_rwlock_writer_unlock_noirq(addr_of_mut!((*proc).update_lock).cast::<locks::McsRwlockLock>(), update.as_mut_ptr().cast());
            process::release_thread(current);
            crate::cls::preempt_enable();
            schedule();
        }
        // Original early branch returns if its scheduler unexpectedly returns.
        return;
    }
    if unsafe { debug_enabled(1) } {
        unsafe { kprintf(b"%s: PID: %d, TID: %d setting PS_EXITED\n\0".as_ptr().cast(), FUNCTION, addr_of!((*proc).pid).read(), addr_of!((*current).tid).read()); }
    }
    unsafe {
        policy::tsc_to_ts(addr_of!((*current).user_tsc).read(), accounting.as_mut_ptr());
        crate::timer::ts_add(addr_of_mut!((*proc).utime), accounting.as_ptr());
        policy::tsc_to_ts(addr_of!((*current).system_tsc).read(), accounting.as_mut_ptr());
        crate::timer::ts_add(addr_of_mut!((*proc).stime), accounting.as_ptr());
        addr_of_mut!((*current).user_tsc).write(0);
        addr_of_mut!((*current).system_tsc).write(0);
        let exit_status = policy::terminate_status_result(rc, sig);
        addr_of_mut!((*proc).group_exit_status).write(exit_status as CULong);
        addr_of_mut!((*current).exit_status).write(exit_status);
        addr_of_mut!((*proc).status).write(PS_EXITED);
        locks::__mcs_rwlock_writer_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
        locks::__mcs_rwlock_writer_unlock_noirq(addr_of_mut!((*proc).update_lock).cast::<locks::McsRwlockLock>(), update.as_mut_ptr().cast());
        terminate_mcexec(rc, sig);
        locks::__mcs_rwlock_writer_lock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
        process::process_list_detach_result(addr_of_mut!((*current).siblings_list));
        locks::__mcs_rwlock_writer_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
        locks::__mcs_rwlock_reader_lock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
    }
    let head = unsafe { addr_of_mut!((*proc).threads_list) };
    let mut count: CInt = 0;
    let mut link = unsafe { addr_of!((*head).next).read() };
    while link != head {
        let other = unsafe { thread_from_siblings(link) };
        if policy::terminate_thread_is_other_result(other.cast(), current.cast()) != 0 {
            count = count.wrapping_add(1);
        }
        link = unsafe { addr_of!((*link).next).read() };
    }
    let mut ids: *mut CInt = null_mut();
    if count != 0 {
        ids = unsafe {
            crate::mem_helpers::kmalloc_tracked(
                size_of::<CInt>().wrapping_mul(count as usize) as CInt,
                IHK_MC_AP_NOWAIT, SOURCE_FILE.cast_mut(), 5346,
            ).cast()
        };
        if !ids.is_null() {
            let mut index: CInt = 0;
            link = unsafe { addr_of!((*head).next).read() };
            while link != head {
                let other = unsafe { thread_from_siblings(link) };
                if policy::terminate_thread_is_other_result(other.cast(), current.cast()) != 0 {
                    unsafe { ids.offset(index as isize).write(addr_of!((*other).tid).read()) };
                    index = index.wrapping_add(1);
                }
                link = unsafe { addr_of!((*link).next).read() };
            }
        }
    }
    unsafe { locks::__mcs_rwlock_reader_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr()) };
    if !ids.is_null() {
        let mut index: CInt = 0;
        while index < count {
            let _ = unsafe { do_kill(current, addr_of!((*proc).pid).read(), ids.offset(index as isize).read(), SIGKILL, null_mut(), 0) };
            index = index.wrapping_add(1);
        }
        unsafe { crate::mem_helpers::kfree_tracked(ids.cast(), SOURCE_FILE.cast_mut(), 5363) };
    }
    // Preserve allocation-failure behavior: no peer kill, then the same active
    // thread scan/scheduler loop. Do not add an error, timeout or lock shortcut.
    loop {
        unsafe { locks::__mcs_rwlock_reader_lock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr()) };
        let mut found = false;
        link = unsafe { addr_of!((*head).next).read() };
        while link != head {
            let other = unsafe { thread_from_siblings(link) };
            if policy::terminate_thread_active_result(unsafe { addr_of!((*other).status).read() }) != 0 {
                found = true;
                break;
            }
            link = unsafe { addr_of!((*link).next).read() };
        }
        unsafe { locks::__mcs_rwlock_reader_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr()) };
        if !found { break; }
        unsafe { schedule() };
    }
    unsafe {
        locks::__mcs_rwlock_writer_lock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
        process::process_list_add_tail_result(addr_of_mut!((*current).siblings_list), addr_of_mut!((*proc).threads_list));
        locks::__mcs_rwlock_writer_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
    }
    let vm = unsafe { addr_of!((*proc).vm).read() };
    unsafe { process::free_all_process_memory_range(vm) };
    if !unsafe { addr_of!((*proc).saved_cmdline).read() }.is_null() {
        unsafe { crate::mem_helpers::kfree_tracked(addr_of!((*proc).saved_cmdline).read().cast(), SOURCE_FILE.cast_mut(), 5403) };
    }
    let report_head = unsafe { addr_of_mut!((*proc).report_threads_list) };
    while unsafe { addr_of!((*report_head).next).read() } != report_head {
        let entry = unsafe { addr_of!((*report_head).next).read() };
        let reported = unsafe { entry.cast::<u8>().sub(offset_of!(Thread, report_siblings_list)).cast::<Thread>() };
        if policy::terminate_report_thread_ptrace_result(unsafe { addr_of!((*reported).ptrace).read() }) != 0 {
            let release_flag = policy::terminate_report_thread_release_needed_result(
                (unsafe { addr_of!((*reported).proc).read() } == proc) as CInt,
                unsafe { addr_of!((*reported).termsig).read() },
            );
            if release_flag != 0 {
                let _ = unsafe { process::process_thread_termsig_clear_result(reported.cast(), offset_of!(Thread, termsig) as CULong, release_flag) };
            }
            unsafe { policy::f03_ptrace_detach_thread_v1(reported, 0) };
            if release_flag != 0 { unsafe { process::release_thread(reported) }; }
        } else {
            unsafe {
                locks::__mcs_rwlock_writer_lock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
                let _ = process::process_thread_report_detach_result(reported.cast(), offset_of!(Thread, report_proc) as CULong, null_mut(), addr_of_mut!((*reported).report_siblings_list));
                locks::__mcs_rwlock_writer_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
                process::release_thread(reported);
            }
        }
        // Never access reported after a releasing helper; reload the list head.
    }
    let children_empty = unsafe { addr_of!((*proc).children_list.next).read() == addr_of_mut!((*proc).children_list) } as CInt;
    let ptraced_empty = unsafe { addr_of!((*proc).ptraced_children_list.next).read() == addr_of_mut!((*proc).ptraced_children_list) } as CInt;
    if policy::terminate_child_cleanup_needed_result(children_empty, ptraced_empty) != 0 {
        let mut bucket = 0usize;
        while bucket < PROCESS_HASH_SIZE {
            // Reload resource_set->process_hash as the C expression does.
            let hash = unsafe { addr_of!((*resources).process_hash).read() };
            unsafe { locks::__mcs_rwlock_writer_lock(addr_of_mut!((*hash).lock[bucket]).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr()) };
            let current_hash = unsafe { addr_of!((*resources).process_hash).read() };
            let bucket_head = unsafe { addr_of_mut!((*current_hash).list[bucket]) };
            let mut child_link = unsafe { addr_of!((*bucket_head).next).read() };
            while child_link != bucket_head {
                // Capture the next link BEFORE any detach/reparent/final release.
                let next = unsafe { addr_of!((*child_link).next).read() };
                let child = unsafe { child_link.cast::<u8>().sub(offset_of!(Process, hash_list)).cast::<Process>() };
                let mut free_child: CInt = 0;
                unsafe { locks::__mcs_rwlock_writer_lock_noirq(addr_of_mut!((*child).update_lock).cast::<locks::McsRwlockLock>(), update.as_mut_ptr().cast()) };
                match policy::terminate_child_action_result(
                    (unsafe { addr_of!((*child).ppid_parent).read() } == proc) as CInt,
                    (unsafe { addr_of!((*child).parent).read() } == proc) as CInt,
                    unsafe { addr_of!((*child).status).read() },
                ) {
                    CHILD_FREE_ZOMBIE => unsafe {
                        let _ = process::process_list_del_init_result(addr_of_mut!((*child).hash_list));
                        let _ = process::process_list_del_init_result(addr_of_mut!((*child).siblings_list));
                        free_child = 1;
                    },
                    action @ (CHILD_REPARENT | CHILD_REPARENT_PTRACED) => {
                        // The original order is exiting parent's lock, then pid1.
                        unsafe {
                            locks::__mcs_rwlock_writer_lock_noirq(addr_of_mut!((*proc).children_lock).cast::<locks::McsRwlockLock>(), children.as_mut_ptr().cast());
                            locks::__mcs_rwlock_writer_lock_noirq(addr_of_mut!((*pid1).children_lock).cast::<locks::McsRwlockLock>(), init_children.as_mut_ptr().cast());
                        }
                        // Keep the pre-lock switch decision; do not reload parent.
                        let ordinary_child = action == CHILD_REPARENT;
                        let _ = unsafe { process::process_child_reparent_result(
                            child.cast(), offset_of!(Process, ppid_parent) as CULong,
                            offset_of!(Process, parent) as CULong, pid1.cast(),
                            if ordinary_child { addr_of_mut!((*child).siblings_list) } else { addr_of_mut!((*child).ptraced_siblings_list) },
                            if ordinary_child { addr_of_mut!((*pid1).children_list) } else { addr_of_mut!((*pid1).ptraced_children_list) },
                            ordinary_child as CInt,
                        ) };
                        unsafe {
                            locks::__mcs_rwlock_writer_unlock_noirq(addr_of_mut!((*pid1).children_lock).cast::<locks::McsRwlockLock>(), init_children.as_mut_ptr().cast());
                            locks::__mcs_rwlock_writer_unlock_noirq(addr_of_mut!((*proc).children_lock).cast::<locks::McsRwlockLock>(), children.as_mut_ptr().cast());
                        }
                    }
                    _ => {}
                }
                unsafe { locks::__mcs_rwlock_writer_unlock_noirq(addr_of_mut!((*child).update_lock).cast::<locks::McsRwlockLock>(), update.as_mut_ptr().cast()) };
                if policy::terminate_release_child_needed_result(free_child) != 0 {
                    unsafe { process::release_process(child) };
                }
                child_link = next;
            }
            let unlock_hash = unsafe { addr_of!((*resources).process_hash).read() };
            unsafe { locks::__mcs_rwlock_writer_unlock(addr_of_mut!((*unlock_hash).lock[bucket]).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr()) };
            bucket += 1;
        }
    }
    if unsafe { debug_enabled(2) } {
        unsafe { kprintf(b"terminate,pid=%d\n\0".as_ptr().cast(), addr_of!((*proc).pid).read()); }
    }
    unsafe {
        policy::f03_finalize_process_v1(proc);
        crate::cls::preempt_disable();
        locks::__mcs_rwlock_writer_lock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
        addr_of_mut!((*current).status).write(PS_EXITED);
        locks::__mcs_rwlock_writer_unlock(addr_of_mut!((*proc).threads_lock).cast::<locks::McsRwlockLock>(), lock.as_mut_ptr());
        process::release_thread(current);
        process::release_process_vm(vm);
        crate::cls::preempt_enable();
        schedule();
        kprintf(b"%s: ERROR: returned from terminate() -> schedule()\n\0".as_ptr().cast(), FUNCTION);
        panic(b"panic\0".as_ptr().cast());
    }
}

const _: unsafe extern "C" fn(CInt, CInt) = terminate;
const _: () = {
    assert!(size_of::<CInt>() == 4);
    assert!(size_of::<CULong>() == 8);
    assert!(PROCESS_HASH_SIZE == 73);
    // Exact nominal-type boundary; runtime-module private offsets are already
    // asserted in lock_helpers/spinlock_helpers, not accessed or made public.
    assert!(size_of::<crate::abi::McsRwlockLock>() == 64);
    assert!(core::mem::align_of::<crate::abi::McsRwlockLock>() == 64);
    assert!(offset_of!(crate::abi::McsRwlockLock, slock) == 0);
    assert!(size_of::<locks::McsRwlockLock>() == 64);
    assert!(core::mem::align_of::<locks::McsRwlockLock>() == 64);
    assert!(size_of::<crate::abi::IhkSpinlock>() == 4);
    assert!(core::mem::align_of::<crate::abi::IhkSpinlock>() == 4);
    assert!(offset_of!(crate::abi::IhkSpinlock, head_tail) == 0);
    assert!(size_of::<crate::spinlock_helpers::IhkSpinlock>() == 4);
    assert!(core::mem::align_of::<crate::spinlock_helpers::IhkSpinlock>() == 4);
    // Newly consumed list/lock/accounting fields: paired real C assertions.
    assert!(offset_of!(Process, hash_list) == 0);
    assert!(offset_of!(Process, update_lock) == 64);
    assert!(offset_of!(Process, report_threads_list) == 152);
    assert!(offset_of!(Process, threads_lock) == 192);
    assert!(offset_of!(Process, ppid_parent) == 280);
    assert!(offset_of!(Process, children_list) == 288);
    assert!(offset_of!(Process, ptraced_children_list) == 304);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(offset_of!(Process, siblings_list) == 384);
    assert!(offset_of!(Process, ptraced_siblings_list) == 400);
    assert!(offset_of!(Process, saved_cmdline) == 1136);
    assert!(offset_of!(Process, utime) == 1312);
    assert!(offset_of!(Thread, exit_status) == 4188);
    assert!(offset_of!(Thread, termsig) == 4196);
    assert!(offset_of!(Thread, siblings_list) == 4312);
    assert!(offset_of!(Thread, report_siblings_list) == 4368);
    assert!(offset_of!(Thread, system_tsc) == 5040);
    assert!(offset_of!(Thread, user_tsc) == 5048);
    assert!(size_of::<McsRwlockNode>() == 64);
    assert!(core::mem::align_of::<McsRwlockNode>() == 64);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(core::mem::align_of::<McsRwlockNodeIrqsave>() == 64);
};
