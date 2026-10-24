// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Prefix fragment only, not an executable queue; actual ABI is referenced directly.
#![no_std]
#[path="/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
use core::ffi::c_void;
use abi::{CInt,CLong,CULong,X86UserContext};
include!("CONSTANTS.UNCHANGED-RUST.inc");
include!("exec_entries_actual.RUST-FIXTURE-FRAGMENT.rs.inc");
