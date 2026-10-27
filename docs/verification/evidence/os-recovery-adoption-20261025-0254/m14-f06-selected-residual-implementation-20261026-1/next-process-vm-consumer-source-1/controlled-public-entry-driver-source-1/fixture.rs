// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile, write};
use crate::abi::{CInt, CLong, CULong, IhkAtomic, Iovec, Process, ProcessVm, SizeT, Thread, VmRange};
use crate::lock_helpers::McsRwlockNodeIrqsave;
#[path = "abi.rs"]
mod abi;
include!("fixture-providers.rs");
include!("actual-types.inc");
include!("actual-layouts.inc");
include!("actual-node.inc");
include!("actual-constants.inc");
include!("actual-offsets.inc");
include!("actual-body.inc");
include!("Rust-ABI-facts.inc");
#[path = "f06_process_vm_entry.rs"]
mod f06_process_vm_entry;
extern "C" {
    fn arch_process_vm_rw_log_bridge(record: *const ArchProcessVmRwLogRecord);
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { loop {} }
