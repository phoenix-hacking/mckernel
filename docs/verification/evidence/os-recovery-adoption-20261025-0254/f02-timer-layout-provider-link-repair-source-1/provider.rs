// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ffi::c_void;
use core::ptr::write_volatile;
pub type CULong = u64;
pub type SizeT = usize;

include!("inline_memset.CURRENT.rs.inc");
