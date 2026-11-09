#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

include!("local_accessor.rs");
include!("ipi_slot.rs");
