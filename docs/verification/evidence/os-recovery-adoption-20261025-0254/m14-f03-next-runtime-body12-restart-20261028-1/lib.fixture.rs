#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod debug {include!("debug-layout.reused.Rust.inc");}
mod policy {
 unsafe extern "C" {fn kprintf(format:*const i8,...)->crate::abi::CInt;}
 include!("entry.fixture.Rust.inc");
}
