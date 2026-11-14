// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual providers; no zeroobj implementation/reference policy is duplicated.
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use abi::{CInt,CULong,OffT,SizeT,VmRange,Memobj};
const NOPHYS:CULong=!0;
mod object_helpers { include!("object_provider.ACTUAL-RUST.inc"); }
mod pte_helpers { include!("pte_provider.ACTUAL-RUST.inc"); }
include!("memobj_get.ACTUAL-RUST.inc");
