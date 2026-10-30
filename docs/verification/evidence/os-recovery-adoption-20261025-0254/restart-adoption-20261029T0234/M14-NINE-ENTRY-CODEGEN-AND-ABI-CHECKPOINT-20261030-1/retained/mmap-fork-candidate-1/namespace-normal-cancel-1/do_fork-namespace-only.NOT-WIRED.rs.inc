// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete current owned-fork/native-TID/scheduler-policy projection. Unselected.
#[cfg(f03_do_fork_owned_candidate)]
mod f03_fork_whole_owned_v1 {
    use core::ffi::c_void;
    use core::mem::{size_of, MaybeUninit};
    use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile};

    use crate::abi::{CInt, CLong, CULong, CpuSet, Memobj, Process, Thread, PTHREAD_ROUTINE_LEN};
    use crate::debug::Ddebug;

    use super::{
        clone_flags_result, clone_host_parent_flags_result, clone_pthread_marker_result,
        clone_use_last_cpu_result, f03_clone_commit_tid_addresses_v1,
        f03_clone_destroy_legacy_thread_v1, f03_clone_finish_report_enqueue_v1,
        f03_clone_initialize_execution_state_v1, f03_clone_prepare_remote_argument_v1,
        f03_clone_publish_thread_process_v1, f03_clone_release_empty_tid_table_v1,
        f03_clone_vm_tid_pool_v1, ptrace_clone_event_result, F03CloneTidDebug, F03TidPoolOrigins,
        CLONE_THREAD, CLONE_VM,
    };

    #[repr(C)]
    struct ForkOrigins {
        file: *const i8,
        remote_argument_line: CInt,
        empty_table_line: CInt,
        saved_command_line: CInt,
        ptrace_report: unsafe extern "C" fn(*mut Thread, *mut Thread, CInt) -> CInt,
    }

    unsafe extern "C" {
        static f03_fork_origins_v1: ForkOrigins;
        static f03_fork_pool_origins_v1: F03TidPoolOrigins;
        static f03_fork_tid_debug_v1: F03CloneTidDebug;
        static f03_fork_constants_v1: [CULong; 4];
        static mut f03_fork_debug_v1: [Ddebug; 11];
        fn kprintf(format: *const i8, ...) -> CInt;
        // Genuine existing cross-file constructor/CPU policy providers. This
        // proposal does not claim their remaining C implementation retired.
        #[link_name = "clone_thread"]
        fn original_clone_thread(
            parent: *mut Thread, pc: CULong, sp: CULong, flags: CInt,
        ) -> *mut Thread;
        #[link_name = "obtain_clone_cpuid"]
        fn original_obtain_cpuid(mask: *mut CpuSet, use_last: CInt) -> CInt;
    }

    macro_rules! debug {
        ($index:expr, $format:expr $(, $value:expr)* $(,)?) => {{
            // SAFETY: Exact original lexical metadata and scalar variadic ABI.
            unsafe {
                if read_volatile(addr_of!(f03_fork_debug_v1[$index].line_flags)) >> 24 != 0 {
                    kprintf($format.as_ptr().cast() $(, $value)*);
                }
            }
        }};
    }

    /// Copy the diagnostic path during the actual VM-reader ownership interval.
    ///
    /// # Safety
    /// Current parent/VM remains live. A linked range owns its memobj/path until
    /// writer removal; the path is an immutable terminated kernel string under
    /// that provider contract. No range/object/path pointer escapes this call.
    unsafe fn snapshot_routine(
        old: *mut Thread, routine: CULong, snapshot: *mut u8,
    ) -> (bool, bool) {
        if routine == 0 {
            return (false, false);
        }
        // SAFETY: Genuine reader lock prevents list/range reclamation here. All
        // stores target the caller's disjoint fixed-size stack byte array.
        unsafe {
            let vm = (*old).vm;
            let lock = addr_of_mut!((*vm).memory_range_lock);
            crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(lock.cast());
            let range = crate::process_helpers::lookup_process_memory_range(
                vm, routine, routine.wrapping_add(1),
            );
            let mut helper = false;
            let mut found = false;
            if !range.is_null() && !(*range).memobj.is_null() {
                let object = (*range).memobj.cast::<Memobj>();
                let path = (*object).path;
                if !path.is_null() {
                    found = true;
                    helper = crate::string::strstr(path, c"omp.so".as_ptr()).is_null()
                        && crate::string::strstr(path, c"libfj90".as_ptr()).is_null();
                    let mut index = 0;
                    while index + 1 < PTHREAD_ROUTINE_LEN {
                        let byte = path.add(index).read() as u8;
                        snapshot.add(index).write(byte);
                        if byte == 0 {
                            break;
                        }
                        index += 1;
                    }
                    // Bound only the diagnostic representation. Kernel paths
                    // that fit the original destination keep identical bytes.
                    snapshot.add(PTHREAD_ROUTINE_LEN - 1).write(0);
                }
            }
            crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(lock.cast());
            (helper, found)
        }
    }

    /// Snapshot only the scalar needed by the host clone policy.
    /// The live current process owns its parent edge. Reparent/removal must take
    /// this same process update_lock for writing; no parent pointer escapes.
    unsafe fn snapshot_host_parent_flags(process: *mut Process, flags: CInt) -> Result<CULong, CInt> {
        let mut node = MaybeUninit::<crate::lock_helpers::McsRwlockNodeIrqsave>::uninit();
        unsafe {
            let lock = addr_of_mut!((*process).update_lock).cast();
            crate::lock_helpers::__mcs_rwlock_reader_lock(lock, node.as_mut_ptr());
            let parent = (*process).ppid_parent;
            let result = if parent.is_null() {
                Err(-super::EINVAL)
            } else {
                Ok(CLong::from(clone_host_parent_flags_result(flags, (*parent).pid)) as CULong)
            };
            crate::lock_helpers::__mcs_rwlock_reader_unlock(lock, node.as_mut_ptr());
            result
        }
    }

    /// Acquire one extra child storage reference before graph/runqueue publication.
    /// The existing constructor/TID-pool ownership must keep storage live before
    /// this checked RMW; earlier TID-slot publication remains a separate review.
    /// This is a new pin, never a guessed constructor or scheduler credit.
    unsafe fn pin_child_before_graph_publication(child: *mut Thread) -> Result<(), CInt> {
        let counter = unsafe {
            core::sync::atomic::AtomicI32::from_ptr(addr_of_mut!((*child).refcount.counter))
        };
        pin_live_counter(counter)
    }

    // Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
    fn pin_live_counter(counter: &core::sync::atomic::AtomicI32) -> Result<(), CInt> {
        use core::sync::atomic::Ordering;
        let mut old = counter.load(Ordering::SeqCst);
        loop {
            // These classifications return without touching the counter. The
            // caller must quarantine UNKNOWN ownership; it cannot reset refs.
            if old <= 0 { return Err(-super::EINVAL); }
            if old == i32::MAX { return Err(-75); } // EOVERFLOW.
            match counter.compare_exchange_weak(old, old + 1, Ordering::SeqCst, Ordering::SeqCst) {
                Ok(_) => return Ok(()),
                Err(actual) => old = actual,
            }
        }
    }

    // Retained owner records are preallocated BEFORE CPU/child construction.
    // There is no reap/retry/free API: UNKNOWN records preserve every captured
    // handle and obligation for separate owner review. Numeric fields are not
    // evidence that the retained objects remain safe to dereference.
    #[repr(C)]
    struct UnknownCloneRecord {
        next: *mut UnknownCloneRecord,
        disposition: CInt, // 1 == UNKNOWN; no successful pin exists.
        reason: CInt,
        child: *mut Thread,
        process: *mut Process,
        vm: *mut crate::abi::ProcessVm,
        cpu: CInt,
        cpu_reservation_obtained: CInt,
        child_tid: CInt,
        tid_table_created: CInt,
        tid_table: *mut c_void,
        tid_count: CInt,
    }

    #[used]
    static UNKNOWN_CLONES: core::sync::atomic::AtomicPtr<UnknownCloneRecord> =
        core::sync::atomic::AtomicPtr::new(null_mut());

    struct PendingCloneQuarantine { record: *mut UnknownCloneRecord }
    impl PendingCloneQuarantine {
        unsafe fn reserve(needed: bool) -> Result<Self, CInt> {
            if !needed { return Ok(Self { record: null_mut() }); }
            let record = unsafe {
                crate::mem_helpers::kmalloc(size_of::<UnknownCloneRecord>() as CInt, 0)
            }.cast::<UnknownCloneRecord>();
            if record.is_null() { return Err(-super::ENOMEM); }
            // Slot owns only its private allocation until an UNKNOWN transfer.
            Ok(Self { record })
        }

        unsafe fn retain_unknown(mut self, mut snapshot: UnknownCloneRecord) {
            use core::sync::atomic::Ordering;
            // The caller reserves this slot before construction on every
            // CLONE_VM route. This transfer is infallible and allocation-free.
            let record = self.record;
            self.record = null_mut();
            snapshot.disposition = 1;
            unsafe { record.write(snapshot) };
            let mut head = UNKNOWN_CLONES.load(Ordering::Acquire);
            loop {
                unsafe { (*record).next = head };
                match UNKNOWN_CLONES.compare_exchange_weak(
                    head, record, Ordering::AcqRel, Ordering::Acquire,
                ) {
                    Ok(_) => return,
                    Err(actual) => head = actual,
                }
            }
        }
    }
    impl Drop for PendingCloneQuarantine {
        fn drop(&mut self) {
            // Frees only an unused record. Never touches child/VM/TID/CPU refs.
            if !self.record.is_null() {
                unsafe { crate::mem_helpers::kfree(self.record.cast()) };
            }
        }
    }

    /// Complete supported do_fork orchestration with original ownership handoffs.
    ///
    /// # Safety
    /// The running parent, process and initialized user context remain live. The
    /// CPU reservation/constructor/gettid/publication providers retain their real
    /// contracts; no successful return invents a child pin or host ACK. All child
    /// borrows stop at the original destructive or retained-disposition edges.
    pub unsafe extern "C" fn f03_do_fork_owned_v1(
        flags: CInt,
        new_stack: CULong,
        parent_tid: CULong,
        child_tid: CULong,
        tls: CULong,
        current_pc: CULong,
        current_stack: CULong,
    ) -> CULong {
        let old = unsafe { (*crate::cls::get_this_cpu_local_var()).current };
        let old_process = unsafe { (*old).proc };
        let term_signal = flags & 0xff;
        debug!(0, concat!("%s,flags=%08x,newsp=%lx,ptidptr=%lx,",
            "ctidptr=%lx,tls=%lx,curpc=%lx,cursp=%lx\0").as_bytes(),
            c"do_fork".as_ptr(), flags, new_stack, parent_tid, child_tid,
            tls, current_pc, current_stack);
        debug!(1, concat!("do_fork(): stack_pointr passed in: 0x%lX, ",
            "stack pointer of caller: 0x%lx\n\0").as_bytes(), new_stack, current_stack);
        // SAFETY: Real current full context and original register getter. Clone3
        // bypasses the legacy pthread-start marker exactly as in selected C.
        let marker = unsafe {
            crate::x86_cpu_helpers::ihk_mc_syscall_number((*old).uctx)
                != f03_fork_constants_v1[0]
                && clone_pthread_marker_result(flags, new_stack, parent_tid) != 0
        };
        if marker {
            unsafe { addr_of_mut!((*old).clone_pthread_start_routine).write(parent_tid) };
            debug!(2, b"%s: clone_pthread_start_routine: 0x%lx\n\0",
                c"do_fork".as_ptr(), parent_tid);
            return 0;
        }
        let routine = unsafe { addr_of!((*old).clone_pthread_start_routine).read() };
        unsafe { addr_of_mut!((*old).clone_pthread_start_routine).write(0) };
        let parent_cpu = unsafe { (*old).cpu_id };
        let error = unsafe { clone_flags_result(flags, (*old_process).coredump_barrier_count) };
        if error != 0 {
            if (flags & CLONE_VM != 0) != (flags & CLONE_THREAD != 0) {
                unsafe {
                    kprintf(c"clone(): ERROR: CLONE_VM and CLONE_THREAD should be set together\n"
                        .as_ptr());
                }
            }
            return error as CLong as CULong;
        }
        // Reserve retained UNKNOWN storage before any CPU or child obligation.
        let quarantine = match unsafe { PendingCloneQuarantine::reserve(flags & CLONE_VM != 0) } {
            Ok(slot) => slot,
            Err(error) => return error as CLong as CULong,
        };
        unsafe {
            if (*old_process).uti_thread_rank != 0 {
                (*old).mod_clone = if (*old_process).clone_count.wrapping_add(1)
                    == (*old_process).uti_thread_rank
                {
                    f03_fork_constants_v1[1] as CInt
                } else {
                    f03_fork_constants_v1[2] as CInt
                };
                kprintf(c"%s: mod_clone is set to %d\n".as_ptr(),
                    c"do_fork".as_ptr(), (*old).mod_clone);
            }
        }
        let mut path = [0_u8; PTHREAD_ROUTINE_LEN];
        let (helper, has_path) = unsafe { snapshot_routine(old, routine, path.as_mut_ptr()) };
        if has_path {
            debug!(3, b"clone(): %s thread from %s\n\0",
                if helper { c"helper" } else { c"compute" }.as_ptr(), path.as_ptr());
        }
        let mut affinity = MaybeUninit::<CpuSet>::uninit();
        let mut inherit_affinity = false;
        let cpu = if helper {
            unsafe { crate::x86_local::ihk_mc_get_processor_id() }
        } else {
            let use_snapshot = unsafe {
                flags & CLONE_THREAD != 0 && (*old_process).uti_thread_rank == 0
                    && (*old).mod_clone == 0 && (*old_process).uti_use_last_cpu == 0
            };
            let cpu = unsafe {
                if use_snapshot {
                    let result = crate::sched_helpers::sched_clone_affinity_snapshot_result(
                        addr_of!((*old).cpu_set) as usize,
                        addr_of!((*old_process).cpu_set) as usize,
                        affinity.as_mut_ptr() as usize, size_of::<CpuSet>(),
                        crate::ap::num_processors,
                    );
                    if result != 0 {
                        let again = unsafe { f03_fork_constants_v1[3] as CInt };
                        return -(again as CLong) as CULong;
                    }
                    inherit_affinity = true;
                    original_obtain_cpuid(affinity.as_mut_ptr(), 0)
                } else {
                    original_obtain_cpuid(
                        addr_of_mut!((*old_process).cpu_set),
                        clone_use_last_cpu_result(
                            (*old).mod_clone, (*old_process).uti_use_last_cpu,
                        ),
                    )
                }
            };
            if cpu == -1 {
                unsafe { kprintf(c"do_fork,core not available\n".as_ptr()) };
                let again = unsafe { f03_fork_constants_v1[3] as CInt };
                return -(again as CLong) as CULong;
            }
            cpu
        };
        let mut constructor = null_mut();
        let stack = if new_stack != 0 { new_stack } else { current_stack };
        let new = unsafe {
            if flags & CLONE_VM == 0 {
                crate::fork_control_guest::process_fork_construct_current_v1(
                    old, current_pc, stack, flags, cpu, addr_of_mut!(constructor),
                )
            } else {
                original_clone_thread(old, current_pc, stack, flags)
            }
        };
        if new.is_null() {
            unsafe { crate::sched_helpers::release_cpuid(cpu) };
            return -super::ENOMEM as CLong as CULong;
        }
        // SAFETY: Constructor still owns child fields. Only copied path bytes
        // survive VM unlock. snprintf bounds the original diagnostic destination.
        unsafe {
            let destination = addr_of_mut!((*new).pthread_routine).cast::<i8>();
            if routine != 0 && has_path {
                crate::numparse::snprintf(destination, PTHREAD_ROUTINE_LEN,
                    c"0x%lx @ %s".as_ptr(), routine, path.as_ptr());
            } else {
                crate::numparse::snprintf(destination, PTHREAD_ROUTINE_LEN,
                    c"%s".as_ptr(), c"[unknown]".as_ptr());
            }
        }
        let new_process = unsafe { (*new).proc };
        let mut error = 0;
        let mut table_created = 0;
        // End-label disposition is local control flow, never an ownership token.
        let release_ids = 'prepared: {
            if inherit_affinity {
                let result = unsafe {
                    crate::sched_helpers::sched_clone_affinity_inherit_result(
                        addr_of_mut!((*new).cpu_set) as usize,
                        affinity.as_ptr() as usize, size_of::<CpuSet>(),
                    )
                };
                if result != 0 {
                    error = -super::EINVAL;
                    break 'prepared false;
                }
            }
            unsafe {
                let address_space = (*(*new).vm).address_space;
                crate::process_helpers::cpu_set(cpu,
                    addr_of_mut!((*address_space).cpu_set),
                    addr_of_mut!((*address_space).cpu_set_lock));
            }
            if flags & CLONE_VM != 0 {
                let next = unsafe {
                    f03_clone_vm_tid_pool_v1(new, new_process, addr_of_mut!(table_created),
                        addr_of_mut!(error), addr_of!(f03_fork_pool_origins_v1))
                };
                if next != 0 {
                    break 'prepared next == 2;
                }
            } else {
                // This is the actual supported owned graph transaction. The legacy
                // partial request1 is not constructed, copied, zeroed or published.
                let mut outcome =
                    MaybeUninit::<crate::fork_control_guest::CallerForkOutcome>::uninit();
                let host_flags = match unsafe { snapshot_host_parent_flags(old_process, flags) } {
                    Ok(value) => value,
                    Err(value) => { error = value; break 'prepared false; }
                };
                let result = unsafe {
                    crate::fork_control_guest::process_fork_owned_caller_runnable_current_v2(
                        old, new, cpu,
                        host_flags,
                        constructor, flags, parent_cpu, child_tid, outcome.as_mut_ptr(),
                    )
                };
                if result != 0 {
                    error = result;
                    break 'prepared false;
                }
                // SAFETY: Non-null output is fully initialized by that real provider.
                let outcome = unsafe { outcome.assume_init() };
                if outcome.disposition == 0 {
                    error = outcome.error;
                    break 'prepared false;
                }
                // Actual Rust-retained disposition bypasses ALL caller destruction
                // and CPU cleanup, including uncertain publication/failure paths.
                return outcome.error as CLong as CULong;
            }
            let tid_error = unsafe {
                f03_clone_commit_tid_addresses_v1(new, flags, parent_tid, child_tid, 1,
                    addr_of_mut!(error), addr_of!(f03_fork_tid_debug_v1))
            };
            if tid_error != 0 {
                break 'prepared true;
            }
            unsafe {
                f03_clone_initialize_execution_state_v1(old, new, flags, tls, parent_cpu,
                    addr_of_mut!(f03_fork_debug_v1[9]));
                if f03_clone_prepare_remote_argument_v1(old, new, addr_of_mut!(error),
                    f03_fork_origins_v1.file, f03_fork_origins_v1.remote_argument_line) != 0
                {
                    break 'prepared true;
                }
                // Capture handles while the caller still has its preexisting
                // borrowed constructor/pool context, BEFORE classifying the ref.
                // A bad ref does not grant any subsequent object dereference.
                let mut unknown_node = MaybeUninit::<crate::lock_helpers::McsRwlockNodeIrqsave>::uninit();
                crate::lock_helpers::__mcs_rwlock_reader_lock(
                    addr_of_mut!((*new_process).threads_lock).cast(), unknown_node.as_mut_ptr(),
                );
                let mut unknown = UnknownCloneRecord {
                    next: null_mut(), disposition: 0, reason: 0,
                    child: new, process: new_process, vm: (*new).vm,
                    cpu, cpu_reservation_obtained: (!helper) as CInt,
                    child_tid: (*new).tid, tid_table_created: table_created,
                    tid_table: (*new_process).tids.cast(), tid_count: (*new_process).nr_tids,
                };
                crate::lock_helpers::__mcs_rwlock_reader_unlock(
                    addr_of_mut!((*new_process).threads_lock).cast(), unknown_node.as_mut_ptr(),
                );
                if let Err(value) = pin_child_before_graph_publication(new) {
                    unknown.reason = value;
                    // UNKNOWN transfer: no ref reset/decrement, TID release,
                    // CPU release, destructor, callback or second pin attempt.
                    quarantine.retain_unknown(unknown);
                    return -super::EBUSY as CLong as CULong;
                }
                // The new pin keeps child/VM/process storage through publication,
                // ptrace callbacks, report attachment, enqueue and optional schedule.
                f03_clone_publish_thread_process_v1(new, old_process, new_process, flags);
            }
            let mut ptrace_event = 0;
            unsafe {
                if (*old).ptrace != 0 {
                    ptrace_event = ptrace_clone_event_result((*old).ptrace, flags);
                    if ptrace_event != 0 {
                        // Genuine existing C adapter/real Rust body and wake provider;
                        // its ignored return and reservation HOLD are not hidden.
                        (f03_fork_origins_v1.ptrace_report)(old, new, ptrace_event);
                    }
                }
                debug!(8, b"clone: kicking scheduler!,cpuid=%d pid=%d tid %d -> tid=%d\n\0",
                    cpu, (*new_process).pid, (*old).tid, (*new).tid);
                // Reuse the existing helper with its TID-before-enqueue snapshot.
                let child_tid = f03_clone_finish_report_enqueue_v1(
                    new, old_process, flags, term_signal, cpu, ptrace_event,
                );
                // Last use of new: consume only our added pin, outside every
                // graph/report lock. This may destroy it; return the copied scalar.
                crate::process_helpers::release_thread(new);
                return child_tid as CLong as CULong;
            }
        };
        if release_ids {
            // Only CLONE_VM reaches this edge in the supported owned projection.
            unsafe {
                f03_clone_release_empty_tid_table_v1(new_process, table_created,
                    f03_fork_origins_v1.file, f03_fork_origins_v1.empty_table_line);
            }
        }
        if !constructor.is_null() {
            let cancel = unsafe {
                crate::fork_control_guest::process_fork_cancel_constructed_current_v1(
                    constructor,
                )
            };
            if cancel != 0 {
                // Failed/partial cleanup retains its opaque graph and CPU obligation.
                return cancel as CLong as CULong;
            }
        } else {
            unsafe {
                f03_clone_destroy_legacy_thread_v1(new, new_process, flags,
                    f03_fork_origins_v1.file, f03_fork_origins_v1.saved_command_line);
            }
        }
        unsafe { crate::sched_helpers::release_cpuid(cpu) };
        error as CLong as CULong
    }

    const _: () = {
        assert!(size_of::<crate::abi::IhkAtomic>() == size_of::<core::sync::atomic::AtomicI32>());
        assert!(core::mem::align_of::<crate::abi::IhkAtomic>() == core::mem::align_of::<core::sync::atomic::AtomicI32>());
        assert!(core::mem::offset_of!(crate::abi::IhkAtomic, counter) == 0);
        assert!(size_of::<crate::abi::McsRwlockLock>() == size_of::<crate::lock_helpers::McsRwlockLock>());
        assert!(core::mem::align_of::<crate::abi::McsRwlockLock>() == core::mem::align_of::<crate::lock_helpers::McsRwlockLock>());
    };

    // Compiler-only real C/Rust layout view; no runtime ownership getter.
    #[used]
    pub static f03_do_fork_Rust_ABI_v1: [CULong; 46] = [
        size_of::<crate::abi::Thread>() as CULong,
        core::mem::align_of::<crate::abi::Thread>() as CULong,
        core::mem::offset_of!(crate::abi::Thread, proc) as CULong,
        core::mem::offset_of!(crate::abi::Thread, vm) as CULong,
        core::mem::offset_of!(crate::abi::Thread, cpu_id) as CULong,
        core::mem::offset_of!(crate::abi::Thread, uctx) as CULong,
        core::mem::offset_of!(crate::abi::Thread, clone_pthread_start_routine) as CULong,
        core::mem::offset_of!(crate::abi::Thread, mod_clone) as CULong,
        core::mem::offset_of!(crate::abi::Thread, pthread_routine) as CULong,
        core::mem::offset_of!(crate::abi::Thread, cpu_set) as CULong,
        core::mem::offset_of!(crate::abi::Thread, tid) as CULong,
        core::mem::offset_of!(crate::abi::Thread, refcount) as CULong,
        size_of::<crate::abi::Process>() as CULong,
        core::mem::align_of::<crate::abi::Process>() as CULong,
        core::mem::offset_of!(crate::abi::Process, coredump_barrier_count) as CULong,
        core::mem::offset_of!(crate::abi::Process, uti_thread_rank) as CULong,
        core::mem::offset_of!(crate::abi::Process, clone_count) as CULong,
        core::mem::offset_of!(crate::abi::Process, uti_use_last_cpu) as CULong,
        core::mem::offset_of!(crate::abi::Process, cpu_set) as CULong,
        core::mem::offset_of!(crate::abi::Process, ppid_parent) as CULong,
        core::mem::offset_of!(crate::abi::Process, pid) as CULong,
        core::mem::offset_of!(crate::abi::Process, threads_lock) as CULong,
        core::mem::offset_of!(crate::abi::Process, nr_tids) as CULong,
        core::mem::offset_of!(crate::abi::Process, tids) as CULong,
        size_of::<crate::abi::McexecTid>() as CULong,
        core::mem::align_of::<crate::abi::McexecTid>() as CULong,
        core::mem::offset_of!(crate::abi::McexecTid, tid) as CULong,
        core::mem::offset_of!(crate::abi::McexecTid, thread) as CULong,
        size_of::<CpuSet>() as CULong,
        core::mem::align_of::<CpuSet>() as CULong,
        size_of::<crate::fork_control_guest::CallerForkOutcome>() as CULong,
        core::mem::align_of::<crate::fork_control_guest::CallerForkOutcome>() as CULong,
        core::mem::offset_of!(crate::fork_control_guest::CallerForkOutcome, disposition) as CULong,
        core::mem::offset_of!(crate::fork_control_guest::CallerForkOutcome, error) as CULong,
        core::mem::offset_of!(crate::fork_control_guest::CallerForkOutcome, handle) as CULong,
        core::mem::offset_of!(crate::abi::Process, update_lock) as CULong,
        size_of::<crate::abi::McsRwlockLock>() as CULong,
        core::mem::align_of::<crate::abi::McsRwlockLock>() as CULong,
        size_of::<crate::abi::IhkAtomic>() as CULong,
        core::mem::align_of::<crate::abi::IhkAtomic>() as CULong,
        core::mem::offset_of!(crate::abi::IhkAtomic, counter) as CULong,
        (core::mem::offset_of!(crate::abi::Thread, refcount) + core::mem::offset_of!(crate::abi::IhkAtomic, counter)) as CULong,
        size_of::<CInt>() as CULong,
        core::mem::align_of::<CInt>() as CULong,
        size_of::<core::sync::atomic::AtomicI32>() as CULong,
        core::mem::align_of::<core::sync::atomic::AtomicI32>() as CULong,
    ];
}
