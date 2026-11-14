#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

use crate::abi::{CInt, CULong};

type CUInt = u32;

const EINVAL: CInt = 22;

type X86VoidFn = unsafe extern "C" fn();
type X86DisableSaveFn = unsafe extern "C" fn() -> CULong;
type X86RestoreFn = unsafe extern "C" fn(CULong);
type X86IcrWriteFn = unsafe extern "C" fn(CUInt, CUInt);

extern "C" {
    fn ihk_mc_mb();
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
    fn x86_write_msr_bridge(reg: CInt, value: CULong);
    fn x86_lapic_write_bridge(reg: CInt, value: CUInt);
    fn x86_cpu_pause_bridge();
}

include!("transactions.rs");
include!("ipi_entries.rs");
include!("icr_callbacks.rs");
include!("fixed_data.rs");
