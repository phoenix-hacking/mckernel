// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// ABI field stride stays abi::McsRwlockLock; callback views the identical real
// lock_helpers type. Both existing layouts are repr(C), 64-byte size/alignment.
const _: () = {
    assert!(size_of::<crate::abi::McsRwlockLock>() == size_of::<crate::lock_helpers::McsRwlockLock>());
    assert!(align_of::<crate::abi::McsRwlockLock>() == align_of::<crate::lock_helpers::McsRwlockLock>());
};
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: retire only the live do_kill process-group enumeration/dispatch branch.
// Direct-target permission, pending queue, wakeup and IPI handling remain C.
unsafe extern "C" {
    #[link_name = "do_kill"]
    fn f06_process_group_recursive_do_kill(
        thread: *mut Thread, pid: CInt, tid: CInt, sig: CInt,
        info: *mut SigInfo, ptracecont: CInt,
    ) -> CULong;
}

/// Called only at the existing tid==-1 && pid<=0 branch, after the C caller's
/// signal validation/default-info setup. `hash` is its original resource-set
/// snapshot: no new current-CPU lookup or migration-dependent snapshot is taken.
/// The caller thread and info remain borrowed across all synchronous calls.
/// Processes are borrowed only while each bucket reader lock is held; only PID
/// values survive unlock. No thread/process owner reference is created here.
#[no_mangle]
pub unsafe extern "C" fn arch_do_kill_process_group_result(
    thread: *mut Thread, pid: CInt, sig: CInt, info: *mut SigInfo,
    ptracecont: CInt, hash: *mut crate::abi::ProcessHash,
) -> CInt {
    let mut pgid = pid.wrapping_neg();
    let mut rc: CInt = -ESRCH;
    let mut pids: *mut CInt = null_mut();
    let mut n: CInt = 0;
    let mut nr_pids: CInt = 0;
    let mut sendme = false;
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    if pid == 0 {
        if thread.is_null() || (*(*thread).proc).pid <= 0 {
            return -ESRCH;
        }
        pgid = (*(*thread).proc).pgid;
    }
    // First pass counts peers only, remembering a matching caller separately.
    for i in 0..crate::abi::PROCESS_HASH_SIZE {
        let lock = core::ptr::addr_of_mut!((*hash).lock).cast::<crate::abi::McsRwlockLock>().add(i);
        let head = core::ptr::addr_of_mut!((*hash).list).cast::<AbiListHead>().add(i);
        crate::lock_helpers::__mcs_rwlock_reader_lock(lock.cast(), node.as_mut_ptr());
        let mut pos = (*head).next;
        while pos != head {
            let proc = pos.cast::<u8>().sub(offset_of!(Process, hash_list)).cast::<Process>();
            if pgid == 1 || (*proc).pgid == pgid {
                if !thread.is_null() && (*proc).pid == (*(*thread).proc).pid {
                    sendme = true;
                } else {
                    nr_pids = nr_pids.wrapping_add(1);
                }
            }
            pos = (*pos).next;
        }
        crate::lock_helpers::__mcs_rwlock_reader_unlock(lock.cast(), node.as_mut_ptr());
    }
    if nr_pids != 0 {
        // Same int allocator ABI/extent conversion as the C kmalloc_tracked call.
        pids = crate::mem_helpers::kmalloc_tracked(
            (size_of::<CInt>() as SizeT).wrapping_mul(nr_pids as SizeT) as CInt,
            IHK_MC_AP_NOWAIT,
            concat!(file!(), "\0").as_ptr().cast_mut().cast(), line!() as CInt,
        ).cast();
        if pids.is_null() { return -ENOMEM; }
    } else if !sendme {
        return rc;
    }

    if nr_pids != 0 {
        // The list can change between passes. Cap collection by the first count;
        // shrink delivers only actual collected PIDs, growth never overruns it.
        for i in 0..crate::abi::PROCESS_HASH_SIZE {
            if n == nr_pids { break; }
            let lock = core::ptr::addr_of_mut!((*hash).lock).cast::<crate::abi::McsRwlockLock>().add(i);
            let head = core::ptr::addr_of_mut!((*hash).list).cast::<AbiListHead>().add(i);
            crate::lock_helpers::__mcs_rwlock_reader_lock(lock.cast(), node.as_mut_ptr());
            let mut pos = (*head).next;
            while pos != head {
                let proc = pos.cast::<u8>().sub(offset_of!(Process, hash_list)).cast::<Process>();
                if pgid == 1 || (*proc).pgid == pgid {
                    if !thread.is_null() && (*proc).pid == (*(*thread).proc).pid {
                        sendme = true;
                    } else {
                        *pids.offset(n as isize) = (*proc).pid;
                        n = n.wrapping_add(1);
                        if n == nr_pids { break; }
                    }
                }
                pos = (*pos).next;
            }
            crate::lock_helpers::__mcs_rwlock_reader_unlock(lock.cast(), node.as_mut_ptr());
        }
        let mut i: CInt = 0;
        while i < n {
            // Original unsigned-long do_kill result is assigned to int rc first.
            // Preserve its low32-bit conversion and last-result return policy.
            rc = f06_process_group_recursive_do_kill(
                thread, *pids.offset(i as isize), -1, sig, info, ptracecont,
            ) as CInt;
            i += 1;
        }
    }
    if sendme {
        rc = f06_process_group_recursive_do_kill(
            thread, (*(*thread).proc).pid, -1, sig, info, ptracecont,
        ) as CInt;
    }
    // Preserve free(NULL) for the original zero-peer/self-only goto-sendme path.
    crate::mem_helpers::kfree_tracked(
        pids.cast(), concat!(file!(), "\0").as_ptr().cast_mut().cast(), line!() as CInt,
    );
    rc
}
