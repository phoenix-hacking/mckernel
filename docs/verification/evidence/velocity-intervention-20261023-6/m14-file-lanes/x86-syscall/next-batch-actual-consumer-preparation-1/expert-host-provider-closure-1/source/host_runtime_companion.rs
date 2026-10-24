// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// HOST fixture companion only. Default genuine std/core/panic_abort runtime;
// deliberately no no_std/custom panic handler/provider stubs/ABI substitutions.
#[path = "abi.ACTUAL.rs"]mod abi;
use abi::{CInt,CULong,SizeT};
use core::ffi::c_void;
use core::ptr::write_volatile;
include!("actual-memset-270B.inc");
include!("actual-inline-memset-691B.inc");
