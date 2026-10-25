// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod f06_do_kill_thread_target_candidate {
    use core::ffi::c_void;
    use core::mem::offset_of;
    use core::ptr::{addr_of_mut, null_mut};

    use crate::abi::{AbiListHead, CInt, McsRwlockLock, Process, Thread, ThreadHash};

    use super::{ESRCH, PS_EXITED, PS_ZOMBIE, SIGKILL};

    /// Individual-TID target lookup and original protected reference acquisition.
    /// Return -ESRCH only for an absent matching live thread; otherwise zero.
    /// IRQ state stays disabled for the existing caller to restore or transfer.
    ///
    /// # Safety
    /// Caller owns IRQ-disabled state and the original resource-set thread hash.
    /// `tid` must map into the actual hash table, as required by the original C
    /// unchecked indexing contract. List members and process relations stay live
    /// under their original hash/update/threads locks. Output slots are distinct
    /// writable C locals, initially NULL. `node` is the original stack lock node,
    /// reused by BOTH hash and threads locks exactly as existing C; the production
    /// noirq providers ignore node contents. `update_node` is a distinct live node.
    /// No hash/list/process lock escapes. A successfully held target reference
    /// transfers to the caller's existing gate/enqueue/wakeup/release lifecycle.
    #[no_mangle]
    pub unsafe extern "C" fn arch_do_kill_thread_target_result(
        table: *mut ThreadHash, pid: CInt, tid: CInt, sig: CInt,
        node: *mut c_void, update_node: *mut c_void,
        selected_process: *mut *mut Process, selected_thread: *mut *mut Thread,
        pending_lock: *mut *mut McsRwlockLock, pending_head: *mut *mut AbiListHead,
    ) -> CInt {
        let hash = crate::process_helpers::thread_hash(tid) as usize;
        // SAFETY: actual hash index validity and genuine array layout are caller
        // contracts; raw pointers avoid references spanning lock acquisitions.
        let (hash_lock, head) = unsafe {
            (addr_of_mut!((*table).lock).cast::<McsRwlockLock>().add(hash),
             addr_of_mut!((*table).list).cast::<AbiListHead>().add(hash))
        };
        // SAFETY: caller's original node and IRQ-disabled hash-lock ownership.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_reader_lock_noirq(hash_lock.cast(), node);
        }
        let mut target: *mut Thread = null_mut();
        // SAFETY: hash lock protects traversal; only real nonsentinel entries
        // become Thread pointers. PID filtering retains original evaluation order.
        unsafe {
            let mut entry = (*head).next;
            while entry != head {
                let candidate = entry.cast::<u8>().sub(offset_of!(Thread, hash_list))
                    .cast::<Thread>();
                if (pid == -1 || (*(*candidate).proc).pid == pid)
                    && (*candidate).tid == tid && (*candidate).status != PS_EXITED
                {
                    target = candidate;
                    break;
                }
                entry = (*entry).next;
            }
        }
        if target.is_null() {
            // SAFETY: original absent-target return unlocks hash; caller restores IRQs.
            unsafe {
                crate::lock_helpers::__mcs_rwlock_reader_unlock_noirq(hash_lock.cast(), node);
            }
            return -ESRCH;
        }
        // SAFETY: hash guard retains selected thread/process relation through the
        // subsequent update/threads lock scopes and the actual hold operation.
        unsafe {
            let process = (*target).proc;
            *selected_process = process;
            let update_lock = addr_of_mut!((*process).update_lock);
            crate::lock_helpers::__mcs_rwlock_reader_lock_noirq(update_lock.cast(), update_node);
            *pending_lock = addr_of_mut!((*target).sigpendinglock);
            *pending_head = addr_of_mut!((*target).sigpending);
            let threads_lock = addr_of_mut!((*process).threads_lock);
            // Deliberate original node reuse: do not silently fix, replace with
            // IRQ-save locks or infer support from a homemade node implementation.
            crate::lock_helpers::__mcs_rwlock_reader_lock_noirq(threads_lock.cast(), node);
            if (*target).status != PS_EXITED
                && (sig == SIGKILL
                    || ((*process).status != PS_EXITED && (*process).status != PS_ZOMBIE))
            {
                let rc = crate::process_helpers::hold_thread(target);
                if rc != 0 {
                    super::kprintf(
                        b"%s: ERROR hold_thread returned %d,tid=%d\n\0".as_ptr().cast(),
                        b"do_kill\0".as_ptr().cast::<i8>(), rc, (*target).tid,
                    );
                    target = null_mut();
                }
            } else {
                target = null_mut();
            }
            *selected_thread = target;
            crate::lock_helpers::__mcs_rwlock_reader_unlock_noirq(threads_lock.cast(), node);
            crate::lock_helpers::__mcs_rwlock_reader_unlock_noirq(update_lock.cast(), update_node);
            crate::lock_helpers::__mcs_rwlock_reader_unlock_noirq(hash_lock.cast(), node);
        }
        0
    }
}
