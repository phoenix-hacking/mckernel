#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
#[path = "debug_type.rs"]
mod debug;

use crate::abi::CInt;
use core::ptr::read_volatile;

extern "C" {
    fn kprintf(format: *const i8, ...) -> CInt;
}

// Declaration of the genuine existing current-CPU provider; no body is copied.
mod x86_local {
    use crate::abi::CInt;
    unsafe extern "C" {
        pub(crate) fn ihk_mc_get_processor_id() -> CInt;
    }
}

include!("x86_interrupt_logger.rs");
include!("ipi_callback.rs");
include!("cpu_verbose_record.rs");
