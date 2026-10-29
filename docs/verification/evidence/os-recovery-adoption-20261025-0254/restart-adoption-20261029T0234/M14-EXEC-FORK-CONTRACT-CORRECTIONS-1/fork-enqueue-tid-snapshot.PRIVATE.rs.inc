// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Complete local clone reporting and the existing final enqueue/return path.
///
/// # Safety
/// The caller has completed thread/process publication and, for non-CLONE_VM,
/// the unchanged host clone request successfully. `new` remains retained through
/// report, TID snapshot and enqueue. The result is a scalar thereafter. `oldproc`
/// and both report lists are live in the reporting branch; their genuine lock
/// serializes list membership. No host request, ownership release or ACK is added.
#[no_mangle]
pub unsafe extern "C" fn f03_clone_finish_report_enqueue_v1(
    new: *mut Thread,
    oldproc: *mut Process,
    flags: CInt,
    termsig: CInt,
    cpuid: CInt,
    ptrace_event: CInt,
) -> CInt {
    if flags & CLONE_VM != 0 && clone_report_thread_result(flags, termsig) != 0 {
        let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        // SAFETY: The original live process owns this lock. The real writer
        // provider initializes the saved IRQ slot before unlock consumes it.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_writer_lock(
                addr_of_mut!((*oldproc).threads_lock).cast(),
                node.as_mut_ptr(),
            );
        }
        // SAFETY: Under threads_lock, use the genuine layout and list provider.
        // Its ignored result and partial guard semantics match the C call.
        unsafe {
            let _ = crate::process_helpers::process_thread_report_attach_result(
                new.cast(),
                offset_of!(Thread, termsig) as CULong,
                1,
                termsig,
                offset_of!(Thread, report_proc) as CULong,
                oldproc.cast(),
                addr_of_mut!((*new).report_siblings_list),
                addr_of_mut!((*oldproc).report_threads_list),
            );
            crate::lock_helpers::__mcs_rwlock_writer_unlock(
                addr_of_mut!((*oldproc).threads_lock).cast(),
                node.as_mut_ptr(),
            );
        }
        // SAFETY: The published thread is retained. Preserve hold after unlock,
        // including the existing void-style ignored result at this caller edge.
        unsafe { let _ = crate::process_helpers::hold_thread(new); }
    }

    // Snapshot while the caller still owns the prepared child. Once enqueued,
    // the child may run and release its last reference before this caller resumes.
    // The TID was committed before publication and is the result of this clone.
    let child_tid = unsafe { addr_of!((*new).tid).read() };
    // SAFETY: This is the original live prepared thread and chosen CPU. Call the
    // genuine void public enqueuer, not its checked internal alternative.
    unsafe { crate::sched_helpers::runq_add_thread(new, cpuid) };
    if ptrace_event != 0 {
        // SAFETY: The original caller's execution/IRQ context permits schedule.
        // The scalar snapshot avoids accessing the child after publication.
        unsafe { schedule() };
    }
    child_tid
}
