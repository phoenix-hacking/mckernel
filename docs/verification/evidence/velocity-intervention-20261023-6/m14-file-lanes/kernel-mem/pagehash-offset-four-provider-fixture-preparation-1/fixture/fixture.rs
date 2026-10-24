#![no_std]
#![allow(dead_code)]
#[path = "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_abi.rs"] mod abi;
#[path = "/home/holden/mckernel/kernel/rust/spinlock_helpers.rs"] mod spinlock_helpers;
#[path = "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/page-offset-typed-provider-source-only-1/page_helpers.rs"] mod page_helpers;
use abi::CULong;
/// Exact existing physical-page hash IRQ-save ticket-lock provider.
/// Caller retains the initialized aligned lock; saved flags are returned unchanged.
#[no_mangle]
pub unsafe extern "C" fn page_hash_lock_bridge(lock_addr: CULong) -> CULong {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Same release/preempt-enable/IRQ-restore provider and exact captured flags.
#[no_mangle]
pub unsafe extern "C" fn page_hash_unlock_bridge(lock_addr: CULong, flags: CULong) {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock, flags,
        )
    }
}

/// Exact existing lock initialization; no allocator or bucket ownership changes.
#[no_mangle]
pub unsafe extern "C" fn page_hash_lock_init_bridge(lock_addr: CULong) {
    unsafe {
        crate::spinlock_helpers::ihk_mc_spinlock_init(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}


const _: unsafe extern "C" fn(*const page_helpers::Page)->abi::OffT = page_helpers::page_get_offset;
