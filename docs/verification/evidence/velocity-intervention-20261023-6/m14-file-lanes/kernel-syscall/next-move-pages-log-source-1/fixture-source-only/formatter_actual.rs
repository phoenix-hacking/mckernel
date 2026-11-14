#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
type CInt = i32;
type CULong = u64;
unsafe extern "C" { fn kprintf(format: *const i8, ...) -> CInt; }
include!("../move_pages_log.UNCHANGED-CONSTANTS.rs.inc");
include!("../move_pages_log.RUST-FRAGMENT.rs.inc");
