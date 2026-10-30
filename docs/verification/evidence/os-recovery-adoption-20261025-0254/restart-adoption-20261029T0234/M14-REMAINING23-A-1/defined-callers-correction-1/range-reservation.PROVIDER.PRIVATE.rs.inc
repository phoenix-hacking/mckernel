// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private source: token registry only, not yet wired into mutators or XPMEM.
#[cfg(f03_mmap_range_reservation_candidate)]
pub(crate) mod f03_mmap_range_reservation_v1 {
    use core::ptr::{null_mut, read, write};
    use core::sync::atomic::{AtomicBool, AtomicPtr, Ordering};
    use crate::abi::{CInt, CULong, ProcessVm, VmRange};
    use super::{cpu_disable_interrupt_save, cpu_restore_interrupt};

    // One caller-owned token lives on the mmap stack until release. While linked,
    // its address and pointed VM/range cannot be recycled. Registry lock protects
    // all node fields and list operations, not VM range trees themselves.
    #[repr(C)]
    pub struct Reservation {
        vm: *mut ProcessVm,
        range: *mut VmRange,
        next: *mut Reservation,
    }
    static REGISTRY_LOCK: AtomicBool = AtomicBool::new(false);
    static REGISTRY_HEAD: AtomicPtr<Reservation> = AtomicPtr::new(null_mut());

    unsafe fn lock_registry() -> CULong {
        let flags = cpu_disable_interrupt_save();
        crate::cls::preempt_disable();
        while REGISTRY_LOCK.compare_exchange_weak(false, true, Ordering::Acquire,
                Ordering::Relaxed).is_err() { core::hint::spin_loop(); }
        flags
    }
    unsafe fn unlock_registry(flags: CULong) {
        REGISTRY_LOCK.store(false, Ordering::Release);
        crate::cls::preempt_enable();
        cpu_restore_interrupt(flags);
    }
    /// # Safety
    /// Caller owns this VM's writer, its linked range, and a unique live stack
    /// slot until unregister. All mutators/teardown must consult the same registry
    /// while owning that writer and must release it before waiting or retrying.
    /// Slot contents are fully written before it is published. This function
    /// neither creates a VM ref nor authorizes concurrent lifetime release.
    pub unsafe fn reserve_write(vm: *mut ProcessVm, range: *mut VmRange,
        slot: *mut Reservation) {
        let flags = lock_registry();
        write(slot, Reservation { vm, range, next: REGISTRY_HEAD.load(Ordering::Relaxed) });
        REGISTRY_HEAD.store(slot, Ordering::Relaxed);
        unlock_registry(flags);
    }
    /// # Safety
    /// Caller holds VM writer and has a live VM. `range==NULL` asks whether any
    /// reservation blocks VM-wide teardown. A non-null range must be a currently
    /// live candidate node selected under that same VM writer. Result is only a
    /// conflict observation: on 1 the caller releases VM writer before retrying;
    /// on 0 it mutates under the same uninterrupted writer acquisition.
    #[no_mangle]
    pub unsafe extern "C" fn f03_mmap_range_conflicts_write_v1(
        vm: *mut ProcessVm, range: *mut VmRange,
    ) -> CInt {
        let flags = lock_registry();
        let mut cur = REGISTRY_HEAD.load(Ordering::Relaxed);
        let mut found = 0;
        while !cur.is_null() {
            if (*cur).vm == vm && (range.is_null() || (*cur).range == range) {
                found = 1; break;
            }
            cur = (*cur).next;
        }
        unlock_registry(flags);
        found
    }
    /// # Safety
    /// The slot remains exclusively owned by its live caller during this check.
    /// Pointer identity is compared under the registry lock before fields are read.
    pub unsafe fn is_registered(vm: *mut ProcessVm, range: *mut VmRange,
        slot: *mut Reservation) -> bool {
        let flags = lock_registry();
        let mut cur = REGISTRY_HEAD.load(Ordering::Relaxed);
        let mut found = false;
        while !cur.is_null() {
            if cur == slot { found = (*cur).vm == vm && (*cur).range == range; break; }
            cur = (*cur).next;
        }
        unlock_registry(flags);
        found
    }
    /// # Safety
    /// This call must be made exactly once for the same live registered slot
    /// after all token-bound readers and XPMEM operations have finished. It does
    /// not wait for outstanding provider work. No slot access follows removal.
    pub unsafe fn release(slot: *mut Reservation) -> CInt {
        let flags = lock_registry();
        let mut cur = REGISTRY_HEAD.load(Ordering::Relaxed);
        let mut previous: *mut Reservation = null_mut();
        while !cur.is_null() && cur != slot { previous = cur; cur = (*cur).next; }
        if cur.is_null() { unlock_registry(flags); return -22; }
        let next = read(core::ptr::addr_of!((*cur).next));
        if previous.is_null() { REGISTRY_HEAD.store(next, Ordering::Relaxed); }
        else { (*previous).next = next; }
        unlock_registry(flags);
        0
    }
}
