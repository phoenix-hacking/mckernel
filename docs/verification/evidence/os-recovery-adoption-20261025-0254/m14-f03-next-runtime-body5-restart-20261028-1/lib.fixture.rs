#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
#[path="attr-layout.reused.rs"] mod f03_perf_attr_callbacks;
mod x86_perfctr { use crate::abi::{CULong,CInt};include!("extra-layout.reused.Rust.inc"); }
mod policy {
 use core::{ffi::c_void,ptr::{read_volatile,write_volatile}};
 use crate::abi::{CInt,CLong,CULong,SizeT,AbiListHead};
 include!("provider-types.Rust.inc");
 unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe{base.add(offset).cast()} }
 include!("allocator-candidate.Rust.inc");
 include!("event-layout.reused.Rust.inc");
 include!("entry.fixture.Rust.inc");
}
