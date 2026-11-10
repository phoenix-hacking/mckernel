#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

use crate::abi::CULong;

type CUInt = u32;

// Reuse the genuine already-qualified WRMSR owner; no body or alias here.
unsafe extern "C" {
    fn wrmsr(index: CUInt, value: CULong);
}

include!("rdmsr.rs");
include!("local_apic_io.rs");
