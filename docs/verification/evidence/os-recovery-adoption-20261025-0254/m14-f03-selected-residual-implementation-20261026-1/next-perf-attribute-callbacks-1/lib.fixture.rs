#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
pub mod abi { pub type CInt=i32; pub type CULong=u64; }
#[path="candidate/kernel/rust/f03_perf_attr_callbacks.rs"]
pub mod f03_perf_attr_callbacks;
