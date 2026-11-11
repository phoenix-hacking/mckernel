// Typed actual ABI primitive effects, with explicit S-release observation only.
pub use crate::abi::IhkSpinlock;
use crate::abi::CULong;
pub unsafe extern "C" fn __ihk_mc_spinlock_lock(lock:*mut IhkSpinlock)->CULong{
 unsafe{crate::host_effects::spinlock_helpers::__ihk_mc_spinlock_lock(lock)}
}
pub unsafe extern "C" fn __ihk_mc_spinlock_unlock(lock:*mut IhkSpinlock,flags:CULong){
 let state=crate::host_effects::held_locks().last().map(|v|v.class)==Some(crate::host_effects::LockClass::State);
 unsafe{crate::host_effects::spinlock_helpers::__ihk_mc_spinlock_unlock(lock,flags)};
 if state {crate::host_effects::assert_effects_unlocked("after actual S release");assert!(crate::host_effects::irq_enabled());unsafe{crate::host_perf_bindings::after_state_unlock()};}
}
pub unsafe extern "C" fn __ihk_mc_spinlock_lock_noirq(lock:*mut IhkSpinlock){unsafe{crate::host_effects::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(lock)}}
pub unsafe extern "C" fn __ihk_mc_spinlock_unlock_noirq(lock:*mut IhkSpinlock){unsafe{crate::host_effects::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(lock)}}
