#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod policy {
    use crate::abi::{CInt,CULong};
    unsafe extern "C" {
        static mut uti_desc:CULong;
        fn kprintf(format:*const i8,...)->CInt;
    }
    include!("util-profile-entry.fixture.Rust.inc");
}
