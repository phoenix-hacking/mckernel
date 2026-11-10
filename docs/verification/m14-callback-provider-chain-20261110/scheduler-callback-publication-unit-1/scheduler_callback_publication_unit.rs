#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

include!("target_declarations.rs");
include!("publisher.rs");
