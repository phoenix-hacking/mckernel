// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Current ordinary-x86 do_fork, using the existing genuine process providers.
//! The separately held owned-constructor transaction is not selected here.
#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12,
    enable_profile, enable_perf, enable_rusage, not(enable_tofu), not(enable_fugaku_hacks),
    f06_obtain_clone_cpuid_candidate, f03_sync_child_event_candidate)))]
compile_error!("do_fork requires its paired current x86/Linux6.12/PROFILE/whole-F06 cohort");

use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, null, null_mut, read_volatile};
use crate::abi::{AddressSpace, CInt, CLong, CULong, CpuSet, McexecTid,
    Memobj, Process, ProcessVm, SigInfo, SizeT, SyscallRequest, Thread, VmRange};
use crate::debug::{kprintf, Ddebug};
use crate::f03_perf_attr_callbacks::PerfEventAttr;
use crate::lock_helpers::{self as locks, McsRwlockNodeIrqsave};
use crate::process_helpers as process;
use crate::syscall_policy::{self as policy, McsRwlockNode};

const CLONE_VM: CInt = 0x100;
const CLONE_THREAD: CInt = 0x10000;
const SYS_CLONE: CULong = 56;
const SYS_KILL: CULong = 62;
const SYS_GETTID: CInt = 186;
const SYS_CLONE3: CULong = 435;
const SIGKILL: CULong = 9;
const EAGAIN: CInt = 11;
const ENOMEM: CInt = 12;
const EINVAL: CInt = 22;
const IHK_MC_AP_NOWAIT: CULong = 2;
const SOURCE_FILE: *const i8 = concat!(env!("MCKERNEL_DO_SYSCALL_C_FILE"), "\0").as_ptr().cast();
const FUNCTION: *const i8 = b"do_fork\0".as_ptr().cast();
const DEBUG_FLAGS: u32 = match env!("MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("do_fork requires the actual C DDEBUG default"),
};
const fn record(function: *const i8, line: u32) -> Ddebug {
    Ddebug { file: SOURCE_FILE, func: function, fmt: null(),
        line_flags: line | (DEBUG_FLAGS << 24) }
}
// Actual selected #line7721 at physical8201: subsequent C lines = physical-481.
// Keep the already extracted TLS helper's explicit7690 identity unchanged.
#[used]
#[link_section = "__verbose"]
static mut FORK_DEBUG: [Ddebug; 11] = [
    record(FUNCTION, 7777), record(FUNCTION, 7782), record(FUNCTION, 7792),
    record(FUNCTION, 7842), record(FUNCTION, 7952), record(FUNCTION, 7972),
    record(FUNCTION, 8030), record(FUNCTION, 8039), record(FUNCTION, 8053),
    record(FUNCTION, 8166), record(FUNCTION, 7690),
];
// These are the three original ptrace_report_clone_log_bridge records. Its
// selected #line7179 maps physical7581 to7179 (physical-402).
#[used]
#[link_section = "__verbose"]
static mut CLONE_REPORT_DEBUG: [Ddebug; 3] = [
    record(b"ptrace_report_clone_log_bridge\0".as_ptr().cast(), 7279),
    record(b"ptrace_report_clone_log_bridge\0".as_ptr().cast(), 7283),
    record(b"ptrace_report_clone_log_bridge\0".as_ptr().cast(), 7288),
];

unsafe extern "C" {
    static mut allow_oversubscribe: CInt;
    fn obtain_clone_cpuid(mask: *mut CpuSet, use_last: CInt) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;
    fn do_kill(thread: *mut Thread, pid: CInt, tid: CInt, signal: CInt,
        info: *mut SigInfo, ptracecont: CInt) -> CULong;
    fn schedule();
}

unsafe fn debug(index: usize) -> bool {
    read_volatile(addr_of!(FORK_DEBUG[index].line_flags)) >> 24 != 0
}

// Re-evaluate the original NR_TIDS expression at each original expansion site.
// The source-defined positive processor count makes signed multiplication
// defined. No new cap, allocation initialization, or oversubscription policy.
unsafe fn nr_tids() -> CInt {
    if read_volatile(addr_of!(allow_oversubscribe)) != 0 {
        if read_volatile(addr_of!(crate::ap::num_processors)).wrapping_mul(2) > 128 {
            read_volatile(addr_of!(crate::ap::num_processors)).wrapping_mul(2)
        } else { 128 }
    } else { read_volatile(addr_of!(crate::ap::num_processors)) }
}

/// Copy only diagnostic bytes while the existing reader protects the range.
/// File/hugefile/device providers own immutable PATH_MAX path storage until
/// range removal releases the object. Defined C string inputs are terminated
/// within that storage. No descriptor/object/path pointer escapes the lock.
unsafe fn routine_snapshot(old: *mut Thread, routine: CULong,
    bytes: *mut u8) -> bool {
    if routine == 0 { return false; }
    let vm = (*old).vm;
    let lock = addr_of_mut!((*vm).memory_range_lock).cast();
    locks::ihk_rwspinlock_read_lock_noirq(lock);
    let range = process::lookup_process_memory_range(vm, routine, routine.wrapping_add(1));
    let mut found = false;
    if !range.is_null() && !(*range).memobj.is_null() {
        let object = (*range).memobj.cast::<Memobj>();
        let path = (*object).path;
        if !path.is_null() {
            found = true;
            let mut i = 0;
            while i + 1 < crate::abi::PATH_MAX {
                let byte = path.add(i).read() as u8;
                bytes.add(i).write(byte);
                if byte == 0 { break; }
                i += 1;
            }
            bytes.add(crate::abi::PATH_MAX - 1).write(0);
        }
    }
    locks::ihk_rwspinlock_read_unlock_noirq(lock);
    found
}

unsafe extern "C" fn settid_log(ret: CInt) {
    kprintf(b"settid: WARNING: do_syscall returns %d\n\0".as_ptr().cast(), ret);
}
unsafe fn settid(count: CInt, tids: *mut CInt) -> CInt {
    // The genuine existing helper writes every request byte before transport.
    let mut request = MaybeUninit::<SyscallRequest>::uninit();
    policy::syscall_settid_body_result(request.as_mut_ptr(), count, tids, SYS_GETTID,
        crate::x86_memory_helpers::virt_to_phys, ihk_mc_get_processor_id,
        do_syscall, settid_log)
}

unsafe extern "C" fn report_lock(lock: CULong, node: *mut c_void) {
    locks::__mcs_rwlock_writer_lock_noirq(lock as *mut locks::McsRwlockLock, node);
}
unsafe extern "C" fn report_unlock(lock: CULong, node: *mut c_void) {
    locks::__mcs_rwlock_writer_unlock_noirq(lock as *mut locks::McsRwlockLock, node);
}
unsafe extern "C" fn report_kill(current: *mut c_void, pid: CInt, tid: CInt,
    signal: CInt, info: *const SigInfo, ptracecont: CInt) -> CLong {
    do_kill(current.cast(), pid, tid, signal, info.cast_mut(), ptracecont) as CLong
}
unsafe extern "C" fn report_wake(queue: *mut c_void) {
    crate::waitq::waitq_wakeup(queue.cast());
}
unsafe extern "C" fn report_log(event: CInt, _value: CInt, _result: CInt) {
    let (index, text): (usize, &[u8]) = match event {
        5 => (0, b"ptrace_report_clone,enter\n\0"),
        6 => (1, b"ptrace_report_clone,kill SIGCHLD\n\0"),
        7 => (2, b"ptrace_report_clone,do_kill failed\n\0"),
        _ => return,
    };
    if read_volatile(addr_of!(CLONE_REPORT_DEBUG[index].line_flags)) >> 24 != 0 {
        kprintf(text.as_ptr().cast());
    }
}
unsafe fn report_clone(old: *mut Thread, new: *mut Thread, event: CInt) {
    let offsets = policy::PtraceReportCloneOffsets {
        thread_proc_offset: offset_of!(Thread, proc),
        thread_tid_offset: offset_of!(Thread, tid),
        thread_status_offset: offset_of!(Thread, status),
        thread_exit_status_offset: offset_of!(Thread, exit_status),
        thread_ptrace_offset: offset_of!(Thread, ptrace),
        thread_ptrace_eventmsg_offset: offset_of!(Thread, ptrace_eventmsg),
        proc_pid_offset: offset_of!(Process, pid),
        proc_parent_offset: offset_of!(Process, parent),
        proc_status_offset: offset_of!(Process, status),
        proc_update_lock_offset: offset_of!(Process, update_lock),
        proc_waitpid_q_offset: offset_of!(Process, waitpid_q),
    };
    let mut lock = MaybeUninit::<McsRwlockNode>::uninit();
    let mut update = MaybeUninit::<McsRwlockNode>::uninit();
    let current = (*crate::cls::get_this_cpu_local_var()).current;
    // The same genuine complete Rust helper and endpoints as the C wrapper.
    // Preserve ignored attach/delivery/result dispositions and real wakeup.
    let _ = policy::ptrace_report_clone_body_result(old.cast(), new.cast(), event,
        current.cast(), &offsets, lock.as_mut_ptr().cast(), update.as_mut_ptr().cast(),
        Some(report_lock), Some(report_unlock),
        Some(policy::f03_ptrace_attach_thread_addr_v1), Some(report_kill),
        Some(report_wake), Some(report_log));
}

/// Complete current legacy-host clone/fork orchestration, exact seven-arg ABI.
///
/// # Safety
/// Running parent/process/context and original constructor/provider contracts
/// remain valid. The child is held before publication; real providers preserve
/// their existing lock/IRQ/CPU/accounting/refcount/ACK dispositions. No extra
/// reference, constructor authority, cancellation, or return validation is added.
#[no_mangle]
pub unsafe extern "C" fn do_fork(clone_flags: CInt, newsp: CULong,
    parent_tidptr: CULong, child_tidptr: CULong, tlsblock_base: CULong,
    curpc: CULong, cursp: CULong) -> CULong {
    let old = (*crate::cls::get_this_cpu_local_var()).current;
    let oldproc = (*old).proc;
    // Preserve the independently qualified current C request1={0}, all72bytes.
    // This same storage survives selector0, selector1, and any original kill.
    let mut request1 = MaybeUninit::<SyscallRequest>::zeroed().assume_init();
    let mut ptrace_event = 0;
    let termsig = clone_flags & 0xff;
    let mut error: CInt;
    if debug(0) { kprintf(b"%s,flags=%08x,newsp=%lx,ptidptr=%lx,ctidptr=%lx,tls=%lx,curpc=%lx,cursp=%lx\0".as_ptr().cast(),
        FUNCTION, clone_flags as u32, newsp, parent_tidptr, child_tidptr, tlsblock_base, curpc, cursp); }
    if debug(1) { kprintf(b"do_fork(): stack_pointr passed in: 0x%lX, stack pointer of caller: 0x%lx\n\0".as_ptr().cast(), newsp, cursp); }
    if crate::x86_cpu_helpers::ihk_mc_syscall_number((*old).uctx) != SYS_CLONE3
        && policy::clone_pthread_marker_result(clone_flags, newsp, parent_tidptr) != 0 {
        (*old).clone_pthread_start_routine = parent_tidptr;
        if debug(2) { kprintf(b"%s: clone_pthread_start_routine: 0x%lx\n\0".as_ptr().cast(), FUNCTION, (*old).clone_pthread_start_routine); }
        return 0;
    }
    let routine = (*old).clone_pthread_start_routine;
    (*old).clone_pthread_start_routine = 0;
    let parent_cpuid = (*old).cpu_id;
    error = policy::clone_flags_result(clone_flags, (*oldproc).coredump_barrier_count);
    if error != 0 {
        if (clone_flags & CLONE_VM != 0 && clone_flags & CLONE_THREAD == 0)
            || (clone_flags & CLONE_VM == 0 && clone_flags & CLONE_THREAD != 0) {
            kprintf(b"clone(): ERROR: CLONE_VM and CLONE_THREAD should be set together\n\0".as_ptr().cast());
        }
        return error as CULong;
    }
    if (*oldproc).uti_thread_rank != 0 {
        (*old).mod_clone = if (*oldproc).clone_count.wrapping_add(1) == (*oldproc).uti_thread_rank { 1 } else { 0 };
        kprintf(b"%s: mod_clone is set to %d\n\0".as_ptr().cast(), FUNCTION, (*old).mod_clone);
    }
    let mut path = MaybeUninit::<[u8; crate::abi::PATH_MAX]>::uninit();
    let pathp = path.as_mut_ptr().cast::<u8>();
    let has_path = routine_snapshot(old, routine, pathp);
    let helper_thread = has_path
        && crate::string::strstr(pathp.cast(), b"omp.so\0".as_ptr().cast()).is_null()
        && crate::string::strstr(pathp.cast(), b"libfj90\0".as_ptr().cast()).is_null();
    if has_path && debug(3) { kprintf(b"clone(): %s thread from %s\n\0".as_ptr().cast(),
        if helper_thread { b"helper\0".as_ptr() } else { b"compute\0".as_ptr() }, pathp); }

    let mut clone_cpu_set = MaybeUninit::<CpuSet>::uninit();
    let mut inherit_affinity = false;
    let cpuid = if helper_thread { ihk_mc_get_processor_id() } else {
        let selected = if clone_flags & CLONE_THREAD != 0 && (*oldproc).uti_thread_rank == 0
            && (*old).mod_clone == 0 && (*oldproc).uti_use_last_cpu == 0 {
            if crate::sched_helpers::sched_clone_affinity_snapshot_result(
                addr_of!((*old).cpu_set) as usize, addr_of!((*oldproc).cpu_set) as usize,
                clone_cpu_set.as_mut_ptr() as usize, size_of::<CpuSet>(), crate::ap::num_processors) != 0 {
                return (-EAGAIN) as CULong;
            }
            inherit_affinity = true;
            obtain_clone_cpuid(clone_cpu_set.as_mut_ptr(), 0)
        } else {
            obtain_clone_cpuid(addr_of_mut!((*oldproc).cpu_set),
                policy::clone_use_last_cpu_result((*old).mod_clone, (*oldproc).uti_use_last_cpu))
        };
        if selected == -1 {
            kprintf(b"do_fork,core not available\n\0".as_ptr().cast());
            return (-EAGAIN) as CULong;
        }
        selected
    };
    let new = process::clone_thread(old, curpc, if newsp != 0 { newsp } else { cursp }, clone_flags);
    if new.is_null() {
        if !helper_thread { crate::sched_helpers::release_cpuid(cpuid); }
        return (-ENOMEM) as CULong;
    }
    if routine != 0 && has_path {
        crate::numparse::sprintf(addr_of_mut!((*new).pthread_routine).cast(),
            b"0x%lx @ %s\0".as_ptr().cast(), routine, pathp);
    } else {
        crate::numparse::sprintf(addr_of_mut!((*new).pthread_routine).cast(),
            b"%s\0".as_ptr().cast(), b"[unknown]\0".as_ptr());
    }
    let newproc = (*new).proc;
    let mut tid_table_created = 0;
    let mut release_ids = false;
    let mut free_mod_argument = false;
    'prepared: {
        if inherit_affinity && crate::sched_helpers::sched_clone_affinity_inherit_result(
            addr_of_mut!((*new).cpu_set) as usize, clone_cpu_set.as_ptr() as usize,
            size_of::<CpuSet>()) != 0 {
            error = -EINVAL;
            break 'prepared;
        }
        let space = (*(*new).vm).address_space;
        process::cpu_set(cpuid, addr_of_mut!((*space).cpu_set), addr_of_mut!((*space).cpu_set_lock));
        if clone_flags & CLONE_VM != 0 {
            let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
            let threads_lock = addr_of_mut!((*newproc).threads_lock).cast();
            locks::__mcs_rwlock_writer_lock(threads_lock, lock.as_mut_ptr());
            if (*newproc).nr_tids == 0 {
                let tids = crate::mem_helpers::kmalloc_tracked(
                    size_of::<CInt>().wrapping_mul(nr_tids() as SizeT) as CInt,
                    IHK_MC_AP_NOWAIT, SOURCE_FILE.cast_mut(), 7927).cast::<CInt>();
                if tids.is_null() {
                    locks::__mcs_rwlock_writer_unlock(threads_lock, lock.as_mut_ptr());
                    error = -ENOMEM;
                    break 'prepared;
                }
                (*newproc).tids = crate::mem_helpers::kmalloc_tracked(
                    size_of::<McexecTid>().wrapping_mul(nr_tids() as SizeT) as CInt,
                    IHK_MC_AP_NOWAIT, SOURCE_FILE.cast_mut(), 7935);
                if (*newproc).tids.is_null() {
                    locks::__mcs_rwlock_writer_unlock(threads_lock, lock.as_mut_ptr());
                    crate::mem_helpers::kfree_tracked(tids.cast(), SOURCE_FILE.cast_mut(), 7938);
                    error = -ENOMEM;
                    break 'prepared;
                }
                tid_table_created = 1;
                error = settid(nr_tids(), tids);
                if error < 0 {
                    locks::__mcs_rwlock_writer_unlock(threads_lock, lock.as_mut_ptr());
                    crate::mem_helpers::kfree_tracked(tids.cast(), SOURCE_FILE.cast_mut(), 7947);
                    release_ids = true;
                    break 'prepared;
                }
                let mut i: CInt = 0;
                while i < nr_tids() && *tids.add(i as usize) != 0 {
                    if debug(4) { kprintf(b"%s: tids[%d]: %d\n\0".as_ptr().cast(), FUNCTION, i, *tids.add(i as usize)); }
                    let slot = (*newproc).tids.cast::<McexecTid>().add(i as usize);
                    (*slot).tid = *tids.add(i as usize);
                    (*slot).thread = null_mut();
                    (*newproc).nr_tids += 1;
                    i += 1;
                }
                crate::mem_helpers::kfree_tracked(tids.cast(), SOURCE_FILE.cast_mut(), 7959);
            }
            (*new).tid = 0;
            'retry_tid: loop {
                let mut i: CInt = 0;
                while i < (*newproc).nr_tids {
                    let slot = (*newproc).tids.cast::<McexecTid>().add(i as usize);
                    if (*slot).thread.is_null() {
                        if !crate::atomic_helpers::atomic_cmpxchg_ptr(
                            addr_of_mut!((*slot).thread).cast(), null_mut(), new.cast()).is_null() {
                            continue 'retry_tid;
                        }
                        (*new).tid = (*slot).tid;
                        if debug(5) { kprintf(b"%s: tid %d assigned to %p\n\0".as_ptr().cast(), FUNCTION, (*new).tid, new); }
                        break;
                    }
                    i += 1;
                }
                break;
            }
            locks::__mcs_rwlock_writer_unlock(threads_lock, lock.as_mut_ptr());
            if (*new).tid == 0 {
                kprintf(b"%s: no more TIDs available\n\0".as_ptr().cast(), FUNCTION);
                let mut i: CInt = 0;
                while i < (*newproc).nr_tids {
                    let slot = (*newproc).tids.cast::<McexecTid>().add(i as usize);
                    kprintf(b"%s: i=%d,tid=%d,thread=%p\n\0".as_ptr().cast(), FUNCTION, i, (*slot).tid, (*slot).thread);
                    i += 1;
                }
                error = -ENOMEM;
                release_ids = true;
                break 'prepared;
            }
        } else {
            request1.number = SYS_CLONE;
            request1.args[0] = 0;
            request1.args[1] = (*(*new).vm).region.user_start;
            request1.args[2] = (*(*new).vm).region.user_end.wrapping_sub((*(*new).vm).region.user_start);
            request1.args[3] = crate::x86_memory_helpers::virt_to_phys((*(*(*new).vm).address_space).page_table);
            request1.args[0] = policy::clone_host_parent_flags_result(clone_flags, (*(*oldproc).ppid_parent).pid) as CULong;
            (*newproc).pid = do_syscall(&mut request1, ihk_mc_get_processor_id()) as CInt;
            if (*newproc).pid < 0 {
                // The real host fork failed: release only the pending parent
                // transaction gate, never close an inherited parent fd.
                #[cfg(f03_perf_owner_protocol)]
                policy::f03_perf_owner::finish_child_host_route(newproc, false);
                kprintf(b"ERROR: forking host process\n\0".as_ptr().cast());
                error = (*newproc).pid;
                break 'prepared;
            }
            (*new).tid = (*newproc).pid;
            // The actual C pids[] is a flexible int array immediately after
            // nslots, beyond the fixed Rust AddressSpace. Use its real trailing
            // allocation, not an invented field or an opt/free_cb overlay.
            // Paired C assertion/table bind this flexible-member byte offset.
            space.cast::<u8>().add(offset_of!(AddressSpace, nslots) + size_of::<CInt>())
                .cast::<CInt>().write((*(*new).proc).pid);
            if debug(6) { kprintf(b"fork(): new pid: %d\n\0".as_ptr().cast(), (*(*new).proc).pid); }
            // The selected Linux consumer actually forked an independent
            // child fd table. Activate its prebound route/monitor association
            // while the pending parent transaction gate still protects it.
            #[cfg(f03_perf_owner_protocol)]
            policy::f03_perf_owner::inherit_monitor_after_host_clone(oldproc, newproc);
            #[cfg(not(f03_perf_owner_protocol))]
            {
                let event = (*oldproc).monitoring_event;
                if !event.is_null() && (*event.cast::<PerfEventAttr>()).flags & 2 != 0 {
                    (*newproc).monitoring_event = (*oldproc).monitoring_event;
                }
            }
        }
        if policy::clone_parent_tid_store_needed_result(clone_flags) != 0 {
            if debug(7) { kprintf(b"clone_flags & CLONE_PARENT_SETTID: 0x%lX\n\0".as_ptr().cast(), parent_tidptr); }
            let _ = crate::x86_memory_helpers::setint_user(parent_tidptr as *mut CInt, (*new).tid);
            // Selected native-TID contract deliberately ignores failed put_user.
        }
        if policy::clone_child_cleartid_needed_result(clone_flags) != 0 {
            if debug(8) { kprintf(b"clone_flags & CLONE_CHILD_CLEARTID: 0x%lX\n\0".as_ptr().cast(), child_tidptr); }
            (*new).clear_child_tid = child_tidptr as *mut CInt;
        }
        if policy::clone_child_tid_store_needed_result(clone_flags) != 0 {
            let _ = crate::x86_memory_helpers::write_process_vm((*new).vm, child_tidptr as *mut c_void,
                addr_of!((*new).tid).cast(), size_of::<CInt>());
        }
        policy::f03_clone_initialize_execution_state_v1(old, new, clone_flags, tlsblock_base,
            parent_cpuid, addr_of_mut!(FORK_DEBUG[10]));
        if policy::f03_clone_prepare_remote_argument_v1(old, new, &mut error, SOURCE_FILE, 7710) != 0 {
            release_ids = true;
            break 'prepared;
        }
        policy::f03_clone_publish_thread_process_v1(new, oldproc, newproc, clone_flags);
        if (*old).ptrace != 0 {
            ptrace_event = policy::ptrace_clone_event_result((*old).ptrace, clone_flags);
            if ptrace_event != 0 { report_clone(old, new, ptrace_event); }
        }
        if debug(9) { kprintf(b"clone: kicking scheduler!,cpuid=%d pid=%d tid %d -> tid=%d\n\0".as_ptr().cast(),
            cpuid, (*newproc).pid, (*old).tid, (*new).tid); }
        if clone_flags & CLONE_VM == 0 {
            request1.number = SYS_CLONE;
            request1.args[0] = 1;
            request1.args[1] = (*new).tid as CULong;
            error = do_syscall(&mut request1, ihk_mc_get_processor_id()) as CInt;
            if error != 0 {
                free_mod_argument = true;
                release_ids = true;
                break 'prepared;
            }
        } else if policy::clone_report_thread_result(clone_flags, termsig) != 0 {
            let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
            let threads_lock = addr_of_mut!((*oldproc).threads_lock).cast();
            locks::__mcs_rwlock_writer_lock(threads_lock, lock.as_mut_ptr());
            let _ = process::process_thread_report_attach_result(new.cast(),
                offset_of!(Thread, termsig) as CULong, 1, termsig,
                offset_of!(Thread, report_proc) as CULong, oldproc.cast(),
                addr_of_mut!((*new).report_siblings_list), addr_of_mut!((*oldproc).report_threads_list));
            locks::__mcs_rwlock_writer_unlock(threads_lock, lock.as_mut_ptr());
            let _ = process::hold_thread(new);
        }
        // The prepared child's committed TID is the return value. After runq
        // publication/schedule the child can exit; perform no later child load.
        let child_tid = (*new).tid;
        crate::sched_helpers::runq_add_thread(new, cpuid);
        if ptrace_event != 0 { schedule(); }
        return child_tid as CULong;
    }
    // Every ordinary pre-publication error releases a still-pending parent
    // gate before the original cleanup. This is idempotent after either host
    // outcome and never changes a successfully activated child's fd ownership.
    #[cfg(f03_perf_owner_protocol)]
    if clone_flags & CLONE_VM == 0 {
        policy::f03_perf_owner::finish_child_host_route(newproc, false);
    }
    if free_mod_argument {
        policy::f03_clone_release_mod_argument_v1(new, SOURCE_FILE, 7792);
    }
    if release_ids {
        if clone_flags & CLONE_VM != 0 {
            policy::f03_clone_release_empty_tid_table_v1(newproc, tid_table_created, SOURCE_FILE, 7800);
        } else {
            request1.number = SYS_KILL;
            request1.args[0] = (*newproc).pid as CULong;
            request1.args[1] = SIGKILL;
            let _ = do_syscall(&mut request1, ihk_mc_get_processor_id());
        }
    }
    // Original destroy_thread/release_cpuid labels, same order and dispositions.
    if clone_flags & CLONE_VM == 0 {
        crate::atomic_helpers::ihk_atomic_set(addr_of_mut!((*(*new).proc).refcount).cast(), 1);
        crate::mem_helpers::kfree_tracked((*newproc).saved_cmdline.cast(), SOURCE_FILE.cast_mut(), 8241);
        (*newproc).saved_cmdline = null_mut();
    }
    crate::atomic_helpers::ihk_atomic_set(addr_of_mut!((*new).refcount).cast(), 1);
    process::release_thread(new);
    crate::sched_helpers::release_cpuid(cpuid);
    error as CULong
}

// Representation requirements are actual selected C definitions, not new ABI.
const _: () = {
    assert!(size_of::<CInt>() == 4 && size_of::<CULong>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(size_of::<CpuSet>() == 128 && align_of::<CpuSet>() == 8);
    assert!(size_of::<McexecTid>() == 16 && align_of::<McexecTid>() == 8);
    assert!(offset_of!(McexecTid, tid) == 0 && offset_of!(McexecTid, thread) == 8);
    assert!(size_of::<crate::abi::McsRwlockLock>() == 64 && align_of::<crate::abi::McsRwlockLock>() == 64);
    assert!(size_of::<locks::McsRwlockLock>() == 64 && align_of::<locks::McsRwlockLock>() == 64);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64 && align_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(size_of::<McsRwlockNode>() == 64 && align_of::<McsRwlockNode>() == 64);
    assert!(size_of::<PerfEventAttr>() == 104 && offset_of!(PerfEventAttr, flags) == 40);
};

// Actual C/Rust field words for the real next image readback; no guessed offsets.
#[used]
#[no_mangle]
pub static f03_do_fork_rust_abi_words: [CULong; 104] = [
    (size_of::<CInt>()) as CULong, // sizeof int
    (align_of::<CInt>()) as CULong, // alignof int
    (size_of::<CULong>()) as CULong, // sizeof unsigned long
    (align_of::<CULong>()) as CULong, // alignof unsigned long
    (size_of::<CpuSet>()) as CULong, // sizeof cpu_set_t
    (align_of::<CpuSet>()) as CULong, // alignof cpu_set_t
    (size_of::<SyscallRequest>()) as CULong, // sizeof struct syscall_request
    (align_of::<SyscallRequest>()) as CULong, // alignof struct syscall_request
    (size_of::<McexecTid>()) as CULong, // sizeof struct mcexec_tid
    (align_of::<McexecTid>()) as CULong, // alignof struct mcexec_tid
    (size_of::<Thread>()) as CULong, // sizeof struct thread
    (align_of::<Thread>()) as CULong, // alignof struct thread
    (size_of::<Process>()) as CULong, // sizeof struct process
    (align_of::<Process>()) as CULong, // alignof struct process
    (size_of::<ProcessVm>()) as CULong, // sizeof struct process_vm
    (align_of::<ProcessVm>()) as CULong, // alignof struct process_vm
    (size_of::<AddressSpace>()) as CULong, // sizeof struct address_space
    (align_of::<AddressSpace>()) as CULong, // alignof struct address_space
    (size_of::<VmRange>()) as CULong, // sizeof struct vm_range
    (align_of::<VmRange>()) as CULong, // alignof struct vm_range
    (size_of::<Memobj>()) as CULong, // sizeof struct memobj
    (align_of::<Memobj>()) as CULong, // alignof struct memobj
    (size_of::<crate::abi::McsRwlockLock>()) as CULong, // sizeof struct mcs_rwlock_lock
    (align_of::<crate::abi::McsRwlockLock>()) as CULong, // alignof struct mcs_rwlock_lock
    (size_of::<McsRwlockNodeIrqsave>()) as CULong, // sizeof struct mcs_rwlock_node_irqsave
    (align_of::<McsRwlockNodeIrqsave>()) as CULong, // alignof struct mcs_rwlock_node_irqsave
    (size_of::<McsRwlockNode>()) as CULong, // sizeof struct mcs_rwlock_node
    (align_of::<McsRwlockNode>()) as CULong, // alignof struct mcs_rwlock_node
    (size_of::<PerfEventAttr>()) as CULong, // sizeof struct perf_event_attr
    (align_of::<PerfEventAttr>()) as CULong, // alignof struct perf_event_attr
    (offset_of!(SyscallRequest,rtid)) as CULong, // struct syscall_request::rtid
    (offset_of!(SyscallRequest,ttid)) as CULong, // struct syscall_request::ttid
    (offset_of!(SyscallRequest,valid)) as CULong, // struct syscall_request::valid
    (offset_of!(SyscallRequest,number)) as CULong, // struct syscall_request::number
    (offset_of!(SyscallRequest,args)) as CULong, // struct syscall_request::args
    (offset_of!(McexecTid,tid)) as CULong, // struct mcexec_tid::tid
    (offset_of!(McexecTid,thread)) as CULong, // struct mcexec_tid::thread
    (offset_of!(Thread,cpu_id)) as CULong, // struct thread::cpu_id
    (offset_of!(Thread,tid)) as CULong, // struct thread::tid
    (offset_of!(Thread,pthread_routine)) as CULong, // struct thread::pthread_routine
    (offset_of!(Thread,status)) as CULong, // struct thread::status
    (offset_of!(Thread,exit_status)) as CULong, // struct thread::exit_status
    (offset_of!(Thread,termsig)) as CULong, // struct thread::termsig
    (offset_of!(Thread,vm)) as CULong, // struct thread::vm
    (offset_of!(Thread,uctx)) as CULong, // struct thread::uctx
    (offset_of!(Thread,proc)) as CULong, // struct thread::proc
    (offset_of!(Thread,report_proc)) as CULong, // struct thread::report_proc
    (offset_of!(Thread,report_siblings_list)) as CULong, // struct thread::report_siblings_list
    (offset_of!(Thread,ptrace)) as CULong, // struct thread::ptrace
    (offset_of!(Thread,ptrace_eventmsg)) as CULong, // struct thread::ptrace_eventmsg
    (offset_of!(Thread,refcount)) as CULong, // struct thread::refcount
    (offset_of!(Thread,clear_child_tid)) as CULong, // struct thread::clear_child_tid
    (offset_of!(Thread,cpu_set)) as CULong, // struct thread::cpu_set
    (offset_of!(Thread,clone_pthread_start_routine)) as CULong, // struct thread::clone_pthread_start_routine
    (offset_of!(Thread,mod_clone)) as CULong, // struct thread::mod_clone
    (offset_of!(Process,threads_lock)) as CULong, // struct process::threads_lock
    (offset_of!(Process,tids)) as CULong, // struct process::tids
    (offset_of!(Process,nr_tids)) as CULong, // struct process::nr_tids
    (offset_of!(Process,parent)) as CULong, // struct process::parent
    (offset_of!(Process,ppid_parent)) as CULong, // struct process::ppid_parent
    (offset_of!(Process,refcount)) as CULong, // struct process::refcount
    (offset_of!(Process,status)) as CULong, // struct process::status
    (offset_of!(Process,waitpid_q)) as CULong, // struct process::waitpid_q
    (offset_of!(Process,pid)) as CULong, // struct process::pid
    (offset_of!(Process,saved_cmdline)) as CULong, // struct process::saved_cmdline
    (offset_of!(Process,cpu_set)) as CULong, // struct process::cpu_set
    (offset_of!(Process,report_threads_list)) as CULong, // struct process::report_threads_list
    (offset_of!(Process,uti_thread_rank)) as CULong, // struct process::uti_thread_rank
    (offset_of!(Process,uti_use_last_cpu)) as CULong, // struct process::uti_use_last_cpu
    (offset_of!(Process,clone_count)) as CULong, // struct process::clone_count
    (offset_of!(Process,monitoring_event)) as CULong, // struct process::monitoring_event
    (offset_of!(Process,coredump_barrier_count)) as CULong, // struct process::coredump_barrier_count
    (offset_of!(Process,update_lock)) as CULong, // struct process::update_lock
    (offset_of!(ProcessVm,address_space)) as CULong, // struct process_vm::address_space
    (offset_of!(ProcessVm,region)) as CULong, // struct process_vm::region
    (offset_of!(ProcessVm,memory_range_lock)) as CULong, // struct process_vm::memory_range_lock
    (offset_of!(AddressSpace,page_table)) as CULong, // struct address_space::page_table
    (offset_of!(AddressSpace,cpu_set)) as CULong, // struct address_space::cpu_set
    (offset_of!(AddressSpace,cpu_set_lock)) as CULong, // struct address_space::cpu_set_lock
    (offset_of!(AddressSpace,nslots)) as CULong, // struct address_space::nslots
    (offset_of!(VmRange,memobj)) as CULong, // struct vm_range::memobj
    (offset_of!(Memobj,path)) as CULong, // struct memobj::path
    (offset_of!(AddressSpace,nslots)+size_of::<CInt>()) as CULong, // struct address_space::pids flexible
    (offset_of!(ProcessVm,region)+offset_of!(crate::abi::VmRegions,user_start)) as CULong, // struct process_vm::region.user_start
    (offset_of!(ProcessVm,region)+offset_of!(crate::abi::VmRegions,user_end)) as CULong, // struct process_vm::region.user_end
    (0) as CULong, // mc_perf_event::attr
    (offset_of!(PerfEventAttr,flags)+size_of::<CULong>()) as CULong, // perf flags unit end
    (size_of::<SyscallRequest>()) as CULong, // DMA request sizeof
    (align_of::<SyscallRequest>()) as CULong, // DMA request align
    (SYS_CLONE) as CULong, // clone number
    (SYS_CLONE3) as CULong, // clone3 number
    (SYS_KILL) as CULong, // kill number
    (SYS_GETTID) as CULong, // gettid number
    (CLONE_VM) as CULong, // CLONE_VM
    (CLONE_THREAD) as CULong, // CLONE_THREAD
    (SIGKILL) as CULong, // SIGKILL
    (EAGAIN) as CULong, // EAGAIN
    (ENOMEM) as CULong, // ENOMEM
    (EINVAL) as CULong, // EINVAL
    (IHK_MC_AP_NOWAIT) as CULong, // NOWAIT
    (128) as CULong, // oversubscribed TIDs
    (crate::abi::PATH_MAX) as CULong, // PATH_MAX
    (crate::abi::PTHREAD_ROUTINE_LEN) as CULong, // pthread routine capacity
    (DEBUG_FLAGS) as CULong, // DDEBUG default
];
const _: unsafe extern "C" fn(CInt,CULong,CULong,CULong,CULong,CULong,CULong)->CULong = do_fork;
