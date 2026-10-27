#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="retained-abi.rs"]pub mod abi;
#[path="retained-atomic_helpers.rs"]pub mod atomic_helpers;
pub mod process_helpers {use crate::abi::Process;unsafe extern "C" {
 #[link_name="f03_fixture_process_release"]pub fn release_process(proc:*mut Process);
}}
pub mod policy {
 use crate::abi::{CInt,CULong};use core::ffi::c_void;
 include!("01-wait-process-release-selected-1/selected.Rust.inc");
 include!("02-terminate-refcount-selected-1/selected.Rust.inc");
#[no_mangle]pub static F03_TERMINATION_PROVIDER_ABI:[CULong;16]=[
 core::mem::size_of::<crate::atomic_helpers::IhkAtomic>() as CULong,
 core::mem::align_of::<crate::atomic_helpers::IhkAtomic>() as CULong,
 0,
 core::mem::size_of::<CULong>() as CULong,
 core::mem::align_of::<CULong>() as CULong,
 core::mem::size_of::<crate::abi::Process>() as CULong,
 core::mem::align_of::<crate::abi::Process>() as CULong,
 core::mem::size_of::<unsafe extern "C" fn(*mut c_void)>() as CULong,
 core::mem::size_of::<unsafe extern "C" fn(*mut c_void,CInt)>() as CULong,
 core::mem::size_of::<unsafe extern "C" fn(*mut CULong,CULong,CULong)->CULong>() as CULong,
 core::mem::size_of::<CInt>() as CULong,
 core::mem::align_of::<CInt>() as CULong,
 core::mem::size_of::<crate::abi::IhkAtomic>() as CULong,
 core::mem::align_of::<crate::abi::IhkAtomic>() as CULong,
 core::mem::offset_of!(crate::abi::IhkAtomic,counter) as CULong,
 core::mem::size_of::<*mut c_void>() as CULong,
];
}
