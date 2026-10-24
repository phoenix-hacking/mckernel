// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
#[path="abi.ACTUAL.rs"]mod abi;
#[path="affinity.ACTUAL.rs"]mod affinity;
use abi::{CInt,CULong,SizeT,CpuSet,CpuLocalVar};
use core::mem::{size_of,align_of,offset_of};
use core::ptr::{addr_of,addr_of_mut,read_volatile,write_volatile};
use core::sync::atomic::{AtomicU64,Ordering};
extern "C" {
 fn fixture_clone_cpu(id:CInt)->*mut CpuLocalVar;
 fn fixture_clone_lock(p:*mut abi::IhkSpinlock)->CULong;
 fn fixture_clone_unlock(p:*mut abi::IhkSpinlock,irq:CULong);
 fn fixture_clone_noirq_lock(p:*mut abi::IhkSpinlock);
 fn fixture_clone_noirq_unlock(p:*mut abi::IhkSpinlock);
 fn kprintf(p:*const i8,...)->CInt;
}
mod cls {use super::*;pub unsafe extern "C" fn get_cpu_local_var(id:CInt)->*mut CpuLocalVar{fixture_clone_cpu(id)}}
mod ap {use super::*;#[no_mangle]pub static mut num_processors:CInt=0;}
mod spinlock_helpers {use super::*;
 pub unsafe fn __ihk_mc_spinlock_lock(p:*mut abi::IhkSpinlock)->CULong{fixture_clone_lock(p)}
 pub unsafe fn __ihk_mc_spinlock_unlock(p:*mut abi::IhkSpinlock,irq:CULong){fixture_clone_unlock(p,irq)}
 pub unsafe fn __ihk_mc_spinlock_lock_noirq(p:*mut abi::IhkSpinlock){fixture_clone_noirq_lock(p)}
 pub unsafe fn __ihk_mc_spinlock_unlock_noirq(p:*mut abi::IhkSpinlock){fixture_clone_noirq_unlock(p)}
}
mod debug {#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
}
include!("../candidate/syscall_policy.obtain_clone_cpuid.FRAGMENT.rs");
include!("real-ABI-Rust-facts.inc");
