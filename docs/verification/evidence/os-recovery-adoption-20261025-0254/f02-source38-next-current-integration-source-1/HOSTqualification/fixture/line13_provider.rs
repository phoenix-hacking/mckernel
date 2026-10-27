// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
use core::ffi::c_void;
use core::ptr::null_mut;
use abi::{CInt,CULong,SizeT,ProcessVm,VmRange};
const PAGE_SIZE:CULong=4096;
const IHK_MC_AP_NOWAIT:CULong=0x0000_02;
const KERNEL_STACK_NR_PAGES:CULong=32;
const VR_AP_USER:CULong=0x4;
const ENOMEM:CInt=12;
// Existing external tracked allocator/free effects, with actual production ABIs.
mod mem_helpers {
 use core::ffi::c_void;
 use crate::abi::{CInt,CULong};
 unsafe extern "C" {
  pub fn kmalloc_tracked(size:CInt,flags:CULong,file:*mut i8,line:CInt)->*mut c_void;
  pub fn kfree_tracked(ptr:*mut c_void,file:*mut i8,line:CInt);
  pub fn _ihk_mc_alloc_aligned_pages_node(n:CInt,a:CInt,f:CULong,node:CInt,user:CInt,addr:CULong,file:*mut i8,line:CInt)->*mut c_void;
  pub fn _ihk_mc_free_pages(ptr:*mut c_void,n:CInt,user:CInt,file:*mut i8,line:CInt);
 }
}
#[path="x86_geometry.ACTUAL.rs"] mod x86_memory_helpers;
unsafe extern "C" {
 static process_page_fault_anon_alloc_file:*const i8;
 static process_page_fault_anon_alloc_line:CInt;
 fn kprintf(format:*const i8,...)->CInt;
}
include!("tracked_current.ACTUAL.rs.inc");
include!("line_storage.ACTUAL.rs.inc");

mod process_create_thread_alloc_pages_bridge_owner {
 use super::*;
 unsafe extern "C" { static process_tracked_allocator_source_file:*const i8;
 static process_create_thread_alloc_pages_source_line:CInt; }
 include!("process_create_thread_alloc_pages_bridge.ACTUAL.rs.inc");
}

mod process_free_thread_pages_bridge_owner {
 use super::*;
 unsafe extern "C" { static process_tracked_allocator_source_file:*const i8;
 static process_free_thread_pages_source_line:CInt; }
 include!("process_free_thread_pages_bridge.ACTUAL.rs.inc");
}

mod process_split_range_alloc_bridge_owner {
 use super::*;
 unsafe extern "C" { static process_tracked_allocator_source_file:*const i8;
 static process_split_range_alloc_source_line:CInt; }
 include!("process_split_range_alloc_bridge.ACTUAL.rs.inc");
}

mod free_pages_owner {
 use super::*;
 unsafe extern "C" { static process_tracked_allocator_source_file:*const i8;
 static process_free_range_pages_source_line:CInt; }
 include!("free_pages.ACTUAL.rs.inc");
 // SAFETY: The caller supplies the original nullable page-span arguments;
 // the existing external fixture backend records them and performs no release.
 #[no_mangle]
 pub unsafe extern "C" fn fixture_invoke_free_range_pages(ptr:*mut c_void,pages:CULong) {
  unsafe { free_pages(ptr,pages); }
 }
}

include!("process_page_fault_anon_allocate_body_result.ACTUAL.rs.inc");

#[no_mangle] pub static LINE13_RUST_ABI:[usize;13]=[
 core::mem::size_of::<CInt>(),core::mem::align_of::<CInt>(),
 core::mem::size_of::<CULong>(),core::mem::size_of::<*mut c_void>(),
 core::mem::size_of::<VmRange>(),core::mem::align_of::<VmRange>(),
 core::mem::offset_of!(VmRange,flag),core::mem::offset_of!(VmRange,pgshift),
 core::mem::size_of::<ProcessVm>(),PAGE_SIZE as usize,0,0,1];
