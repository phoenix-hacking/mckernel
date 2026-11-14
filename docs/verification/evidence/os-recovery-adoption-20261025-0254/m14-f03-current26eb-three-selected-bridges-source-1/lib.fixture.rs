#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="retained-abi.rs"]pub mod abi;
pub mod process_helpers {
 use crate::abi::{CInt,Thread};
 unsafe extern "C" {
  #[link_name="f03_three_fixture_find"]pub fn find_thread(tgid:CInt,tid:CInt)->*mut Thread;
  #[link_name="f03_three_fixture_unlock"]pub fn thread_unlock(thread:*mut Thread);
 }
}
pub mod waitq {
 type CUInt=u32;
 include!("retained-waitq-layout.Rust.inc");
 unsafe extern "C" {
  #[link_name="f03_three_fixture_wake"]pub(crate) fn waitq_wakeup(waitq:*mut Waitq);
 }
 #[no_mangle]
 pub static F03_THREE_WAKE_PROVIDER_ABI:[crate::abi::CULong;19]=[
  core::mem::size_of::<crate::abi::Thread>() as _,core::mem::align_of::<crate::abi::Thread>() as _,
  core::mem::size_of::<crate::abi::CInt>() as _,core::mem::align_of::<crate::abi::CInt>() as _,
  core::mem::size_of::<crate::abi::CULong>() as _,core::mem::align_of::<crate::abi::CULong>() as _,
  core::mem::size_of::<*mut core::ffi::c_void>() as _,core::mem::align_of::<*mut core::ffi::c_void>() as _,
  core::mem::size_of::<unsafe extern "C" fn(crate::abi::CInt,crate::abi::CInt)->crate::abi::CULong>() as _,
  core::mem::size_of::<unsafe extern "C" fn(crate::abi::CULong)>() as _,
  core::mem::size_of::<unsafe extern "C" fn(*mut core::ffi::c_void)>() as _,
  core::mem::size_of::<Waitq>() as _,core::mem::align_of::<Waitq>() as _,
  core::mem::offset_of!(Waitq,lock) as _,core::mem::offset_of!(Waitq,waitq) as _,
  core::mem::size_of::<IhkSpinlock>() as _,core::mem::align_of::<IhkSpinlock>() as _,
  core::mem::size_of::<ListHead>() as _,core::mem::align_of::<ListHead>() as _,
 ];
}
pub mod policy {
 use crate::abi::{CInt,CULong,Thread};use core::ffi::c_void;
 include!("01-ptrace_wakeup_find_thread_bridge/selected.Rust.inc");
 include!("02-ptrace_wakeup_thread_unlock_bridge/selected.Rust.inc");
 include!("03-thread_exit_waitq_wake_bridge/selected.Rust.inc");
}
