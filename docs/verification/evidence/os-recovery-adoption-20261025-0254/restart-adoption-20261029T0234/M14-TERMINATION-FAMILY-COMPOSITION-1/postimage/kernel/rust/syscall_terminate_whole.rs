// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Supported non-ToFu/non-DCFA transaction; final stack handoff remains unselected.
    use core::ffi::c_void;
    use core::mem::{offset_of, size_of, MaybeUninit};
    use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile, write_volatile};

    use crate::abi::{
        AbiListHead, CInt, CULong, Process, ResourceSet, Thread, TimeSpec, PROCESS_HASH_SIZE,
    };
    use crate::debug::Ddebug;
    use crate::lock_helpers::{McsRwlockLock, McsRwlockNodeIrqsave};
    use crate::process_helpers::{
        free_all_process_memory_range, process_child_reparent_result,
        process_list_add_tail_result, process_list_del_init_result, process_list_detach_result,
        process_thread_report_detach_result, process_thread_termsig_clear_result,
        release_process, release_process_vm, release_thread,
    };

    use super::{
        f03_finalize_process_v1, f03_ptrace_detach_thread_v1, f03_thread_exit_signal_v1,
        f06_ptrace_report_signal_kill, schedule, terminate_child_action_result,
        terminate_child_cleanup_needed_result, terminate_process_exited_result,
        terminate_release_child_needed_result, terminate_report_thread_ptrace_result,
        terminate_report_thread_release_needed_result, terminate_status_result,
        terminate_thread_active_result, terminate_thread_is_other_result, tsc_to_ts,
        McsRwlockNode, PS_EXITED, SIGKILL, TERMINATE_CHILD_ACTION_FREE_ZOMBIE,
        TERMINATE_CHILD_ACTION_REPARENT_CHILD, TERMINATE_CHILD_ACTION_REPARENT_PTRACED,
    };

    // The Rust-owned metadata below is limited to the reviewed /src source
    // profile. The compiler's selected __FILE__/__LINE__ must be verified before
    // the candidate can be enabled; these source facts are not runtime proof.
    const SOURCE_FILE: &[u8] = b"/src/kernel/syscall.c\0";
    const FUNCTION_NAME: &[u8] = b"terminate\0";
    const NOWAIT: CULong = 0x000002;
    #[cfg(f03_terminate_origin_dispatch)]
    const ORIGIN_LINES: [CInt; 6] = [5271, 5292, 5511, 5346, 5363, 5403];
    #[cfg(not(f03_terminate_origin_dispatch))]
    const ORIGIN_LINES: [CInt; 6] = [5278, 5299, 5518, 5353, 5370, 5410];

    // Match the three original ddebug records and writable flag semantics.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    static mut f03_terminate_debug_v1: [Ddebug; 3] = [
        Ddebug { file: SOURCE_FILE.as_ptr().cast(), func: FUNCTION_NAME.as_ptr().cast(),
            fmt: core::ptr::null(), line_flags: ORIGIN_LINES[0] as u32 },
        Ddebug { file: SOURCE_FILE.as_ptr().cast(), func: FUNCTION_NAME.as_ptr().cast(),
            fmt: core::ptr::null(), line_flags: ORIGIN_LINES[1] as u32 },
        Ddebug { file: SOURCE_FILE.as_ptr().cast(), func: FUNCTION_NAME.as_ptr().cast(),
            fmt: core::ptr::null(), line_flags: ORIGIN_LINES[2] as u32 },
    ];

    unsafe extern "C" {
        #[link_name = "sync_child_event"]
        fn original_sync_child_event(event: *mut c_void);
        #[link_name = "terminate_mcexec"]
        fn original_terminate_mcexec(rc: CInt, sig: CInt);
        fn kprintf(format: *const i8, ...) -> CInt;
    }

    macro_rules! debug {
        ($index:expr, $format:expr $(, $value:expr)* $(,)?) => {{
            // SAFETY: Genuine original lexical record and scalar variadic ABI.
            unsafe {
                if read_volatile(addr_of!(f03_terminate_debug_v1[$index].line_flags)) >> 24 != 0 {
                    kprintf($format.as_ptr().cast() $(, $value)*);
                }
            }
        }};
    }

    unsafe fn thread_from_sibling(node: *mut AbiListHead) -> *mut Thread {
        // SAFETY: Call only after excluding the live list head while holding its
        // original threads lock. The node belongs to a retained real Thread.
        unsafe { node.cast::<u8>().sub(offset_of!(Thread, siblings_list)).cast() }
    }

    unsafe fn process_from_hash(node: *mut AbiListHead) -> *mut Process {
        // SAFETY: The process hash writer lock retains this non-head element.
        unsafe { node.cast::<u8>().sub(offset_of!(Process, hash_list)).cast() }
    }

    unsafe fn account_time(thread: *mut Thread, process: *mut Process) {
        let mut delta = MaybeUninit::<TimeSpec>::uninit();
        // SAFETY: Actual update/threads locks retain these fields. tsc_to_ts
        // initializes both timespec members before the genuine ts_add reads it.
        unsafe {
            tsc_to_ts((*thread).user_tsc, delta.as_mut_ptr());
            crate::timer::ts_add(addr_of_mut!((*process).utime), delta.as_ptr());
            tsc_to_ts((*thread).system_tsc, delta.as_mut_ptr());
            crate::timer::ts_add(addr_of_mut!((*process).stime), delta.as_ptr());
            write_volatile(addr_of_mut!((*thread).user_tsc), 0);
            write_volatile(addr_of_mut!((*thread).system_tsc), 0);
        }
    }

    unsafe fn reparent_children(
        resources: *mut ResourceSet, process: *mut Process, pid1: *mut Process,
        irq_node: *mut McsRwlockNodeIrqsave, update_node: *mut McsRwlockNode,
        parent_node: *mut McsRwlockNode, pid1_node: *mut McsRwlockNode,
    ) {
        // SAFETY: Resource/hash/PID1 lifetimes are the original termination
        // graph. Every raw next pointer is captured before unlink/final release,
        // and no released child is inspected. Distinct noirq nodes are retained.
        unsafe {
            let hash = (*resources).process_hash;
            for index in 0..PROCESS_HASH_SIZE {
                let hash_lock = addr_of_mut!((*hash).lock[index]).cast::<McsRwlockLock>();
                crate::lock_helpers::__mcs_rwlock_writer_lock(hash_lock, irq_node);
                let head = addr_of_mut!((*hash).list[index]);
                let mut cursor = (*head).next;
                while cursor != head {
                    let next = (*cursor).next;
                    let child = process_from_hash(cursor);
                    let child_update = addr_of_mut!((*child).update_lock).cast();
                    crate::lock_helpers::__mcs_rwlock_writer_lock_noirq(
                        child_update, update_node.cast(),
                    );
                    let action = terminate_child_action_result(
                        ((*child).ppid_parent == process) as CInt,
                        ((*child).parent == process) as CInt, (*child).status,
                    );
                    let mut free_child = 0;
                    match action {
                        TERMINATE_CHILD_ACTION_FREE_ZOMBIE => {
                            process_list_del_init_result(addr_of_mut!((*child).hash_list));
                            process_list_del_init_result(addr_of_mut!((*child).siblings_list));
                            free_child = 1;
                        }
                        TERMINATE_CHILD_ACTION_REPARENT_CHILD
                        | TERMINATE_CHILD_ACTION_REPARENT_PTRACED => {
                            let old_children = addr_of_mut!((*process).children_lock).cast();
                            let new_children = addr_of_mut!((*pid1).children_lock).cast();
                            crate::lock_helpers::__mcs_rwlock_writer_lock_noirq(
                                old_children, parent_node.cast(),
                            );
                            crate::lock_helpers::__mcs_rwlock_writer_lock_noirq(
                                new_children, pid1_node.cast(),
                            );
                            let ordinary = action == TERMINATE_CHILD_ACTION_REPARENT_CHILD;
                            let (entry, target) = if ordinary {
                                (addr_of_mut!((*child).siblings_list),
                                    addr_of_mut!((*pid1).children_list))
                            } else {
                                (addr_of_mut!((*child).ptraced_siblings_list),
                                    addr_of_mut!((*pid1).ptraced_children_list))
                            };
                            process_child_reparent_result(
                                child.cast(), offset_of!(Process, ppid_parent) as CULong,
                                offset_of!(Process, parent) as CULong, pid1.cast(), entry,
                                target, ordinary as CInt,
                            );
                            crate::lock_helpers::__mcs_rwlock_writer_unlock_noirq(
                                new_children, pid1_node.cast(),
                            );
                            crate::lock_helpers::__mcs_rwlock_writer_unlock_noirq(
                                old_children, parent_node.cast(),
                            );
                        }
                        _ => {}
                    }
                    crate::lock_helpers::__mcs_rwlock_writer_unlock_noirq(
                        child_update, update_node.cast(),
                    );
                    if terminate_release_child_needed_result(free_child) != 0 {
                        release_process(child);
                    }
                    cursor = next;
                }
                crate::lock_helpers::__mcs_rwlock_writer_unlock(hash_lock, irq_node);
            }
        }
    }

    /// Complete the original supported termination control and ownership order.
    ///
    /// # Safety
    /// The original current Thread/Process/VM/resource graph stays valid through
    /// the exact lock and release edges below. Final current-thread destruction
    /// must retain the executing stack and CPU scheduler handoff until schedule;
    /// this module neither supplies that authority nor creates a reference.
    /// Legacy void ptrace detach must consume its report-list edge; a future
    /// fallible reservation binder cannot be substituted without propagation.
    /// The original selected allocation domain also requires a nonnegative peer
    /// count for which `count * sizeof(int)` fits the allocator's C int size and
    /// matches the number of peer nodes under the held reader lock. No claim is
    /// made about C signed-overflow or implementation-defined narrowing cases.
    #[export_name = "terminate"]
    pub unsafe extern "C" fn f03_terminate_whole_v1(rc: CInt, sig: CInt) {
        let mut irq_node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        let mut update_node = MaybeUninit::<McsRwlockNode>::uninit();
        let mut parent_node = MaybeUninit::<McsRwlockNode>::uninit();
        let mut pid1_node = MaybeUninit::<McsRwlockNode>::uninit();
        // SAFETY: This is the exact borrowed current graph, not an owned Rust
        // reference. Each callback receives the original lock/node/argument.
        unsafe {
            let local = crate::cls::get_this_cpu_local_var();
            let resources = (*local).resource_set;
            let current = (*crate::cls::get_this_cpu_local_var()).current;
            let process = (*current).proc;
            let pid1 = (*resources).pid1;
            let perf = (*process).monitoring_event;
            if !perf.is_null() {
                original_sync_child_event(perf);
            }
            let update = addr_of_mut!((*process).update_lock).cast();
            let threads = addr_of_mut!((*process).threads_lock).cast();
            crate::lock_helpers::__mcs_rwlock_writer_lock_noirq(
                update, update_node.as_mut_ptr().cast(),
            );
            crate::lock_helpers::__mcs_rwlock_writer_lock(threads, irq_node.as_mut_ptr());
            if terminate_process_exited_result((*process).status) != 0 {
                debug!(0, b"%s: PID: %d, TID: %d PS_EXITED already\n\0",
                    c"terminate".as_ptr(), (*process).pid, (*current).tid);
                crate::cls::preempt_disable();
                account_time(current, process);
                (*current).status = PS_EXITED;
                (*current).exit_status = (*process).group_exit_status as CInt;
                f03_thread_exit_signal_v1(current);
                crate::lock_helpers::__mcs_rwlock_writer_unlock(threads, irq_node.as_mut_ptr());
                crate::lock_helpers::__mcs_rwlock_writer_unlock_noirq(
                    update, update_node.as_mut_ptr().cast(),
                );
                release_thread(current);
                // No access through current/process after this release.
                crate::cls::preempt_enable();
                schedule();
                return;
            }
            debug!(1, b"%s: PID: %d, TID: %d setting PS_EXITED\n\0",
                c"terminate".as_ptr(), (*process).pid, (*current).tid);
            account_time(current, process);
            let exit_status = terminate_status_result(rc, sig);
            (*process).group_exit_status = exit_status as CULong;
            (*current).exit_status = exit_status;
            (*process).status = PS_EXITED;
            crate::lock_helpers::__mcs_rwlock_writer_unlock(threads, irq_node.as_mut_ptr());
            crate::lock_helpers::__mcs_rwlock_writer_unlock_noirq(
                update, update_node.as_mut_ptr().cast(),
            );
            original_terminate_mcexec(rc, sig);
            crate::lock_helpers::__mcs_rwlock_writer_lock(threads, irq_node.as_mut_ptr());
            process_list_detach_result(addr_of_mut!((*current).siblings_list));
            crate::lock_helpers::__mcs_rwlock_writer_unlock(threads, irq_node.as_mut_ptr());

            crate::lock_helpers::__mcs_rwlock_reader_lock(threads, irq_node.as_mut_ptr());
            let head = addr_of_mut!((*process).threads_list);
            let mut cursor = (*head).next;
            let mut count: CInt = 0;
            while cursor != head {
                let thread = thread_from_sibling(cursor);
                if terminate_thread_is_other_result(thread.cast(), current.cast()) != 0 {
                    count = count.wrapping_add(1);
                }
                cursor = (*cursor).next;
            }
            let mut ids: *mut CInt = null_mut();
            if count != 0 {
                ids = crate::mem_helpers::kmalloc_tracked(
                    count.wrapping_mul(size_of::<CInt>() as CInt), NOWAIT,
                    SOURCE_FILE.as_ptr().cast_mut().cast(), ORIGIN_LINES[3],
                ).cast();
                if !ids.is_null() {
                    cursor = (*head).next;
                    let mut index = 0;
                    while cursor != head {
                        let thread = thread_from_sibling(cursor);
                        if terminate_thread_is_other_result(thread.cast(), current.cast()) != 0 {
                            ids.add(index).write((*thread).tid);
                            index += 1;
                        }
                        cursor = (*cursor).next;
                    }
                }
            }
            crate::lock_helpers::__mcs_rwlock_reader_unlock(threads, irq_node.as_mut_ptr());
            if !ids.is_null() {
                for index in 0..count as usize {
                    let _ = f06_ptrace_report_signal_kill(
                        current.cast(), (*process).pid, ids.add(index).read(), SIGKILL,
                        core::ptr::null(), 0,
                    );
                }
                crate::mem_helpers::kfree_tracked(
                    ids.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), ORIGIN_LINES[4],
                );
            }
            loop {
                crate::lock_helpers::__mcs_rwlock_reader_lock(threads, irq_node.as_mut_ptr());
                let mut found = false;
                cursor = (*head).next;
                while cursor != head {
                    let thread = thread_from_sibling(cursor);
                    if terminate_thread_active_result((*thread).status) != 0 {
                        found = true;
                        break;
                    }
                    cursor = (*cursor).next;
                }
                crate::lock_helpers::__mcs_rwlock_reader_unlock(threads, irq_node.as_mut_ptr());
                if !found {
                    break;
                }
                schedule();
            }
            crate::lock_helpers::__mcs_rwlock_writer_lock(threads, irq_node.as_mut_ptr());
            process_list_add_tail_result(addr_of_mut!((*current).siblings_list), head);
            crate::lock_helpers::__mcs_rwlock_writer_unlock(threads, irq_node.as_mut_ptr());
            let vm = (*process).vm;
            free_all_process_memory_range(vm);
            let saved = (*process).saved_cmdline;
            if !saved.is_null() {
                crate::mem_helpers::kfree_tracked(
                    saved.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), ORIGIN_LINES[5],
                );
            }
            let reports = addr_of_mut!((*process).report_threads_list);
            while (*reports).next != reports {
                let report = (*reports).next.cast::<u8>()
                    .sub(offset_of!(Thread, report_siblings_list)).cast::<Thread>();
                if terminate_report_thread_ptrace_result((*report).ptrace) != 0 {
                    let release = terminate_report_thread_release_needed_result(
                        ((*report).proc == process) as CInt, (*report).termsig,
                    );
                    if release != 0 {
                        process_thread_termsig_clear_result(
                            report.cast(), offset_of!(Thread, termsig) as CULong, release,
                        );
                    }
                    f03_ptrace_detach_thread_v1(report, 0);
                    if release != 0 {
                        release_thread(report);
                    }
                } else {
                    crate::lock_helpers::__mcs_rwlock_writer_lock(threads, irq_node.as_mut_ptr());
                    process_thread_report_detach_result(
                        report.cast(), offset_of!(Thread, report_proc) as CULong,
                        null_mut(), addr_of_mut!((*report).report_siblings_list),
                    );
                    crate::lock_helpers::__mcs_rwlock_writer_unlock(threads, irq_node.as_mut_ptr());
                    release_thread(report);
                }
            }
            let children = addr_of_mut!((*process).children_list);
            let ptraced_children = addr_of_mut!((*process).ptraced_children_list);
            if terminate_child_cleanup_needed_result(
                ((*children).next == children) as CInt,
                ((*ptraced_children).next == ptraced_children) as CInt,
            ) != 0 {
                reparent_children(
                    resources, process, pid1, irq_node.as_mut_ptr(), update_node.as_mut_ptr(),
                    parent_node.as_mut_ptr(), pid1_node.as_mut_ptr(),
                );
            }
            debug!(2, b"terminate,pid=%d\n\0", (*process).pid);
            f03_finalize_process_v1(process);
            crate::cls::preempt_disable();
            // Original current-thread/process ownership must keep threads valid
            // across finalize_process; this proposal does not invent that ref.
            crate::lock_helpers::__mcs_rwlock_writer_lock(threads, irq_node.as_mut_ptr());
            (*current).status = PS_EXITED;
            crate::lock_helpers::__mcs_rwlock_writer_unlock(threads, irq_node.as_mut_ptr());
            release_thread(current);
            release_process_vm(vm);
            // No current/process/VM pointer is dereferenced beyond this point.
            // Executing-stack retention until scheduler handoff remains a HOLD.
            crate::cls::preempt_enable();
            schedule();
            kprintf(c"%s: ERROR: returned from terminate() -> schedule()\n".as_ptr(),
                c"terminate".as_ptr());
            crate::abort::panic(c"panic".as_ptr());
        }
    }

    #[no_mangle]
    #[used]
    pub static f03_terminate_Rust_ABI_v1: [CULong; 59] = [
        size_of::<crate::abi::Thread>() as CULong,
        core::mem::align_of::<crate::abi::Thread>() as CULong,
        offset_of!(crate::abi::Thread, proc) as CULong,
        offset_of!(crate::abi::Thread, vm) as CULong,
        offset_of!(crate::abi::Thread, status) as CULong,
        offset_of!(crate::abi::Thread, exit_status) as CULong,
        offset_of!(crate::abi::Thread, user_tsc) as CULong,
        offset_of!(crate::abi::Thread, system_tsc) as CULong,
        offset_of!(crate::abi::Thread, tid) as CULong,
        offset_of!(crate::abi::Thread, siblings_list) as CULong,
        offset_of!(crate::abi::Thread, report_siblings_list) as CULong,
        offset_of!(crate::abi::Thread, report_proc) as CULong,
        offset_of!(crate::abi::Thread, ptrace) as CULong,
        offset_of!(crate::abi::Thread, termsig) as CULong,
        size_of::<crate::abi::Process>() as CULong,
        core::mem::align_of::<crate::abi::Process>() as CULong,
        offset_of!(crate::abi::Process, monitoring_event) as CULong,
        offset_of!(crate::abi::Process, update_lock) as CULong,
        offset_of!(crate::abi::Process, threads_lock) as CULong,
        offset_of!(crate::abi::Process, status) as CULong,
        offset_of!(crate::abi::Process, group_exit_status) as CULong,
        offset_of!(crate::abi::Process, utime) as CULong,
        offset_of!(crate::abi::Process, stime) as CULong,
        offset_of!(crate::abi::Process, pid) as CULong,
        offset_of!(crate::abi::Process, threads_list) as CULong,
        offset_of!(crate::abi::Process, vm) as CULong,
        offset_of!(crate::abi::Process, saved_cmdline) as CULong,
        offset_of!(crate::abi::Process, report_threads_list) as CULong,
        offset_of!(crate::abi::Process, children_list) as CULong,
        offset_of!(crate::abi::Process, ptraced_children_list) as CULong,
        offset_of!(crate::abi::Process, ppid_parent) as CULong,
        offset_of!(crate::abi::Process, parent) as CULong,
        offset_of!(crate::abi::Process, siblings_list) as CULong,
        offset_of!(crate::abi::Process, ptraced_siblings_list) as CULong,
        offset_of!(crate::abi::Process, children_lock) as CULong,
        offset_of!(crate::abi::Process, hash_list) as CULong,
        size_of::<crate::abi::ResourceSet>() as CULong,
        core::mem::align_of::<crate::abi::ResourceSet>() as CULong,
        offset_of!(crate::abi::ResourceSet, process_hash) as CULong,
        offset_of!(crate::abi::ResourceSet, pid1) as CULong,
        size_of::<crate::abi::ProcessHash>() as CULong,
        core::mem::align_of::<crate::abi::ProcessHash>() as CULong,
        offset_of!(crate::abi::ProcessHash, list) as CULong,
        offset_of!(crate::abi::ProcessHash, lock) as CULong,
        size_of::<crate::abi::TimeSpec>() as CULong,
        core::mem::align_of::<crate::abi::TimeSpec>() as CULong,
        offset_of!(crate::abi::TimeSpec, tv_sec) as CULong,
        offset_of!(crate::abi::TimeSpec, tv_nsec) as CULong,
        size_of::<crate::abi::AbiListHead>() as CULong,
        core::mem::align_of::<crate::abi::AbiListHead>() as CULong,
        offset_of!(crate::abi::AbiListHead, next) as CULong,
        offset_of!(crate::abi::AbiListHead, prev) as CULong,
        size_of::<McsRwlockNode>() as CULong,
        core::mem::align_of::<McsRwlockNode>() as CULong,
        size_of::<McsRwlockNodeIrqsave>() as CULong,
        core::mem::align_of::<McsRwlockNodeIrqsave>() as CULong,
        size_of::<McsRwlockLock>() as CULong,
        core::mem::align_of::<McsRwlockLock>() as CULong,
        PROCESS_HASH_SIZE as CULong,
    ];

const _: unsafe extern "C" fn(CInt, CInt) = f03_terminate_whole_v1;
