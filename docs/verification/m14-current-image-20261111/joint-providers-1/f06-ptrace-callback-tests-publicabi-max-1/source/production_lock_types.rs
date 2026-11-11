use crate::abi::CULong;
use crate::spinlock_helpers;
#[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}
#[repr(C, align(64))]
pub struct McsRwlockLock {
    slock: spinlock_helpers::IhkSpinlock,
}
// Test-only lower effects. No real spinlock, GS or IRQ instruction is invoked.
pub unsafe extern "C" fn __mcs_rwlock_writer_lock(lock:*mut McsRwlockLock,node:*mut McsRwlockNodeIrqsave) {
 crate::host_writer_lock(lock as usize,node as usize); (*node).irqsave=crate::SAVED_IRQ;
}
pub unsafe extern "C" fn __mcs_rwlock_writer_unlock(lock:*mut McsRwlockLock,node:*mut McsRwlockNodeIrqsave) {
 let saved=(*node).irqsave; crate::host_writer_unlock(lock as usize,node as usize,saved);
}
