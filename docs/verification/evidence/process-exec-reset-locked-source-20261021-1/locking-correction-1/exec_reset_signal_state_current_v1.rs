use crate::abi::{KSigAction, SigCommon, Thread};
use crate::lock_helpers::McsRwlockNodeIrqsave;
use core::mem::MaybeUninit;
use core::ptr::null_mut;

/// Reset the signal state at the real successful exec commit point.
///
/// # Safety
/// `thread` and its `sigcommon` are the live current exec owner. The caller
/// keeps the live signal-table allocation pinned and preemption disabled across
/// this body and its existing clear_fp_regs call. The shared table writer lock
/// serializes caught-handler resets with peer sigaction/signal-table access.
/// This does not acquire/release a Thread, VM, signal table or altstack owner.
#[no_mangle]
pub unsafe extern "C" fn exec_reset_signal_state_current_v1(thread: *mut Thread) {
    unsafe extern "C" { fn clear_fp_regs(); }
    let common = (*thread).sigcommon.cast::<SigCommon>();
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let lock = core::ptr::addr_of_mut!((*common).lock).cast();
    crate::lock_helpers::__mcs_rwlock_writer_lock(lock, node.as_mut_ptr());
    let actions = core::ptr::addr_of_mut!((*common).action).cast::<KSigAction>();
    // Match the real x86-64 _NSIG=64 table. Raw field access avoids extending
    // a whole-table mutable borrow across the architecture callback.
    for i in 0..64 {
        let handler = core::ptr::addr_of_mut!((*actions.add(i)).sa.sa_handler);
        let old = core::ptr::read(handler) as usize;
        if old != 0 && old != 1 {
            core::ptr::write(handler, null_mut());
        }
    }
    // Only the action fields are protected. Restore the previous IRQ state and
    // preemption nesting before the architecture callback or altstack writes.
    crate::lock_helpers::__mcs_rwlock_writer_unlock(lock, node.as_mut_ptr());
    // Preserve the exact old ordering: dispositions, FP reset, altstack reset.
    clear_fp_regs();
    (*thread).sigstack.ss_sp = null_mut();
    (*thread).sigstack.ss_flags = 2; // SS_DISABLE
    (*thread).sigstack.ss_size = 0;
}
