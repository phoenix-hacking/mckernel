// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
mod pte_helpers { include!("pte_predicates.ACTUAL-RUST.inc"); }
use core::ffi::c_void;use abi::{CInt,CULong,SizeT};
include!("callbacks.ACTUAL-RUST.inc");
