// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: coalesce/allocate/publish while the EXISTING C pending writer lock is held.
// The caller retains its held target reference and disabled IRQ state throughout;
// this helper neither locks/unlocks nor releases that target reference.
#[no_mangle]
pub unsafe extern "C" fn arch_do_kill_pending_enqueue_result(
    target: *mut Thread, head: *mut AbiListHead, mask: CULong, sig: CInt,
    info: *const SigInfo, ptracecont: CInt, doint: *mut CInt,
) -> CInt {
    let mut pending: *mut crate::abi::SigPending = null_mut();
    // Actual caller sets this slot to zero before taking the writer lock.
    // A coalesced signal leaves that slot untouched, like the original branch.
    if sig < 33 {
        let mut pos = (*head).next;
        while pos != head {
            let candidate = pos.cast::<u8>()
                .wrapping_sub(offset_of!(crate::abi::SigPending, list))
                .cast::<crate::abi::SigPending>();
            if (*candidate).sigmask.val[0] == mask && (*candidate).ptracecont == ptracecont {
                pending = candidate;
                break;
            }
            pos = (*candidate).list.next;
        }
    }
    if !pending.is_null() {
        // Standard-signal coalescing leaves existing info/list/interrupted state
        // and target sigevent untouched, exactly like the original branch.
        return 0;
    }
    // Preserve doint=1 EVEN when the unchanged allocator returns NULL.
    *doint = 1;
    pending = crate::mem_helpers::kmalloc_tracked(
        size_of::<crate::abi::SigPending>() as CInt, IHK_MC_AP_NOWAIT,
        concat!(file!(), "\0").as_ptr().cast_mut().cast(), line!() as CInt,
    ).cast();
    if pending.is_null() { return -ENOMEM; }
    crate::string::__inline_memset(pending.cast(), 0, size_of::<crate::abi::SigPending>());
    (*pending).sigmask.val[0] = mask;
    // Copy every siginfo byte, including its representation/padding as in C.
    crate::string::memcpy(core::ptr::addr_of_mut!((*pending).info).cast(),
        info.cast(), size_of::<SigInfo>());
    (*pending).ptracecont = ptracecont;
    if sig == SIGKILL || sig == SIGSTOP {
        crate::list_helpers::list_add(core::ptr::addr_of_mut!((*pending).list).cast(), head.cast());
    } else {
        crate::list_helpers::list_add_tail(core::ptr::addr_of_mut!((*pending).list).cast(), head.cast());
    }
    // Ownership transfers to the protected list before the original event store.
    // No free is allowed here: do_signal/the pending consumer later owns release.
    (*target).sigevent = 1;
    0
}
