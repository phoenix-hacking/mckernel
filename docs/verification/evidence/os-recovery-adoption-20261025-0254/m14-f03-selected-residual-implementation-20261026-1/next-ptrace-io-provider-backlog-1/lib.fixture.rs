#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="retained-abi.rs"]pub mod abi;
pub mod process_helpers {use crate::abi::{CInt,Thread};unsafe extern "C" {
 #[link_name="f03_fixture_find"]pub fn find_thread(tgid:CInt,tid:CInt)->*mut Thread;
 #[link_name="f03_fixture_unlock"]pub fn thread_unlock(thread:*mut Thread);
}}
pub mod x86_memory_helpers {use crate::abi::{CInt,SizeT};use core::ffi::c_void;unsafe extern "C" {
 #[link_name="f03_fixture_copy"]pub fn copy_from_user(dst:*mut c_void,src:*const c_void,bytes:SizeT)->CInt;
}}
pub mod policy {
 use crate::abi::{CInt,CLong,CULong,SizeT,Thread};use core::ffi::c_void;
 include!("01-ptrace-find-selected-1/selected.Rust.inc");
 include!("02-ptrace-unlock-selected-1/selected.Rust.inc");
 include!("retained-public-copy-from.Rust.inc");
#[no_mangle]pub static F03_PTRACE_IO_PROVIDER_ABI:[CULong;16]=[
 core::mem::size_of::<Thread>() as CULong,core::mem::align_of::<Thread>() as CULong,
 core::mem::size_of::<CInt>() as CULong,core::mem::align_of::<CInt>() as CULong,
 core::mem::size_of::<CLong>() as CULong,core::mem::align_of::<CLong>() as CULong,
 core::mem::size_of::<CULong>() as CULong,core::mem::align_of::<CULong>() as CULong,
 core::mem::size_of::<SizeT>() as CULong,core::mem::align_of::<SizeT>() as CULong,
 core::mem::size_of::<*mut c_void>() as CULong,core::mem::align_of::<*mut c_void>() as CULong,
 core::mem::size_of::<unsafe extern "C" fn(CInt,CInt)->CULong>() as CULong,
 core::mem::size_of::<unsafe extern "C" fn(CULong)>() as CULong,
 core::mem::size_of::<unsafe extern "C" fn(*mut u8,CULong,SizeT)->CLong>() as CULong,
 core::mem::offset_of!(Thread,proc) as CULong,
];
}
